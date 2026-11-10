"""Read-only order/leg/FILL reconciler for the isolated Alpaca PAPER bridge.

Does not submit/cancel/replace orders, flatten positions, or infer fees.
Any unclear ownership/leg status remains unverified and blocks GO.
"""
from __future__ import annotations
from decimal import Decimal,InvalidOperation
from urllib.parse import quote
from .bridge import Unsafe,SubmissionUnknown,BrokerRejected,EVENT_TABLE,INTENT_TABLE,event,db_connect,http
import json

TERMINAL={"canceled","expired","rejected","done_for_day","filled"}
def qty(x):
    try: d=Decimal(str(x))
    except (InvalidOperation,ValueError): raise Unsafe("invalid broker quantity")
    if not d.is_finite() or d<0: raise Unsafe("invalid broker quantity")
    return d

def check_parent(row,parent):
    if (not isinstance(parent,dict) or parent.get("id")!=row["broker_order_id"]
        or parent.get("client_order_id")!=row["client_order_id"]
        or parent.get("symbol")!=row["symbol"] or parent.get("side")!="buy"
        or parent.get("order_class")!="bracket" or parent.get("type")!="limit"
        or str(parent.get("limit_price"))!=str(row["limit_price"])):
        raise Unsafe("PAPER parent identity or bracket parameters mismatch")

def assess(row,parent,activities):
    """No fabricated fee/net P&L. Requires activity UUIDs and order UUIDs."""
    check_parent(row,parent)
    legs=parent.get("legs") or []
    if not isinstance(legs,list): raise Unsafe("malformed bracket legs")
    allowed={parent["id"]}
    targets=[];stops=[]
    for leg in legs:
        if not isinstance(leg,dict) or not leg.get("id") or leg.get("symbol")!=row["symbol"]:
            raise Unsafe("unattributed bracket leg")
        if leg.get("side")!="sell": raise Unsafe("nonexit bracket leg")
        allowed.add(leg["id"])
        if leg.get("type")=="limit":
            if Decimal(str(leg.get("limit_price","0")))!=Decimal(str(row["profit_target"])):
                raise Unsafe("bracket target differs from recommendation")
            targets.append(leg)
        elif leg.get("type") in ("stop","stop_limit"):
            if Decimal(str(leg.get("stop_price","0")))!=Decimal(str(row["stop_loss"])):
                raise Unsafe("bracket stop differs from recommendation")
            stops.append(leg)
        else: raise Unsafe("unknown bracket leg")
    seen=set();filled_buy=Decimal(0);filled_sell=Decimal(0)
    buy_notional=Decimal(0);sell_notional=Decimal(0)
    last_exit=None
    for a in sorted(activities,key=lambda a:str(a.get("transaction_time",""))):
        if not isinstance(a,dict) or a.get("activity_type")!="FILL":
            raise Unsafe("unexpected broker activity type")
        oid=a.get("order_id")
        if oid not in allowed or not a.get("id") or a["id"] in seen:
            raise Unsafe("unknown/duplicate fill activity order UUID")
        seen.add(a["id"])
        if a.get("symbol")!=row["symbol"]: raise Unsafe("fill symbol mismatch")
        n=qty(a.get("qty"));p=qty(a.get("price"))
        if n<=0 or p<=0: raise Unsafe("bad fill quantity or price")
        side=a.get("side")
        if side=="buy" and oid==parent["id"]:
            filled_buy+=n;buy_notional+=n*p
        elif side=="sell" and oid!=parent["id"]:
            filled_sell+=n;sell_notional+=n*p
            last_exit=a.get("transaction_time")
        else: raise Unsafe("activity side/order UUID mismatch")
        if filled_sell>filled_buy: raise Unsafe("sell before attributable buy")
    if filled_buy>qty(row["intended_qty"]):
        raise Unsafe("bridge fill exceeds intended whole-share quantity")
    if filled_buy!=qty(parent.get("filled_qty","0")):
        raise Unsafe("incomplete or conflicting parent FILL activity readback")
    if filled_buy==0:
        return {"state":"UNFILLED" if parent.get("status") not in TERMINAL else "UNFILLED_TERMINAL",
                "fills":len(seen)}
    if filled_sell<filled_buy:
        state=("PARTIAL_UNPROTECTED" if filled_buy<qty(row["intended_qty"]) or
               len(targets)!=1 or len(stops)!=1 else "OPEN_WITH_BRACKET")
        return {"state":state,"buy_qty":str(filled_buy),"sell_qty":str(filled_sell),
                "unprotected_partial":state=="PARTIAL_UNPROTECTED","fills":len(seen)}
    if filled_sell>filled_buy: raise Unsafe("broker oversell")
    return {"state":"CLOSED_NEEDS_FEE_RECON","buy_qty":str(filled_buy),
            "sell_qty":str(filled_sell),"gross_pnl":str(sell_notional-buy_notional),
            "fees_verified":False,"net_pnl":None,"exit_at":last_exit,
            "fill_activity_count":len(seen),"fill_activity_ids":sorted(seen)}

def fetch_all_activities(order_id,httpfn):
    # Restrict to one attributable Alpaca order. 20 full pages => fail closed.
    if not isinstance(order_id,str) or not order_id: raise Unsafe("missing order id")
    collected=[];token=None;tokens=set()
    for _ in range(20):
        p="/v2/account/activities?activity_types=FILL&order_id="+quote(order_id,safe="")+"&page_size=100&direction=asc"
        if token: p+="&page_token="+quote(token,safe="")
        page=httpfn("GET",p)
        if not isinstance(page,list): raise Unsafe("malformed FILL activity page")
        collected+=page
        if len(page)<100: return collected
        token=page[-1].get("id")
        if not token or token in tokens: raise Unsafe("nonadvancing activity pagination")
        tokens.add(token)
    raise Unsafe("activity page limit exceeded: incomplete readback")

def reconcile_one(row,httpfn=http):
    if not row.get("broker_order_id"):
        raise Unsafe("no verified broker order ID: cannot reconcile")
    oid=row["broker_order_id"]
    parent=httpfn("GET","/v2/orders/"+quote(oid,safe="")+"?nested=true")
    check_parent(row,parent)
    children=parent.get("legs") or []
    ids=[oid]+[x.get("id") for x in children]
    acts=[]
    for order_id in ids:
        acts.extend(fetch_all_activities(order_id,httpfn))
    return assess(row,parent,acts)

def reconcile_once(connect=db_connect,httpfn=http):
    # Separate GET-only reconciliation, even for uncertain previous attempts.
    # REQUIRE account allowlist: no unscoped account audit.
    import os
    expected=os.getenv("PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT")
    if not expected: raise Unsafe("PAPER account allowlist missing")
    acct=httpfn("GET","/v2/account")
    if acct.get("id")!=expected: raise Unsafe("PAPER identity mismatch")
    conn=connect("PAPER_BRIDGE_ROUTER_CNF")
    output=[]
    try:
        cur=conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM "+INTENT_TABLE+
            " WHERE status IN ('BROKER_ACCEPTED','RESERVED_UNKNOWN','PARTIAL_UNPROTECTED',"+
            "'OPEN_WITH_BRACKET','CLOSED_NEEDS_FEE_RECON') ORDER BY issued_at_utc LIMIT 50")
        rows=cur.fetchall()
        conn.commit()
        for row in rows:
            try:
                if row["status"]=="RESERVED_UNKNOWN" and not row.get("broker_order_id"):
                    # Readback only by deterministic client ID; DO NOT retransmit.
                    parent=httpfn("GET","/v2/orders:by_client_order_id?client_order_id="+
                                  quote(row["client_order_id"],safe=""))
                    if parent.get("client_order_id")!=row["client_order_id"] or not parent.get("id"):
                        raise Unsafe("unverified previously ambiguous submission")
                    row["broker_order_id"]=parent["id"]
                result=reconcile_one(row,httpfn)
                current=result["state"]
                cur.execute("UPDATE "+INTENT_TABLE+
                    " SET status=%s,broker_status=%s,broker_order_id=%s,last_checked_utc=UTC_TIMESTAMP(6)"+
                    " WHERE recommendation_id=%s",(current,current,row["broker_order_id"],
                                                    row["recommendation_id"]))
                event(cur,row["recommendation_id"],"BROKER_FILL_READBACK",result)
                conn.commit()
                output.append({"recommendation_id":row["recommendation_id"],"state":current})
            except (Unsafe,SubmissionUnknown,BrokerRejected) as exc:
                conn.rollback()
                output.append({"recommendation_id":row["recommendation_id"],
                               "state":"UNKNOWN_READBACK","reason":type(exc).__name__})
        return output
    finally:conn.close()

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true",required=True)
    p.parse_args()
    print(json.dumps(reconcile_once(),sort_keys=True))
if __name__=="__main__":main()
