"""Read-only reconciliation of FDR scheduled exit decisions with ALPACA PAPER filled lots.

Input pairs must be independently broker-verified filled buy/sell pairs.
Journal rows are independent historical service output, NOT evidence of fills.
Outputs omit client/order/fill/account identifiers. Never submits broker requests.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

CHI=ZoneInfo("America/Chicago")
ET=ZoneInfo("America/New_York")

def as_time(value):
    if isinstance(value,datetime): dt=value
    else: dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("timezone required")
    return dt.astimezone(CHI)

def read_exit_journal(lines):
    records=[]
    for line in lines:
        try:
            outer=json.loads(line)
            msg=json.loads(outer.get("MESSAGE",""))
            at=as_time(outer["__REALTIME_TIMESTAMP"]) if "T" in str(outer.get("__REALTIME_TIMESTAMP","")) else None
            if at is None:
                from datetime import timezone
                at=datetime.fromtimestamp(int(outer["__REALTIME_TIMESTAMP"])/1000000,timezone.utc).astimezone(CHI)
            if msg.get("strategy")!="five_day_rebound" or msg.get("status")!="EXIT_MANAGEMENT": continue
            for action in msg.get("orders",[]):
                if not isinstance(action,str) or ":" not in action: continue
                kind,symbol=action.split(":",1)
                if kind in ("PREOPEN_EXIT_REQUEST","NO_FRESH_EXIT_QUOTE"):
                    records.append((at,kind,symbol))
        except (ValueError,TypeError,KeyError,OverflowError):
            continue
    return records

def reconcile(pairs, events):
    output=[]
    seen=set()
    for trade in pairs:
        if trade.get("source")!="FDR":continue
        for required in ("entry_order_id","exit_order_id","entry_at","exit_at","entry","exit","qty","symbol","day"):
            if not trade.get(required): raise ValueError("incomplete verified filled pair")
        pairid=(trade["entry_order_id"],trade["exit_order_id"])
        if pairid[0]==pairid[1] or pairid in seen:raise ValueError("duplicate broker order pair")
        seen.add(pairid)
        start,finish=as_time(trade["entry_at"]),as_time(trade["exit_at"])
        if finish<start:raise ValueError("exit precedes entry")
        if finish.date().isoformat()!=trade["day"]:raise ValueError("fill day mismatch")
        if trade.get("exit_type")!="limit":raise ValueError("unexpected FDR exit type")
        matching=sorted(
           [e for e in events if e[1]=="PREOPEN_EXIT_REQUEST" and e[2]==trade["symbol"]
            and e[0].date()==finish.date() and timedelta(0)<=finish-e[0]<=timedelta(seconds=20)],
           key=lambda x:x[0])
        request=matching[-1][0] if matching else None
        prior_no_quote=any(e[1]=="NO_FRESH_EXIT_QUOTE" and e[2]==trade["symbol"]
            and e[0].date()==finish.date() and e[0]<finish for e in events)
        exit_day_first=datetime.combine(finish.date(),datetime.min.time(),CHI).replace(hour=7,minute=30)
        clock_ok=(request is not None and request>=exit_day_first and request.hour==7)
        outcome={
          "session":trade["day"],"symbol":trade["symbol"],
          "entry_ct":start.strftime("%H:%M:%S"),
          "exit_filled_ct":finish.strftime("%H:%M:%S"),
          "duration_minutes":round((finish-start).total_seconds()/60,3),
          "gross_pnl_usd":str((Decimal(str(trade["exit"]))-Decimal(str(trade["entry"])))*Decimal(str(trade["qty"]))),
          "broker_fill_pair_confirmed":True,
          "journal_scheduled_request_ct":request.strftime("%H:%M:%S") if request else None,
          "request_to_filled_seconds":round((finish-request).total_seconds(),3) if request else None,
          "quote_stale_before_request":prior_no_quote,
          "origin": "FDR_SCHEDULED_PREOPEN_EXIT" if clock_ok else "UNKNOWN"
        }
        output.append(outcome)
    pnl=sum((Decimal(x["gross_pnl_usd"]) for x in output),Decimal(0))
    return {"scope":"previously authenticated one Alpaca PAPER account, broker-filled FDR lots only",
      "distinct_days":len(set(x["session"] for x in output)),
      "roundtrips":len(output),"filled_sells":len(output),
      "scheduled_exit_identified":sum(x["origin"]=="FDR_SCHEDULED_PREOPEN_EXIT" for x in output),
      "unknown_exit_origin":sum(x["origin"]=="UNKNOWN" for x in output),
      "prior_stale_quote_count":sum(x["quote_stale_before_request"] for x in output),
      "gross_filled_pnl_usd":str(pnl),"all_loss":bool(output) and all(Decimal(x["gross_pnl_usd"])<0 for x in output),
      "trades":sorted(output,key=lambda x:x["symbol"]),"broker_orders_submitted":0,
      "actual_issuer_news_clearance":"NOT_EVALUATED_HISTORICAL_TRADES_ONLY"}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--pairs",required=True)
    p.add_argument("--journal",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    with open(a.pairs) as f: pairs=json.load(f)["trades"]
    with open(a.journal) as f: events=read_exit_journal(f)
    with open(a.output,"w") as f: json.dump(reconcile(pairs,events),f,indent=2)
    print("offline reconciled FDR filled orders to original journal, no broker calls")