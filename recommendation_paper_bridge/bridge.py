#!/usr/bin/env python3
"""Isolated Alpaca PAPER recommendation intake/router. No LIVE endpoints.

No broker network calls unless three independently provisioned commissioning
gates are present. Designed to fail closed: ambiguous submissions are NEVER
retried automatically. Existing V1 executor and host worktrees are not used.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta, time
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib import request, parse, error
from zoneinfo import ZoneInfo

DB_NAME = "securityprepper_trading"
CT = ZoneInfo("America/Chicago")
NY = ZoneInfo("America/New_York")
PAPER_HOST = "https://paper-api.alpaca.markets"
DATA_HOST = "https://data.alpaca.markets"
INTENT_TABLE = DB_NAME + ".sp_paper_rec_intents"
EVENT_TABLE = DB_NAME + ".sp_paper_rec_events"
CLAIM_TABLE = DB_NAME + ".sp_paper_rec_symbol_claims"
TASKS = {"Task - Trading Opportunities "+x for x in ("One","Two","Three","Four")}
SYMBOL = re.compile(r"[A-Z][A-Z0-9.]{0,11}\Z")
REC_ID = re.compile(r"TO-20[0-9]{6}-[A-Z0-9.]+-T[1-4]-[A-Z0-9]+\Z")
MAX_RISK_NOTIONAL = Decimal("2000")
MAX_SPREAD = Decimal("0.01")
MAX_QUOTE_AGE = timedelta(seconds=45)
ENTRY_CUTOFF = time(13,15)
EXIT_CUTOFF = time(13,40)
TERMINAL = {"filled","canceled","expired","rejected","done_for_day"}

class Unsafe(ValueError): pass
class SubmissionUnknown(RuntimeError): pass
class BrokerRejected(RuntimeError): pass

def utc(value):
    if not isinstance(value,str):
        raise Unsafe("timestamp must be ISO-8601")
    try: t=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as e: raise Unsafe("invalid timestamp") from e
    if t.tzinfo is None: raise Unsafe("timestamp must be timezone aware")
    return t.astimezone(timezone.utc)

def money(value,field):
    if isinstance(value,(float,bool)) or value is None: raise Unsafe(field+": decimal string required")
    try: x=Decimal(str(value))
    except (InvalidOperation,ValueError): raise Unsafe(field+": invalid number")
    if not x.is_finite() or x<=0 or x>1000000 or x.as_tuple().exponent < -4:
        raise Unsafe(field+": invalid precision or range")
    return x

def as_db_time(t):
    return t.astimezone(timezone.utc).replace(tzinfo=None)

def safe_client_id(rec_id):
    return "TO-P-"+sha256((rec_id+"|PAPER|BUY|v1").encode()).hexdigest()[:40]

def validate_recommendation(r, now=None):
    now=now or datetime.now(timezone.utc)
    names=("recommendation_id","issued_at_utc","quote_at_utc","symbol","action",
           "quote_last","quote_bid","quote_ask","limit","profit_target",
           "stop_loss","rationale","source_task","source_run_id")
    if not isinstance(r,dict) or any(not r.get(k) for k in names):
        raise Unsafe("required recommendation provenance missing")
    if not REC_ID.fullmatch(str(r["recommendation_id"])):
        raise Unsafe("recommendation ID is not canonical")
    if not SYMBOL.fullmatch(str(r["symbol"])) or "-"+r["symbol"]+"-" not in r["recommendation_id"]:
        raise Unsafe("symbol mismatch")
    if r["source_task"] not in TASKS or r["action"] not in ("BUY NOW","BUY AT PULLBACK"):
        raise Unsafe("unsupported originating task or action")
    issued,quote=utc(r["issued_at_utc"]),utc(r["quote_at_utc"])
    if not timedelta(0)<=now-issued<=timedelta(minutes=5):
        raise Unsafe("recommendation timestamp not current")
    if not timedelta(0)<=issued-quote<=timedelta(seconds=90):
        raise Unsafe("quote timestamp not contemporaneous")
    if len(str(r["rationale"]))>3000 or not str(r["rationale"]).strip():
        raise Unsafe("rationale missing or too long")
    if len(str(r["source_run_id"]))>128 or not re.fullmatch(r"[\w.:-]+",str(r["source_run_id"])):
        raise Unsafe("invalid task run ID")
    last,bid,ask,limit,target,stop=(money(r[k],k) for k in (
         "quote_last","quote_bid","quote_ask","limit","profit_target","stop_loss"))
    if not (bid<=last<=ask) or (ask-bid)/ask>MAX_SPREAD:
        raise Unsafe("quote is crossed/outside allowed spread")
    if not stop<limit<target or stop>=bid:
        raise Unsafe("profit/stop protection not coherent with bid/limit")
    if r["action"]=="BUY NOW" and ask>limit:
        raise Unsafe("BUY NOW requires ask within recommended limit")
    for p in (limit,target,stop):
        if not Decimal("0.65")<=p/last<=Decimal("1.5"):
            raise Unsafe("mis-scaled numeric level")
    qty=int((MAX_RISK_NOTIONAL/limit).to_integral_value(rounding=ROUND_FLOOR))
    if not 1<=qty<=10000: raise Unsafe("notional/whole-share quantity invalid")
    # Entry will not silently carry across the overnight or the owner's cutoff.
    session=issued.astimezone(CT).date()
    expiry=datetime.combine(session,ENTRY_CUTOFF,CT).astimezone(timezone.utc)
    status="PENDING" if issued<expiry and issued.astimezone(CT).weekday()<5 else "NOT_PLACED_CUTOFF"
    return dict(id=r["recommendation_id"],issued=issued,quote=quote,session=session,
                expiry=expiry,action=r["action"],symbol=r["symbol"],source_task=r["source_task"],
                source_run_id=r["source_run_id"],rationale=str(r["rationale"]).strip(),
                last=last,bid=bid,ask=ask,limit=limit,target=target,stop=stop,
                qty=qty,client_id=safe_client_id(r["recommendation_id"]),status=status)

def db_connect(config_env):
    import mysql.connector
    conf=os.environ.get(config_env,"")
    if not conf or not os.path.isabs(conf):
        raise Unsafe("protected database connection config not available")
    return mysql.connector.connect(option_files=conf,option_groups="client",
                                    autocommit=False,connection_timeout=6)

def event(cur, rec_id, kind, payload):
    cur.execute("INSERT INTO "+EVENT_TABLE+"(recommendation_id,event_type,evidence_json) VALUES(%s,%s,%s)",
                (rec_id,kind,json.dumps(payload,sort_keys=True,separators=(",",":"))))

def ingest(r, now=None, connect=db_connect, test_rollback=False):
    s=validate_recommendation(r,now)
    conn=connect("PAPER_BRIDGE_INTAKE_CNF")
    try:
        cur=conn.cursor()
        conn.start_transaction()
        cur.execute("INSERT INTO "+INTENT_TABLE+"""(recommendation_id,issued_at_utc,quote_at_utc,
                     expires_at_utc,session_date,symbol,action,source_task,source_run_id,rationale,
                     quote_last,quote_bid,quote_ask,limit_price,profit_target,stop_loss,intended_qty,
                     client_order_id,status,failure_code)
                     VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (s["id"],as_db_time(s["issued"]),as_db_time(s["quote"]),as_db_time(s["expiry"]),
             s["session"],s["symbol"],s["action"],s["source_task"],s["source_run_id"],s["rationale"],
             s["last"],s["bid"],s["ask"],s["limit"],s["target"],s["stop"],s["qty"],s["client_id"],
             s["status"],"PAST_ENTRY_CUTOFF" if s["status"]!="PENDING" else None))
        event(cur,s["id"],"RECOMMENDATION_RECORDED",{
            "source_task":s["source_task"],"source_run_id":s["source_run_id"],
            "quote_last":str(s["last"]),"quote_bid":str(s["bid"]),"quote_ask":str(s["ask"]),
            "limit":str(s["limit"]),"target":str(s["target"]),"stop":str(s["stop"]),
            "rationale":s["rationale"],"time":s["issued"].isoformat(),"status":s["status"]})
        # Project into existing canonical recommendation ledgers atomically,
        # without invoking or weakening the review-only writer.
        cur.execute("INSERT INTO "+DB_NAME+""".sp_live_recommendation_ledger
            (source_observed_at_utc,f_recommendation_id,f_recommended_at,f_symbol,
             f_action,f_recommended_qty,f_entry_rule,f_profit_targets,f_stop_invalidation,
             f_source_workflow,f_status,f_source_context,f_notes)
             VALUES (UTC_TIMESTAMP(6),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (s["id"],as_db_time(s["issued"]),s["symbol"],s["action"],s["qty"],
             "PAPER limit $"+str(s["limit"]),"PAPER bracket target $"+str(s["target"]),
             "PAPER bracket stop $"+str(s["stop"]),s["source_task"],
             s["status"],s["rationale"],"Source run "+s["source_run_id"]+"; receipt pending"))
        cur.execute("INSERT INTO "+DB_NAME+""".sp_notes_recommendations
            (source_observed_at_utc,f_recommendation_id,f_symbol,f_side,f_quantity,
             f_status,f_baseline_price,f_baseline_bid,f_baseline_ask,f_baseline_timestamp,
             f_entry_guidance,f_protection_guidance,f_management_guidance,
             f_user_approval_required,f_execution_authorized,f_expires_at,f_notes)
             VALUES (UTC_TIMESTAMP(6),%s,%s,'BUY',%s,%s,%s,%s,%s,%s,%s,%s,%s,0,1,%s,%s)""",
            (s["id"],s["symbol"],s["qty"],s["status"],s["last"],s["bid"],s["ask"],
             as_db_time(s["quote"]),"limit "+str(s["limit"]),
             "target "+str(s["target"])+"; stop "+str(s["stop"]),
             "NO LIVE; order receipt mandatory; 13:40 CT flat",as_db_time(s["expiry"]),s["rationale"]))
        if test_rollback:
            # Verify both new and canonical legacy ledger rows within the
            # same transaction, then leave absolutely no persistent test data.
            cur.execute("SELECT COUNT(*) FROM "+INTENT_TABLE+
                        " WHERE recommendation_id=%s",(s["id"],))
            a=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM "+DB_NAME+
                        ".sp_live_recommendation_ledger WHERE f_recommendation_id=%s",(s["id"],))
            b=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM "+DB_NAME+
                        ".sp_notes_recommendations WHERE f_recommendation_id=%s",(s["id"],))
            c=cur.fetchone()[0]
            if (a,b,c)!=(1,1,1): raise Unsafe("atomic dual-ledger readback failed")
            conn.rollback()
        else:
            conn.commit()
        return {"recommendation_id":s["id"],"status":"ROLLBACK_VERIFIED" if test_rollback else s["status"],
                "client_order_id":s["client_id"],"intended_qty":s["qty"],
                "order_submitted":False}
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()

class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Unsafe("broker redirects prohibited")

def creds():
    base=os.environ.get("CREDENTIALS_DIRECTORY","")
    if not base: raise Unsafe("systemd LoadCredential required")
    k=(Path(base)/"alpaca_data_key_id").read_text().strip()
    s=(Path(base)/"alpaca_data_secret").read_text().strip()
    if not k or not s: raise Unsafe("broker credentials unavailable")
    return {"APCA-API-KEY-ID":k,"APCA-API-SECRET-KEY":s,"Accept":"application/json",
            "Content-Type":"application/json"}

def http(method,path,body=None,data=False):
    if method not in ("GET","POST","DELETE") or not path.startswith("/") or ".." in path or "://" in path:
        raise Unsafe("restricted HTTP operation")
    if method=="DELETE" and not re.fullmatch(r"/v2/orders/[a-fA-F0-9-]{36}",path):
        raise Unsafe("delete restricted to exact PAPER order UUID")
    if data:
        if method!="GET" or not path.startswith("/v2/stocks/"):
            raise Unsafe("data GET only")
    elif not (path.startswith("/v2/orders") or path.startswith("/v2/account/activities?") or path in ("/v2/account","/v2/positions")):
        raise Unsafe("broker path forbidden")
    url=(DATA_HOST if data else PAPER_HOST)+path
    raw=None if body is None else json.dumps(body,separators=(",",":")).encode()
    try:
        resp=request.build_opener(NoRedirect()).open(
            request.Request(url,data=raw,headers=creds(),method=method),timeout=9)
        with resp:
            if resp.status not in (200,201,204): raise SubmissionUnknown("broker HTTP uncertainty")
            blob=resp.read(600001)
    except error.HTTPError as e:
        if e.code in (400,401,403,404,422): raise BrokerRejected("HTTP "+str(e.code))
        raise SubmissionUnknown("broker HTTP uncertainty") from e
    except (error.URLError,TimeoutError,OSError) as e:
        raise SubmissionUnknown("transport uncertainty: requires readback") from e
    if len(blob)>600000: raise SubmissionUnknown("oversized broker response")
    if not blob: return {}
    try: return json.loads(blob)
    except (ValueError,UnicodeError): raise SubmissionUnknown("non-JSON broker response")

def require_commissioned():
    # Never run an unprotected order path just because a timer exists.
    for name in ("PAPER_BRIDGE_COMMISSIONED","PAPER_BRIDGE_SHARED_LOCK_ATTESTED",
                 "PAPER_BRIDGE_EXIT_GUARD_ATTESTED"):
        if os.environ.get(name)!="1": raise Unsafe(name+" not verified")
    if not os.environ.get("PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT"):
        raise Unsafe("PAPER account allowlist missing")

def entry_window(now):
    t=now.astimezone(CT)
    ny=now.astimezone(NY)
    return (t.weekday()<5 and time(8,30)<=t.time()<ENTRY_CUTOFF
            and time(9,30)<=ny.time()<time(16,0))

def require_holiday(now):
    from holiday_gate import current_gate
    path=Path(os.environ.get("PAPER_BRIDGE_HOLIDAY_CACHE",""))
    if not path.is_absolute(): raise Unsafe("holiday cache missing")
    gate,_=current_gate(path,now)
    if not gate or gate.get("paused") is not False: raise Unsafe("holiday not verified unpaused")

def preflight(row, now, httpfn=http):
    require_commissioned()
    require_holiday(now)
    if not entry_window(now): raise Unsafe("outside RTH/PAPER entry cutoff")
    issued=row["issued_at_utc"].replace(tzinfo=timezone.utc)
    expiration=row["expires_at_utc"].replace(tzinfo=timezone.utc)
    if now>=expiration or now-issued>timedelta(minutes=5):
        raise Unsafe("recommendation expired; no carryover")
    acct=httpfn("GET","/v2/account")
    expected=os.environ["PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT"]
    if acct.get("id")!=expected or acct.get("account_blocked") or acct.get("trading_blocked") is not False:
        raise Unsafe("PAPER account identity not verified")
    if acct.get("status")!="ACTIVE": raise Unsafe("account not active")
    poses=httpfn("GET","/v2/positions")
    orders=httpfn("GET","/v2/orders?status=open&limit=500&nested=true")
    if not isinstance(poses,list) or not isinstance(orders,list) or len(orders)>=500:
        raise Unsafe("incomplete broker positions/order inventory")
    symbol=row["symbol"]
    if any(x.get("symbol")==symbol for x in poses+orders):
        raise Unsafe("symbol already occupied by another strategy/order")
    q=httpfn("GET","/v2/stocks/"+parse.quote(symbol,safe="")+"/quotes/latest?feed=sip",
             data=True)
    quote=q.get("quote") if isinstance(q,dict) else None
    if not isinstance(quote,dict): raise Unsafe("missing current SIP quote")
    when=utc(quote.get("t"))
    if not timedelta(0)<=now-when<=MAX_QUOTE_AGE: raise Unsafe("quote stale")
    bid,ask=money(str(quote.get("bp")),"bid"),money(str(quote.get("ap")),"ask")
    if bid>ask or (ask-bid)/ask>MAX_SPREAD: raise Unsafe("crossed/wide quote")
    limit=Decimal(str(row["limit_price"]))
    stop=Decimal(str(row["stop_loss"]))
    target=Decimal(str(row["profit_target"]))
    if not stop<bid<=ask<target: raise Unsafe("stop/target no longer consistent")
    if row["action"]=="BUY NOW" and ask>limit: raise Unsafe("limit would chase above allowed ask")
    qty=int(row["intended_qty"])
    cost=limit*qty
    if qty<1 or cost>MAX_RISK_NOTIONAL or Decimal(str(acct.get("cash","0")))<cost:
        raise Unsafe("cash/cap/quantity invalid")
    return {"account_fingerprint":sha256(expected.encode()).hexdigest()[:24],
            "bid":bid,"ask":ask,"quote_at":when}

def bracket_payload(row):
    """One Alpaca RTH DAY limit entry plus exact, broker-native TP/stop legs."""
    return {"symbol":row["symbol"],"side":"buy","type":"limit",
            "qty":str(int(row["intended_qty"])),"limit_price":str(row["limit_price"]),
            "time_in_force":"day","extended_hours":False,"order_class":"bracket",
            "take_profit":{"limit_price":str(row["profit_target"])},
            "stop_loss":{"stop_price":str(row["stop_loss"])},
            "client_order_id":row["client_order_id"]}

def process_once(now=None, connect=db_connect, httpfn=http):
    now=now or datetime.now(timezone.utc)
    require_commissioned()
    # Additional RTH, owner-cutoff and holiday checks before ANY broker call.
    if not entry_window(now): return {"status":"OUTSIDE_ENTRY_WINDOW","order_attempts":0}
    require_holiday(now)
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    outputs=[]
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM "+INTENT_TABLE+
                    " WHERE status='PENDING' ORDER BY issued_at_utc LIMIT 12")
        rows=cur.fetchall()
        for row in rows:
            rec_id=row["recommendation_id"]
            try:
                proof=preflight(row,now,httpfn)
            except (Unsafe,BrokerRejected,SubmissionUnknown) as exc:
                # Treat transient data failures as hold/no order; never infer fill.
                outputs.append({"recommendation_id":rec_id,"status":"NO_ORDER",
                                "reason":type(exc).__name__})
                continue
            try:
                conn.start_transaction()
                cur.execute("INSERT INTO "+CLAIM_TABLE+
                    "(session_date,paper_account_fingerprint,symbol,recommendation_id)"+
                    " VALUES(%s,%s,%s,%s)",(row["session_date"],
                    proof["account_fingerprint"],row["symbol"],rec_id))
                cur.execute("UPDATE "+INTENT_TABLE+" SET status='RESERVED_UNKNOWN',"+
                    "paper_account_fingerprint=%s,last_checked_utc=UTC_TIMESTAMP(6)"+
                    " WHERE recommendation_id=%s AND status='PENDING'",
                    (proof["account_fingerprint"],rec_id))
                if cur.rowcount!=1: raise Unsafe("reservation state raced")
                event(cur,rec_id,"PAPER_SUBMISSION_RESERVED",{"client_order_id":row["client_order_id"]})
                conn.commit()
            except Exception:
                conn.rollback()
                outputs.append({"recommendation_id":rec_id,"status":"DUPLICATE_OR_RACED"})
                continue
            # Unknown submission leaves RESERVED_UNKNOWN; never auto-retry.
            try:
                response=httpfn("POST","/v2/orders",bracket_payload(row))
                if (response.get("client_order_id")!=row["client_order_id"] or not response.get("id") or
                    response.get("order_class")!="bracket" or response.get("side")!="buy" or
                    response.get("symbol")!=row["symbol"]):
                    raise SubmissionUnknown("order identity/readback missing")
                cur.execute("UPDATE "+INTENT_TABLE+
                    " SET status='BROKER_ACCEPTED',broker_order_id=%s,broker_status=%s,"+
                    "broker_receipt_json=%s,last_checked_utc=UTC_TIMESTAMP(6)"+
                    " WHERE recommendation_id=%s",
                    (response["id"],response.get("status","accepted"),
                     json.dumps({"order_class":response.get("order_class"),
                      "client_order_id":response.get("client_order_id"),
                      "broker_order_id":response["id"],"status":response.get("status")}),
                     rec_id))
                event(cur,rec_id,"BROKER_ACCEPTED",{"broker_order_id":response["id"],
                      "status":response.get("status"),"order_class":response.get("order_class")})
                conn.commit()
                outputs.append({"recommendation_id":rec_id,"status":"BROKER_ACCEPTED"})
            except BrokerRejected as exc:
                cur.execute("UPDATE "+INTENT_TABLE+" SET status='BROKER_REJECTED',failure_code=%s "+
                    "WHERE recommendation_id=%s",(str(exc),rec_id))
                event(cur,rec_id,"BROKER_REJECTED",{"reason":str(exc)})
                conn.commit()
                outputs.append({"recommendation_id":rec_id,"status":"BROKER_REJECTED"})
            except (SubmissionUnknown,Unsafe) as exc:
                event(cur,rec_id,"BROKER_SUBMISSION_UNKNOWN",{"reason":type(exc).__name__,
                      "readback_required":True})
                conn.commit()
                outputs.append({"recommendation_id":rec_id,"status":"UNKNOWN_NO_RETRY"})
        return {"status":"SCAN_COMPLETE","results":outputs}
    finally: conn.close()

def expire_unsubmitted(now=None,connect=db_connect):
    """Persist no-order outcome; no broker calls, even without commissioning."""
    now=now or datetime.now(timezone.utc)
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT recommendation_id,client_order_id FROM "+INTENT_TABLE+
                    " WHERE status='PENDING' AND (expires_at_utc<=%s OR issued_at_utc<%s)"+
                    " ORDER BY issued_at_utc LIMIT 250",
                    (as_db_time(now),as_db_time(now-timedelta(minutes=5))))
        rows=cur.fetchall()
        conn.commit()
        for row in rows:
            cur.execute("UPDATE "+INTENT_TABLE+
                " SET status='NO_ORDER_EXPIRED',failure_code='STALE_OR_ENTRY_CUTOFF',"+
                " last_checked_utc=UTC_TIMESTAMP(6)"+
                " WHERE recommendation_id=%s AND status='PENDING'",(row["recommendation_id"],))
            if cur.rowcount!=1:
                conn.rollback()
                continue
            event(cur,row["recommendation_id"],"PAPER_INTENT_EXPIRED_NO_ORDER",
                  {"reason":"stale recommendation or owner entry cutoff",
                   "client_order_id":row["client_order_id"],"broker_order_id":None})
            conn.commit()
        return {"expired_without_order":len(rows)}
    except Exception:
        conn.rollback()
        raise
    finally:conn.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("intake","run-once","expire-only","status"))
    p.add_argument("--test-rollback",action="store_true")
    args=p.parse_args()
    if args.mode=="intake":
        import sys
        r=json.load(sys.stdin)
        print(json.dumps(ingest(r,test_rollback=args.test_rollback),sort_keys=True))
    elif args.mode=="run-once":
        print(json.dumps(process_once(),sort_keys=True))
    elif args.mode=="expire-only":
        print(json.dumps(expire_unsubmitted(),sort_keys=True))
    else:
        print(json.dumps({"router_commissioned":os.getenv("PAPER_BRIDGE_COMMISSIONED")=="1",
                          "active_broker_network":False,
                          "capability":"Alpaca PAPER RTH bracket only"}))
if __name__=="__main__": main()
