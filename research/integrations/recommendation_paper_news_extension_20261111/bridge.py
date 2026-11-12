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
from .news_clearance import require_clear, NewsBlocked
from .entry_tracking import pre_order, EntryExtended

DB_NAME = "securityprepper_trading"
CT = ZoneInfo("America/Chicago")
NY = ZoneInfo("America/New_York")
PAPER_HOST = "https://paper-api.alpaca.markets"
DATA_HOST = "https://data.alpaca.markets"
INTENT_TABLE = DB_NAME + ".sp_paper_rec_intents"
EVENT_TABLE = DB_NAME + ".sp_paper_rec_events"
CLAIM_TABLE = DB_NAME + ".sp_paper_rec_symbol_claims"
REBOUND_TASK = "Task - Five-Day Rebound Alerts"
EARN_TASK = "www3 Earnings Host Monitor"
TASKS = {"Task - Trading Opportunities "+x for x in ("One","Two","Three","Four")} | {REBOUND_TASK,EARN_TASK}
SYMBOL = re.compile(r"[A-Z][A-Z0-9.]{0,11}\Z")
REC_ID = re.compile(r"(?:TO-20[0-9]{6}-[A-Z0-9.]+-T[1-4]-[A-Z0-9]+|FDR5-20[0-9]{6}-[A-Z0-9.]+-[A-Z0-9]{8,32}|EARN-20[0-9]{6}-[A-Z0-9.]+-[A-F0-9]{12})\Z")
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
    return ("FR5-P-" if rec_id.startswith("FDR5-") else ("ERN-P-" if rec_id.startswith("EARN-") else "TO-P-"))+sha256((rec_id+"|PAPER|BUY|v1").encode()).hexdigest()[:40]

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
    if (r["source_task"]==REBOUND_TASK)!=(str(r["recommendation_id"]).startswith("FDR5-")):
        raise Unsafe("five-day rebound source and ID must match")
    if (r["source_task"]==EARN_TASK)!=(str(r["recommendation_id"]).startswith("EARN-")):
        raise Unsafe("earnings source and ID must match")
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
    if r["source_task"]==REBOUND_TASK:
        evidence=r.get("rebound_evidence")
        if not isinstance(evidence,dict):
            raise Unsafe("five-day rebound independently sourced evidence required")
        def num(name):
            try: v=Decimal(str(evidence[name]))
            except (KeyError,InvalidOperation,TypeError,ValueError):
                raise Unsafe("five-day rebound evidence missing/invalid: "+name)
            if not v.is_finite(): raise Unsafe("invalid rebound metric: "+name)
            return v
        if num("peak_to_current_decline_pct")<8:
            raise Unsafe("five-day decline below research threshold")
        if num("median_dollar_volume_20d")<20000000:
            raise Unsafe("insufficient five-day rebound liquidity")
        if (num("price_extension_pct")>Decimal("1.5")
            or num("expected_after_cost_gain_pct")<Decimal("1.5")
            or num("reward_risk_ratio")<2):
            raise Unsafe("extended entry or insufficient expected reward")
        if evidence.get("two_completed_5m_reversal_bars") is not True:
            raise Unsafe("completed price reversal confirmation missing")
        if evidence.get("negative_catalyst_veto_checked") is not True or evidence.get("veto_active") is not False:
            raise Unsafe("unverified news veto")
        if not str(evidence.get("catalyst_source","")).strip():
            raise Unsafe("rebound catalyst source missing")
        if (ask-bid)/ask>Decimal("0.005") or (limit-stop)/limit>Decimal("0.03"):
            raise Unsafe("rebound spread or stop risk exceeded")
        if (target-limit)/(limit-stop)<Decimal("2"):
            raise Unsafe("price levels violate 2:1 reward/risk")
        # Conservative estimate, NOT independently validated broker after-fee P&L.
        estimated_gain_pct=(target-limit)/limit*100-Decimal("0.5")
        if estimated_gain_pct<Decimal("1.5") or num("expected_after_cost_gain_pct")>estimated_gain_pct:
            raise Unsafe("projected after-cost gain exceeds plausible target")
        if not timedelta(0)<=now-utc(evidence.get("asof_utc"))<=timedelta(seconds=90):
            raise Unsafe("rebound evidence stale")
    if r["source_task"]==EARN_TASK:
        from .earnings_guard import gate as earnings_source_gate
        try:
            earnings_source_gate(r,now,dict(last=last,bid=bid,ask=ask,limit=limit,target=target,stop=stop))
        except (OSError,ValueError,KeyError,TypeError) as exc:
            raise Unsafe("independent earnings evidence gate rejected") from exc
    qty=int((MAX_RISK_NOTIONAL/limit).to_integral_value(rounding=ROUND_FLOOR))
    if not 1<=qty<=10000: raise Unsafe("notional/whole-share quantity invalid")
    # Entry will not silently carry across the overnight or the owner's cutoff.
    session=issued.astimezone(CT).date()
    expiry=datetime.combine(session,ENTRY_CUTOFF,CT).astimezone(timezone.utc)
    status="PENDING" if issued<expiry and issued.astimezone(CT).weekday()<5 else "NOT_PLACED_CUTOFF"
    if status=="PENDING" and r["source_task"]==REBOUND_TASK:
        status="REBOUND_ORDER_READY"
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

def ingest(r, now=None, connect=db_connect, test_rollback=False, clockfn=None):
    first_seen = clockfn() if clockfn else datetime.now(timezone.utc)
    s=validate_recommendation(r, now or first_seen)
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
            "rationale":s["rationale"],"time":s["issued"].isoformat(),"status":s["status"],
            "first_seen_at_utc":first_seen.isoformat(),
            "recommendation_to_intake_ms":int((first_seen-s["issued"]).total_seconds()*1000),
            "order_submitted":False})
        if s["source_task"]==REBOUND_TASK:
            event(cur,s["id"],"FIVE_DAY_REBOUND_SCREENED",r["rebound_evidence"])
        if s["source_task"]==EARN_TASK:
            event(cur,s["id"],"OFFICIAL_EARNINGS_AND_SIP_ATTESTED",{"earnings_event_id":r["earnings_event_id"],"official_release_source":"root-owned independent verified attestation","quote_at_utc":str(s["quote"].isoformat()),"order_submitted":False})
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
    expected_paper_account()

def expected_paper_account():
    """Never put the authorized broker account identity in a service environment."""
    root=os.environ.get("CREDENTIALS_DIRECTORY","")
    if not root:
        raise Unsafe("systemd protected expected account credential missing")
    p=Path(root)/"expected_paper_account"
    try: value=p.read_text(encoding="utf-8").strip()
    except (OSError,UnicodeError) as exc:
        raise Unsafe("broker account allowlist credential missing") from exc
    if not re.fullmatch(r"[a-fA-F0-9-]{36}",value):
        raise Unsafe("invalid PAPER account allowlist credential")
    return value

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

def unextended_entry_evidence(symbol,ask,now,httpfn):
    """Independent SIP last-completed-close check before a PAPER broker POST.

    Reuses the same licensed GET-only data connection as the existing quote.
    No other broker, account or optional external inventory is consulted.
    """
    from multi_broker_bridge.entry_extension import (
         fetch_completed_closes, examine, ExtensionRejected)
    from .entry_tracking import pct
    def daily_get(url,headers):
        if not url.startswith(DATA_HOST+"/v2/stocks/"):
            raise Unsafe("untrusted baseline GET URL")
        return httpfn("GET",url[len(DATA_HOST):],data=True)
    try:
        refs=fetch_completed_closes(now,[symbol],{},daily_get)
        return examine(symbol,ask,refs,now)
    except ExtensionRejected as exc:
        if str(exc).startswith("ALREADY_EXTENDED_"):
            try:
                verified_close=refs[symbol]["close"]
                measured=str(pct(ask,verified_close))
                raise Unsafe("ENTRY_ALREADY_EXTENDED_FROM_PREVIOUS_CLOSE:"+
                             measured+"_PCT") from exc
            except (KeyError,TypeError,ValueError):
                pass
        raise Unsafe("PREVIOUS_CLOSE_EVIDENCE_UNKNOWN") from exc
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise Unsafe("PREVIOUS_CLOSE_EVIDENCE_UNKNOWN") from exc

def preflight(row, now, httpfn=http):
    require_commissioned()
    require_holiday(now)
    if not entry_window(now): raise Unsafe("outside RTH/PAPER entry cutoff")
    issued=row["issued_at_utc"].replace(tzinfo=timezone.utc)
    expiration=row["expires_at_utc"].replace(tzinfo=timezone.utc)
    if now>=expiration or now-issued>timedelta(minutes=5):
        raise Unsafe("recommendation expired; no carryover")
    # Before requesting ANY broker inventory, independently qualify issuer/news.
    # Unknown or material adverse evidence blocks new BUY at this point.
    try:
        require_clear(row["symbol"],datetime.now(timezone.utc))
    except NewsBlocked as exc:
        raise Unsafe(exc.status+":"+exc.reason) from exc
    acct=httpfn("GET","/v2/account")
    expected=expected_paper_account()
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
    extension_evidence=unextended_entry_evidence(symbol,ask,now,httpfn)
    qty=int(row["intended_qty"])
    cost=limit*qty
    if qty<1 or cost>MAX_RISK_NOTIONAL or Decimal(str(acct.get("cash","0")))<cost:
        raise Unsafe("cash/cap/quantity invalid")
    if row["source_task"]==EARN_TASK:
        from .earnings_portfolio_guard import require as earnings_risk_require
        try:
            earnings_risk_require(acct,poses,orders,now,cost,expected)
        except (OSError,ValueError,KeyError,TypeError,ArithmeticError) as exc:
            raise Unsafe("receiving Alpaca PAPER loss/exposure gate unavailable") from exc
        # OTHER-broker information is informational only. Its absence, stale
        # state, malformed data, or inability to import its reader must NEVER
        # be an order veto when own-broker Alpaca checks independently pass.
        try:
            from .earnings_ibkr_guard import advisory as earnings_ibkr_advisory
            context=earnings_ibkr_advisory(symbol,now)
            allowed_statuses=("VERIFIED_NO_KNOWN_OVERLAP","VERIFIED_SAME_SYMBOL_OVERLAP",
                              "CORRELATED_EXPOSURE_NOT_CLEARED",
                              "UNAVAILABLE_STALE_OR_INCOMPLETE")
            if not isinstance(context,dict) or context.get("status") not in allowed_statuses:
                raise ValueError("untrusted optional broker advisory")
            cross_broker={"other_broker":"IBKR","status":context["status"],
                          "advisory_only":True,"blocks_order":False}
        except Exception:
            cross_broker={"other_broker":"IBKR","status":"UNAVAILABLE_STALE_OR_INCOMPLETE",
                          "advisory_only":True,"blocks_order":False}
    else:
        cross_broker=None
    try:
        tracking=pre_order(row,{"entry_extension":extension_evidence,
                                "bid":bid,"ask":ask,"quote_at":when})
    except EntryExtended as exc:
        raise Unsafe("ENTRY_ALREADY_EXTENDED_FROM_RECOMMENDATION:"+str(exc)) from exc
    except (ValueError,KeyError,TypeError) as exc:
        raise Unsafe("ENTRY_PRICE_PROVENANCE_UNKNOWN") from exc
    try:
        # Use decision clock after the broker and price checks, not a stale
        # scan-start clock; synthetic tests inject a mock via require_clear.
        news=require_clear(symbol,datetime.now(timezone.utc))
    except NewsBlocked as exc:
        raise Unsafe(exc.status+":"+exc.reason) from exc
    return {"other_broker_advisory":cross_broker,
            "news_clearance":news,"entry_tracking":tracking,
            "entry_extension":extension_evidence,
            "account_fingerprint":sha256(expected.encode()).hexdigest()[:24],
            "bid":bid,"ask":ask,"quote_at":when}

def bracket_payload(row):
    """One Alpaca RTH DAY limit entry plus exact, broker-native TP/stop legs."""
    return {"symbol":row["symbol"],"side":"buy","type":"limit",
            "qty":str(int(row["intended_qty"])),"limit_price":str(row["limit_price"]),
            "time_in_force":"day","extended_hours":False,"order_class":"bracket",
            "take_profit":{"limit_price":str(row["profit_target"])},
            "stop_loss":{"stop_price":str(row["stop_loss"])},
            "client_order_id":row["client_order_id"]}

def process_once(now=None, connect=db_connect, httpfn=http,
                 only_recommendation_id=None, clockfn=None):
    now=now or datetime.now(timezone.utc)
    def observation_now():
        # Real wall clock even if dispatcher supplied an earlier scan-start.
        # Broker-free unit tests inject clockfn; production never does.
        return clockfn() if clockfn else datetime.now(timezone.utc)
    require_commissioned()
    # Additional RTH, owner-cutoff and holiday checks before ANY broker call.
    if not entry_window(now): return {"status":"OUTSIDE_ENTRY_WINDOW","order_attempts":0}
    require_holiday(now)
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    outputs=[]
    try:
        cur=conn.cursor(dictionary=True)
        # Earnings recommendations are handled ONLY by an event-specific
        # order-first dispatcher. A generic timer may never auto-pick them.
        query=("SELECT * FROM "+INTENT_TABLE+
               " WHERE status='PENDING' AND source_task<>%s")
        params=(EARN_TASK,)
        if only_recommendation_id is not None:
            query=("SELECT * FROM "+INTENT_TABLE+
                   " WHERE status IN ('PENDING','REBOUND_ORDER_READY')"
                   " AND recommendation_id=%s")
            params=(only_recommendation_id,)
        query+=" ORDER BY issued_at_utc LIMIT 12"
        cur.execute(query,params)
        rows=cur.fetchall()
        # A SELECT with autocommit=False starts an implicit transaction.
        # End it before the subsequent explicit reservation transaction.
        conn.commit()
        for row in rows:
            rec_id=row["recommendation_id"]
            router_seen=observation_now()
            try:
                proof=preflight(row,now,httpfn)
            except (Unsafe,BrokerRejected,SubmissionUnknown) as exc:
                # All sources: material/unknown news or a chased entry is a
                # terminal NO_ORDER, not a retry on later timer iterations.
                rejection=str(exc)
                if rejection.startswith("NEWS_") or rejection.startswith("ENTRY_ALREADY_EXTENDED_"):
                    terminal=("NEWS_BLOCKED_NO_ORDER" if rejection.startswith("NEWS_")
                              else "EXTENDED_NO_ORDER")
                    cur.execute("UPDATE "+INTENT_TABLE+
                        " SET status=%s,failure_code=%s,last_checked_utc=UTC_TIMESTAMP(6)"+
                        " WHERE recommendation_id=%s AND status IN ('PENDING','REBOUND_ORDER_READY')",
                        (terminal,rejection[:120],rec_id))
                    if cur.rowcount==1:
                        event(cur,rec_id,"PAPER_PREFLIGHT_BLOCKED",{
                            "reason":rejection, "order_submitted":False,
                            "router_seen_at_utc":router_seen.isoformat()})
                    conn.commit()
                    outputs.append({"recommendation_id":rec_id,"status":"NO_ORDER",
                                    "reason":rejection})
                    continue
                # Fail closed for new rebound orders: no deferred timer buy on old evidence.
                if row["source_task"]==REBOUND_TASK:
                    cur.execute("UPDATE "+INTENT_TABLE+
                        " SET status='REBOUND_PREFLIGHT_NO_ORDER',failure_code=%s,"+
                        " last_checked_utc=UTC_TIMESTAMP(6)"+
                        " WHERE recommendation_id=%s AND status='REBOUND_ORDER_READY'",
                        (type(exc).__name__,rec_id))
                    if cur.rowcount==1:
                        event(cur,rec_id,"REBOUND_PREFLIGHT_NO_ORDER",
                              {"reason":type(exc).__name__,"order_submitted":False})
                    conn.commit()
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
                    " WHERE recommendation_id=%s AND status IN ('PENDING','REBOUND_ORDER_READY')",
                    (proof["account_fingerprint"],rec_id))
                if cur.rowcount!=1: raise Unsafe("reservation state raced")
                if (proof.get("news_clearance",{}).get("status")!="NEWS_CLEAR_ASOF"
                        or proof.get("entry_tracking",{}).get("price_gate")!="NO_CHASE"):
                    raise Unsafe("mandatory NEWS_CLEAR_ASOF/extension proof missing")
                first_seen=row.get("created_at_utc")
                if isinstance(first_seen,datetime):
                    first_seen=first_seen.replace(tzinfo=timezone.utc)
                else:
                    first_seen=None
                event(cur,rec_id,"PAPER_PREORDER_MEASURED",{
                    "router_seen_at_utc":router_seen.isoformat(),
                    "first_seen_at_utc":first_seen.isoformat() if first_seen else None,
                    "recommendation_issued_at_utc":row["issued_at_utc"].replace(tzinfo=timezone.utc).isoformat(),
                    "price":proof["entry_tracking"],"news":proof["news_clearance"],
                    "order_submitted":False})
                event(cur,rec_id,"PAPER_SUBMISSION_RESERVED",{"client_order_id":row["client_order_id"],
                   "other_broker_advisory":proof.get("other_broker_advisory"),
                   "entry_extension":proof.get("entry_extension"),
                   "news_status":proof["news_clearance"]["status"]})
                conn.commit()
            except Exception:
                conn.rollback()
                outputs.append({"recommendation_id":rec_id,"status":"DUPLICATE_OR_RACED"})
                continue
            # Immediately before placing an order, re-validate the trusted
            # news attestation and quote/cutoff. Never accept stale clearance
            # or infer broker acceptance/filled shares from sending POST.
            post_started=observation_now()
            try:
                if (post_started>=row["expires_at_utc"].replace(tzinfo=timezone.utc)
                    or not entry_window(post_started) or
                    post_started-now>timedelta(seconds=45)):
                    raise Unsafe("ENTRY_WINDOW_CHANGED_BEFORE_POST")
                quote_time=proof.get("quote_at")
                if not isinstance(quote_time,datetime) or not timedelta(0)<=post_started-quote_time<=MAX_QUOTE_AGE:
                    raise Unsafe("QUOTE_STALE_BEFORE_POST")
                final_news=require_clear(row["symbol"],post_started)
                if final_news.get("status")!="NEWS_CLEAR_ASOF":
                    raise Unsafe("NEWS_UNKNOWN_BEFORE_POST")
            except (NewsBlocked,Unsafe) as exc:
                reason=(exc.status+":"+exc.reason if isinstance(exc,NewsBlocked)
                        else str(exc))
                cur.execute("UPDATE "+INTENT_TABLE+
                    " SET status='NO_ORDER_PREPOST_RECHECK',failure_code=%s,"+
                    "last_checked_utc=UTC_TIMESTAMP(6) WHERE recommendation_id=%s"+
                    " AND status='RESERVED_UNKNOWN'",(reason[:120],rec_id))
                event(cur,rec_id,"PAPER_PREPOST_BLOCKED",{
                    "reason":reason,"order_submitted":False,
                    "post_would_start_at_utc":post_started.isoformat()})
                conn.commit()
                outputs.append({"recommendation_id":rec_id,"status":"NO_ORDER",
                                "reason":reason})
                continue
            first_seen=row.get("created_at_utc")
            first_seen=(first_seen.replace(tzinfo=timezone.utc)
                        if isinstance(first_seen,datetime) else None)
            issued=row["issued_at_utc"].replace(tzinfo=timezone.utc)
            post_metrics={
                "post_started_at_utc":post_started.isoformat(),
                "intake_seen_to_post_ms":int((post_started-first_seen).total_seconds()*1000)
                                         if first_seen else None,
                "source_issued_to_post_ms":int((post_started-issued).total_seconds()*1000),
                "news_status":final_news["status"],
                "news_evidence_sha256":final_news["evidence_sha256"],
                "preorder_price":proof["entry_tracking"],
                "broker_status":"NOT_YET_ACKNOWLEDGED","broker_filled":False}
            event(cur,rec_id,"PAPER_ORDER_POST_STARTED",post_metrics)
            conn.commit()  # durable timestamp BEFORE network; never retry an unknown POST
            # Unknown submission leaves RESERVED_UNKNOWN; never auto-retry.
            try:
                response=httpfn("POST","/v2/orders",bracket_payload(row))
                if (response.get("client_order_id")!=row["client_order_id"] or not response.get("id") or
                    response.get("order_class")!="bracket" or response.get("side")!="buy" or
                    response.get("symbol")!=row["symbol"] or response.get("type")!="limit" or
                    response.get("time_in_force")!="day" or response.get("extended_hours") is not False or
                    Decimal(str(response.get("limit_price","0")))!=Decimal(str(row["limit_price"])) or
                    Decimal(str(response.get("qty","0")))!=Decimal(str(row["intended_qty"]))):
                    raise SubmissionUnknown("PAPER bracket parent receipt mismatch")
                # A broker acknowledgement is not sufficient; read the same
                # parent ID back independently before claiming receipt success.
                readback=httpfn("GET","/v2/orders/"+parse.quote(response["id"],safe="")+"?nested=true")
                if (not isinstance(readback,dict) or readback.get("id")!=response["id"] or
                    readback.get("client_order_id")!=row["client_order_id"] or
                    readback.get("order_class")!="bracket" or readback.get("symbol")!=row["symbol"] or
                    readback.get("side")!="buy"):
                    raise SubmissionUnknown("PAPER bracket broker readback missing/mismatched")
                cur.execute("UPDATE "+INTENT_TABLE+
                    " SET status='BROKER_ACCEPTED',broker_order_id=%s,broker_status=%s,"+
                    "broker_receipt_json=%s,last_checked_utc=UTC_TIMESTAMP(6)"+
                    " WHERE recommendation_id=%s",
                    (response["id"],response.get("status","accepted"),
                     json.dumps({"order_class":response.get("order_class"),
                      "client_order_id":response.get("client_order_id"),
                      "broker_order_id":response["id"],"status":response.get("status")}),
                     rec_id))
                accepted_at=observation_now()
                event(cur,rec_id,"BROKER_ACCEPTED",{"broker_order_id":response["id"],
                      "status":response.get("status"),"order_class":response.get("order_class"),
                      "broker_accepted_at_utc":accepted_at.isoformat(),
                      "source_issued_to_accepted_ms":int((accepted_at-issued).total_seconds()*1000),
                      "first_seen_to_accepted_ms":int((accepted_at-first_seen).total_seconds()*1000)
                                                   if first_seen else None,
                      "post_to_broker_accepted_ms":int((accepted_at-post_started).total_seconds()*1000),
                      "not_a_fill":True,"preorder_price":proof["entry_tracking"]})
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
                    " WHERE status IN ('PENDING','REBOUND_ORDER_READY') AND (expires_at_utc<=%s OR issued_at_utc<%s)"+
                    " ORDER BY issued_at_utc LIMIT 250",
                    (as_db_time(now),as_db_time(now-timedelta(minutes=5))))
        rows=cur.fetchall()
        conn.commit()
        for row in rows:
            cur.execute("UPDATE "+INTENT_TABLE+
                " SET status='NO_ORDER_EXPIRED',failure_code='STALE_OR_ENTRY_CUTOFF',"+
                " last_checked_utc=UTC_TIMESTAMP(6)"+
                " WHERE recommendation_id=%s AND status IN ('PENDING','REBOUND_ORDER_READY')",(row["recommendation_id"],))
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
