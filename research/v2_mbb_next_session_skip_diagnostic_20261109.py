"""Sanitized read-only MBB next-session BUY_WATCH diagnostic reducer.

Use with journalctl short-iso output on a completed eligible session. Does not
call broker, read credentials, query cash, or issue orders. Never asserts that
historical 2026-11-09 candidate_count implied an AMD BUY_WATCH.
"""
from __future__ import annotations
from datetime import datetime
import argparse,json,sys
from zoneinfo import ZoneInfo
CHICAGO=ZoneInfo("America/Chicago")
KNOWN_SKIP={
  "NO_FRESH_BID_ASK","BROKER_ORDER_ALREADY_OPEN","HOLIDAY_GATE_BLOCKED",
  "EXISTING_BROKER_POSITION","AFTER_ENTRY_CUTOFF",
  "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY",
  "PER_ORDER_NOTIONAL_CAP","PAPER_CASH_INSUFFICIENT"}
def parse_lines(lines,day,symbol="AMD"):
    result=[]
    for line in lines:
        idx=line.find("{")
        if idx<0:continue
        try:
            obj=json.loads(line[idx:])
        except (ValueError,TypeError):continue
        if not isinstance(obj,dict) or obj.get("status") not in (
                "SCAN_COMPLETE","PAPER_DAILY_EXIT_GUARD","FAIL_CLOSED"):continue
        stamp=line.split(" ",1)[0]
        try:
            dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if dt.tzinfo is None or dt.astimezone(CHICAGO).date().isoformat()!=day:
                continue
        except (ValueError,TypeError):continue
        if obj.get("status")!="SCAN_COMPLETE":
            result.append({"time_chicago":dt.astimezone(CHICAGO).isoformat(),
                           "stage":obj["status"],"signal_status":"NOT_ASSESSABLE"})
            continue
        has_watch="buy_watch_symbols" in obj
        has_skips="skipped_buy_reasons" in obj
        watches=obj.get("buy_watch_symbols",[])
        skips=obj.get("skipped_buy_reasons",[])
        orders=obj.get("orders",[])
        emitted=(isinstance(watches,list) and symbol in watches) if has_watch else None
        reasons=sorted(set(x.get("reason") for x in skips
                           if isinstance(x,dict) and x.get("symbol")==symbol
                           and isinstance(x.get("reason"),str))) if isinstance(skips,list) else []
        order_status=sorted(set(str(x.get("status",x.get("action","UNKNOWN")))
                                for x in orders if isinstance(x,dict)
                                and x.get("symbol")==symbol and
                                x.get("side")=="buy")) if isinstance(orders,list) else []
        if not has_watch or not has_skips:stage="DIAGNOSTICS_MISSING"
        elif order_status:stage="BUY_ORDER_REQUEST_RECORDED_BROKER_FILL_NOT_PROVEN"
        elif reasons:stage="BUY_WATCH_SKIPPED_WITH_RECORDED_REASON"
        elif emitted is False:stage="NO_BUY_WATCH_EMITTED_REASON_UPSTREAM_UNPROVEN"
        elif emitted is True:stage="BUY_WATCH_WITHOUT_SKIP_OR_ORDER_CHECK_RESERVATION_AND_BROKER"
        else:stage="UNKNOWN"
        result.append({
         "time_chicago":dt.astimezone(CHICAGO).isoformat(),
         "stage":stage,
         "engine_buy_watch_emitted":emitted,
         "skip_reason_codes":reasons,
         "all_skip_codes_known":all(r in KNOWN_SKIP for r in reasons),
         "buy_order_status_codes":order_status,
         "candidate_count_buy_plus_exit":obj.get("candidate_count"),
         "holiday_gate_allows_new_entries":obj.get("gate_allows_new_entries"),
         "feed":obj.get("data_feed"),
        })
    return {"session_day_chicago":day,"symbol":symbol,"scans":len(result),
            "records":result,
            "scope":"SANITIZED JOURNAL ONLY; broker quote, positions, open orders, buying power and final fills independently unverified"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--day",required=True)
    p.add_argument("--symbol",default="AMD")
    p.add_argument("--input",default="-")
    a=p.parse_args()
    if a.input=="-":x=parse_lines(sys.stdin,a.day,a.symbol)
    else:
        with open(a.input) as f:x=parse_lines(f,a.day,a.symbol)
    print(json.dumps(x,indent=2))
if __name__=="__main__":main()
