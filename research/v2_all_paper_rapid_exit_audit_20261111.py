"""Pure offline order-level PAPER round-trip reconciliation; NO network, broker calls or orders.

Never merge MBB and FDR positions, invent an exit reason from price, count
each partial FILL activity as a new trade, or mistake order final-fill time for
the timestamp of every partial execution.
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
import argparse
import json
from pathlib import Path

CT=ZoneInfo("America/Chicago")

def source_for(client_id: str) -> str:
    if not isinstance(client_id,str) or not client_id:
        raise ValueError("missing client_order_id")
    if client_id.startswith("MBB-"): return "MBB"
    if client_id.startswith("FDR-"): return "FDR"
    return "OTHER_UNLINKED"

def parsed_timestamp(s: str) -> datetime:
    if not isinstance(s,str): raise ValueError("missing filled_at")
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None: raise ValueError("naive fill timestamp")
    return t.astimezone(CT)

def session_day(t: datetime) -> str:
    if t.tzinfo is None: raise ValueError("naive local time")
    local=t.astimezone(CT)
    return (local.date()+timedelta(days=1) if local.hour>=19 else local.date()).isoformat()

def positive_decimal(v, label: str) -> Decimal:
    try: x=Decimal(str(v))
    except (InvalidOperation,ValueError,TypeError):raise ValueError("invalid "+label) from None
    if not x.is_finite() or x<=0: raise ValueError("invalid "+label)
    return x

def audit(snapshot: dict) -> dict:
    if (snapshot.get("paper_only") is not True
        or snapshot.get("broker_verified") is not True
        or snapshot.get("recent_orders_complete") is not True
        or not isinstance(snapshot.get("recent_orders"),list)
        or len(snapshot["recent_orders"])>=500):
        raise ValueError("broker scope or coverage cannot be verified")
    filled=[]; seen=set(); nonfilled=0
    for o in snapshot["recent_orders"]:
        if not isinstance(o,dict):raise ValueError("malformed order")
        cid=o.get("client_order_id")
        if cid in seen:raise ValueError("duplicate client id")
        if not isinstance(cid,str) or not cid:raise ValueError("missing client id")
        seen.add(cid)
        if o.get("status")!="filled":
            nonfilled+=1
            continue
        sym=o.get("symbol")
        if not isinstance(sym,str) or not sym.isupper():raise ValueError("missing symbol")
        side=o.get("side")
        if side not in ("buy","sell"):raise ValueError("invalid side")
        at=parsed_timestamp(o.get("filled_at"))
        qty=positive_decimal(o.get("filled_qty"),"filled qty")
        price=positive_decimal(o.get("filled_avg_price"),"filled average price")
        filled.append((at,cid,source_for(cid),session_day(at),sym,side,qty,price))
    filled.sort(key=lambda row:(row[0],row[1]))
    lots=defaultdict(deque)
    closed=[];unmatched=[]
    for at,cid,source,day,sym,side,qty,px in filled:
        key=(source,day,sym)
        if side=="buy":
            lots[key].append([qty,px,at,cid])
            continue
        remaining=qty
        while remaining:
            if not lots[key]:
                unmatched.append({"day":day,"source":source,"symbol":sym,"kind":"SELL_WITHOUT_SAME_SOURCE_BUY"})
                break
            entry=lots[key][0]
            consumed=min(entry[0],remaining)
            entry[0]-=consumed; remaining-=consumed
            gross=(px-entry[1])*consumed
            hold=(at-entry[2]).total_seconds()/60
            if hold<0:raise ValueError("negative hold")
            closed.append({"day":day,"source":source,"symbol":sym,
                           "entry_client_id":entry[3],"exit_client_id":cid,
                           "quantity":str(consumed),
                           "entry_price":str(entry[1]),"exit_price":str(px),
                           "entry_final_fill_ct":entry[2].isoformat(),
                           "exit_final_fill_ct":at.isoformat(),
                           "order_final_fill_hold_minutes":round(hold,4),
                           "gross_pnl_usd":str(gross),
                           "exit_reason":"UNKNOWN_ORIGINAL_DECISION_NOT_IN_ORDER_EXPORT"})
            if not entry[0]:lots[key].popleft()
    for (src,day,sym),values in lots.items():
        if values:
            unmatched.append({"day":day,"source":src,"symbol":sym,
                              "kind":"OPEN_OR_UNPAIRED_BUY_ORDER"})
    cohorts={}
    by=defaultdict(list)
    for row in closed:
        by[(row["day"],row["source"])].append(row)
    for (day,src),rows in sorted(by.items()):
        cohorts[day+"|"+src]={
            "count":len(rows),
            "positive_gross_count":sum(Decimal(r["gross_pnl_usd"])>0 for r in rows),
            "gross_pnl_usd":str(sum((Decimal(r["gross_pnl_usd"]) for r in rows),Decimal(0))),
            "cumulative_hold_minutes":{str(n):sum(r["order_final_fill_hold_minutes"]<=n for r in rows)
                                       for n in (2,5,10,30)}
        }
    return {"scope":"ONE_AUTHENTICATED_PAPER_ACCOUNT_IDENTIFICATION_NOT_EXPORTED",
            "snapshot_asof_utc":snapshot.get("asof_utc"),
            "coverage_from_utc":snapshot.get("recent_orders_since_utc"),
            "actual_filled_orders":len(filled),"nonfilled_orders":nonfilled,
            "closed_order_level_lots":len(closed),"unmatched":unmatched,
            "distinct_trading_days":len({r["day"] for r in closed}),
            "gross_pnl_usd":str(sum((Decimal(r["gross_pnl_usd"]) for r in closed),Decimal(0))),
            "cohorts":cohorts,
            "exit_reasons_verified":0,
            "net_after_fees_established":False,
            "no_fill_activity_timing_or_spread_proof":True,
            "no_orders_submitted":True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("snapshot",type=Path)
    args=p.parse_args()
    report=audit(json.loads(args.snapshot.read_text()))
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
