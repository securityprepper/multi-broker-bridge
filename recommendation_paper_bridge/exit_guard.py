"""Isolated Alpaca PAPER mandatory-exit guard; no LIVE URLs.

Requires separate commissioning, exclusive lot ownership, and idempotent SQL
reservation. Never retries uncertain broker cancellation/submission.
"""
from __future__ import annotations
from datetime import datetime,timezone,time
from decimal import Decimal
from hashlib import sha256
from urllib.parse import quote
import json,os,re
from .bridge import (
    Unsafe,SubmissionUnknown,BrokerRejected,require_commissioned,db_connect,
    CT,NY,INTENT_TABLE,event,http
)
from .reconcile import check_parent,assess,fetch_all_activities

FLAT_TABLE="securityprepper_trading.sp_paper_rec_flatten_intents"
UUID=re.compile(r"[a-f0-9-]{36}\Z",re.I)
OPEN_STATES={"new","accepted","pending_new","partially_filled","held","pending_replace","pending_cancel","calculated"}
def broker_uuid(value):
    if not isinstance(value,str) or not UUID.fullmatch(value):
        raise Unsafe("unexpected broker UUID")
    return value

def flat_id(rec):
    return "TO-F-"+sha256((rec+"|PAPER|FLATTEN|v1").encode()).hexdigest()[:40]

def exclusively_owned(symbol,remaining,positions,working,allowed):
    """Reject aggregate positions that may contain any other strategy's shares."""
    if not isinstance(positions,list) or not isinstance(working,list) or len(working)>=500:
        raise Unsafe("incomplete account positions/open order inventory")
    matches=[p for p in positions if p.get("symbol")==symbol]
    if len(matches)!=1 or Decimal(str(matches[0].get("qty","0")))!=remaining:
        raise Unsafe("aggregate position != independently matched strategy-owned shares")
    if matches[0].get("side")!="long":
        raise Unsafe("not a verified long")
    for o in working:
        if o.get("symbol")==symbol and o.get("id") not in allowed:
            raise Unsafe("unrelated open broker order on same symbol")
    return True

def plan(row,parent,activities,positions,working,now):
    check_parent(row,parent)
    check=assess(row,parent,activities)
    buy=Decimal(check.get("buy_qty","0"))
    sold=Decimal(check.get("sell_qty","0"))
    local=now.astimezone(CT)
    if local.weekday()>4 or not time(8,30)<=local.time()<time(15,0):
        return {"action":"SAFETY_ESCALATE","reason":"unavailable regular-hours close"}
    if check["state"]=="CLOSED_NEEDS_FEE_RECON":
        return {"action":"NONE","reason":"position already closed"}
    if buy==0:
        if local.time()>=time(13,15) and parent.get("status") in OPEN_STATES:
            return {"action":"CANCEL_UNFILLED_PARENT","quantity":"0"}
        return {"action":"NONE","reason":"unfilled parent"}
    if buy<sold: raise Unsafe("oversold attributable fills")
    remaining=buy-sold
    if not remaining: return {"action":"NONE","reason":"fully exited"}
    if local.time()<time(13,40) and check["state"]!="PARTIAL_UNPROTECTED":
        return {"action":"NONE","reason":"verified protective bracket still active"}
    if local.time()<time(8,30): raise Unsafe("extended-hours synthetic exits not authorized")
    allowed={parent["id"]}|{x.get("id") for x in parent.get("legs",[]) or []}
    exclusively_owned(row["symbol"],remaining,positions,working,allowed)
    return {"action":"FLATTEN_EXCLUSIVE_PAPER","quantity":str(remaining),
            "stop_bracket_child_ids":[x["id"] for x in parent.get("legs",[]) or []
                                    if x.get("status") in OPEN_STATES],
            "parent_cancel_needed":parent.get("status") in OPEN_STATES,
            "reason":"PARTIAL_UNPROTECTED" if check["state"]=="PARTIAL_UNPROTECTED"
                     else "OWNER_1340_MANDATORY_FLAT"}

def authenticated_account(httpfn):
    expected=os.environ.get("PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT")
    if not expected: raise Unsafe("PAPER account allowlist required")
    a=httpfn("GET","/v2/account")
    if a.get("id")!=expected or a.get("trading_blocked") is not False:
        raise Unsafe("wrong/blocked PAPER account")
    return expected

def receipt(row,httpfn=http):
    oid=broker_uuid(row["broker_order_id"])
    parent=httpfn("GET","/v2/orders/"+oid+"?nested=true")
    check_parent(row,parent)
    ids=[oid]+[broker_uuid(x["id"]) for x in (parent.get("legs") or [])]
    activities=[]
    for i in ids: activities+=fetch_all_activities(i,httpfn)
    return parent,activities

def cancel_verified(order_id,httpfn):
    oid=broker_uuid(order_id)
    try:
        httpfn("DELETE","/v2/orders/"+oid)
    except BrokerRejected:
        # Already canceled/filled is NOT an authorization to assume success.
        pass
    o=httpfn("GET","/v2/orders/"+oid)
    if o.get("id")!=oid or o.get("status") not in ("canceled","expired","filled"):
        raise SubmissionUnknown("order cancellation not verified")
    return o

def flatten_once(row,now=None,connect=db_connect,httpfn=http):
    now=now or datetime.now(timezone.utc)
    require_commissioned()
    authenticated_account(httpfn)
    parent,activities=receipt(row,httpfn)
    positions=httpfn("GET","/v2/positions")
    working=httpfn("GET","/v2/orders?status=open&limit=500")
    decision=plan(row,parent,activities,positions,working,now)
    if decision["action"]=="NONE": return decision
    if decision["action"]=="SAFETY_ESCALATE":
        raise Unsafe("out-of-session position risk: no unsupported sell")
    if decision["action"]=="CANCEL_UNFILLED_PARENT":
        cancel_verified(parent["id"],httpfn)
        return {"action":"UNFILLED_CANCEL_VERIFIED"}
    if decision["action"]!="FLATTEN_EXCLUSIVE_PAPER":
        raise Unsafe("unrecognized exit action")
    # Reserve once durably BEFORE altering any broker order. A crash leaves
    # an UNKNOWN state that must be broker-reconciled rather than retried.
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    rec=row["recommendation_id"]
    try:
        cur=conn.cursor()
        conn.start_transaction()
        cur.execute("INSERT INTO "+FLAT_TABLE+
            "(recommendation_id,client_order_id,quantity,status,evidence_json) VALUES(%s,%s,%s,%s,%s)",
            (rec,flat_id(rec),decision["quantity"],"FLATTEN_UNKNOWN_RESERVED",
             json.dumps({"reason":decision["reason"],"asof_utc":now.isoformat()})))
        event(cur,rec,"FLATTEN_RESERVED",{"client_order_id":flat_id(rec),
            "quantity":decision["quantity"],"reason":decision["reason"]})
        conn.commit()
    except Exception:
        conn.rollback()
        return {"action":"NO_RETRY_EXISTING_OR_UNCERTAIN_FLATTEN"}
    finally: conn.close()
    for oid in decision["stop_bracket_child_ids"]:
        cancel_verified(oid,httpfn)
    if decision["parent_cancel_needed"]:
        cancel_verified(parent["id"],httpfn)
    # Verify the bracket was actually canceled and that no stop filled in
    # the meantime, THEN re-establish exact exclusive account position size.
    parent2,activities2=receipt(row,httpfn)
    result=assess(row,parent2,activities2)
    remaining=Decimal(result.get("buy_qty","0"))-Decimal(result.get("sell_qty","0"))
    if remaining<=0:
        return {"action":"NO_MARKET_SELL_ALREADY_FLAT"}
    positions2=httpfn("GET","/v2/positions")
    working2=httpfn("GET","/v2/orders?status=open&limit=500")
    exclusively_owned(row["symbol"],remaining,positions2,working2,set())
    if remaining!=Decimal(decision["quantity"]):
        raise SubmissionUnknown("fill quantity changed after flatten reservation")
    if not (time(8,30)<=now.astimezone(CT).time()<time(15,0)):
        raise Unsafe("mandatory market order outside regular session")
    payload={"symbol":row["symbol"],"side":"sell","type":"market",
             "qty":str(remaining),"time_in_force":"day",
             "extended_hours":False,"client_order_id":flat_id(rec)}
    order=httpfn("POST","/v2/orders",payload)
    if order.get("client_order_id")!=flat_id(rec) or not order.get("id"):
        raise SubmissionUnknown("flatten response unknown; do not retry")
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    try:
        cur=conn.cursor()
        cur.execute("UPDATE "+FLAT_TABLE+
            " SET status='FLATTEN_BROKER_ACK',paper_broker_order_id=%s,"+
            "checked_at_utc=UTC_TIMESTAMP(6) WHERE recommendation_id=%s"+
            " AND status='FLATTEN_UNKNOWN_RESERVED'",(order["id"],rec))
        if cur.rowcount!=1: raise Unsafe("flatten acknowledgement reservation missing")
        event(cur,rec,"FLATTEN_BROKER_ACK",{"client_order_id":flat_id(rec),
            "broker_order_id":order["id"],"broker_status":order.get("status")})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally: conn.close()
    return {"action":"FLATTEN_SUBMITTED_VERIFY_FILL","client_order_id":flat_id(rec),
            "broker_order_id":order["id"],"quantity":str(remaining)}

def readback_flatten(recommendation_id, client_order_id, quantity, httpfn=http):
    """No second SELL. Read broker status only; report unresolved after 14:00."""
    if client_order_id!=flat_id(recommendation_id):
        raise Unsafe("noncanonical flatten client order ID")
    a=authenticated_account(httpfn)
    order=httpfn("GET","/v2/orders:by_client_order_id?client_order_id="+quote(client_order_id,safe=""))
    if not isinstance(order,dict) or order.get("client_order_id")!=client_order_id:
        raise SubmissionUnknown("flatten order identity unknown")
    n=Decimal(str(order.get("filled_qty","0")))
    if n<0 or n>Decimal(str(quantity)):
        raise Unsafe("flatten quantity mismatch")
    if n==Decimal(str(quantity)) and order.get("status")=="filled":
        return {"status":"FLATTEN_FILLED","broker_order_id":order["id"],
                "filled_qty":str(n)}
    if order.get("status") in ("canceled","expired","rejected"):
        return {"status":"CRITICAL_FLATTEN_FAILED","broker_order_id":order.get("id"),
                "filled_qty":str(n)}
    return {"status":"FLATTEN_UNCONFIRMED","broker_order_id":order.get("id"),
            "filled_qty":str(n)}


def run_guard_once(now=None,connect=db_connect,httpfn=http):
    """Continuous PAPER protection/cutoff watch; no automatic unknown retries."""
    now=now or datetime.now(timezone.utc)
    require_commissioned()
    authenticated_account(httpfn)
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM securityprepper_trading.sp_paper_rec_intents "+
            "WHERE broker_order_id IS NOT NULL AND status IN "+
            "('BROKER_ACCEPTED','OPEN_WITH_BRACKET','PARTIAL_UNPROTECTED',"+
            "'UNFILLED','RESERVED_UNKNOWN','UNFILLED_TERMINAL') "+
            "ORDER BY CASE WHEN status='PARTIAL_UNPROTECTED' THEN 0 "+
            "WHEN status IN ('BROKER_ACCEPTED','OPEN_WITH_BRACKET') THEN 1 ELSE 2 END, "+
            "issued_at_utc LIMIT 76")
        rows=cur.fetchall()
        conn.commit()
        if len(rows)>75:
            raise Unsafe("PAPER exit-guard backlog exceeds 75; no silent uncovered positions")
        results=[]
        for row in rows:
            rec=row["recommendation_id"]
            cur.execute("SELECT * FROM "+FLAT_TABLE+" WHERE recommendation_id=%s",(rec,))
            existing=cur.fetchone()
            conn.commit()
            if existing:
                # A prior submission may have been uncertain. Read it back,
                # but NEVER issue another sell with this recommendation key.
                try:
                    x=readback_flatten(rec,existing["client_order_id"],
                                      existing["quantity"],httpfn)
                    cur.execute("UPDATE "+FLAT_TABLE+
                        " SET status=%s,checked_at_utc=UTC_TIMESTAMP(6),"+
                        "paper_broker_order_id=COALESCE(%s,paper_broker_order_id)"+
                        " WHERE recommendation_id=%s",
                        (x["status"],x["broker_order_id"],rec))
                    event(cur,rec,"FLATTEN_READBACK",x)
                    conn.commit()
                    results.append({"recommendation_id":rec,**x})
                except (Unsafe,SubmissionUnknown,BrokerRejected) as e:
                    conn.rollback()
                    results.append({"recommendation_id":rec,
                                    "status":"CRITICAL_FLATTEN_READBACK_UNKNOWN",
                                    "reason":type(e).__name__})
                continue
            try:
                x=flatten_once(row,now,connect,httpfn)
                if x.get("action")=="UNFILLED_CANCEL_VERIFIED":
                    cur.execute("UPDATE securityprepper_trading.sp_paper_rec_intents"+
                        " SET status='UNFILLED_CANCELED',last_checked_utc=UTC_TIMESTAMP(6)"+
                        " WHERE recommendation_id=%s",(rec,))
                    event(cur,rec,"UNFILLED_CANCELED_AT_CUTOFF",{"broker_order_id":row["broker_order_id"]})
                    conn.commit()
                results.append({"recommendation_id":rec,**x})
            except (Unsafe,SubmissionUnknown,BrokerRejected) as e:
                conn.rollback()
                results.append({"recommendation_id":rec,"status":"CRITICAL_EXIT_GUARD_UNKNOWN",
                                "reason":type(e).__name__})
        return {"checked":len(rows),"outcomes":results}
    finally:conn.close()

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true",required=True)
    x=p.parse_args()
    print(json.dumps(run_guard_once(),sort_keys=True))
if __name__=="__main__":main()
