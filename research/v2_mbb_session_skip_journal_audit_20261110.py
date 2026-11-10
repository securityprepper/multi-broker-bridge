"""Read-only, credential-free aggregation of MBB executor journal scan diagnostics.

Input: journald JSON lines, not broker orders or fills.
A repeated scan is NOT a separate attempted order or a distinct opportunity.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
import sys
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
ALLOWED = {"PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY",
           "NO_FRESH_BID_ASK"}

def summarize(lines, local_day):
    scans = 0
    candidate_scans = 0
    candidate_occurrences = Counter()
    reasons = Counter()
    reported_orders = 0
    examples = []
    tracked_counts = Counter()
    for line in lines:
        try:
            entry = json.loads(line)
            stamp = int(entry["__REALTIME_TIMESTAMP"]) / 1_000_000
            when = datetime.fromtimestamp(stamp, CHICAGO)
            msg = json.loads(entry["MESSAGE"])
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if when.date().isoformat() != local_day:
            continue
        if msg.get("status") != "SCAN_COMPLETE" or msg.get("mode") != "PAPER_EXECUTION":
            continue
        scans += 1
        if isinstance(msg.get("tracked"), int):
            tracked_counts[msg["tracked"]] += 1
        watch = msg.get("buy_watch_symbols")
        if not isinstance(watch, list):
            watch = []
        if watch:
            candidate_scans += 1
            for symbol in watch:
                if isinstance(symbol, str) and symbol.isalpha() and len(symbol) <= 6:
                    candidate_occurrences[symbol] += 1
        skip = []
        for s in msg.get("skipped_buy_reasons", []):
            if not isinstance(s, dict):
                continue
            symbol, reason = s.get("symbol"), s.get("reason")
            if isinstance(symbol, str) and symbol.isalpha() and len(symbol) <= 6 and isinstance(reason, str):
                reasons[(symbol, reason)] += 1
                skip.append({"symbol":symbol,"reason":reason})
        orders = msg.get("orders", [])
        if isinstance(orders, list):
            reported_orders += len(orders) # These are scan reports, NOT broker fills.
        if watch:
            examples.append({"chicago_time":when.isoformat(),
                             "watch": sorted(s for s in watch if isinstance(s,str)),
                             "skipped":skip,
                             "reported_order_count":len(orders) if isinstance(orders,list) else None})
    return {"local_day":local_day,"scan_records":scans,"scans_with_candidates":candidate_scans,
            "candidate_occurrences":dict(sorted(candidate_occurrences.items())),
            "candidate_symbol_count":len(candidate_occurrences),
            "skipped_reason_occurrences":[{"symbol":s,"reason":reason,"count":n}
               for (s,reason),n in sorted(reasons.items())],
            "reported_orders_not_verified_fills":reported_orders,
            "tracked_counts":dict(sorted(tracked_counts.items())),
            "candidate_scan_events":examples,
            "evidence_scope":"journald summary; no independent broker fill or execution verification"}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--day",required=True,help="America/Chicago YYYY-MM-DD")
    args=parser.parse_args()
    print(json.dumps(summarize(sys.stdin,args.day),indent=2,sort_keys=True))

if __name__=="__main__":
    main()