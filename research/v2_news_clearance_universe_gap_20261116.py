#!/usr/bin/env python3
"""Read-only V2 coverage-intersection audit. No broker, network, or trading access."""
import argparse
import collections
import json
import sys


def audit(scans, source_symbols, clear_symbols):
    seen = set()
    reason_counts = collections.Counter()
    watched = []
    candidate_scans = 0
    for scan in scans:
        if scan.get("status") != "SCAN_COMPLETE":
            continue
        items = scan.get("buy_watch_symbols", [])
        if not isinstance(items, list):
            raise ValueError("buy_watch_symbols must be list")
        if items:
            candidate_scans += 1
        seen.update(items)
        watched.extend(items)
        skipped = scan.get("skipped_buy_reasons", [])
        if not isinstance(skipped, list):
            raise ValueError("skipped_buy_reasons must be list")
        reason_counts.update(str(x.get("reason", "UNKNOWN")) for x in skipped if isinstance(x, dict))
    s, c = set(source_symbols), set(clear_symbols)
    if not c <= s:
        raise ValueError("published clearance not in trusted source universe")
    return {
        "candidate_scans": candidate_scans,
        "buy_watch_appearances": len(watched),
        "distinct_buy_watch_symbols": len(seen),
        "source_covered_distinct": len(seen & s),
        "source_uncovered_distinct": len(seen - s),
        "clear_intersection_distinct": len(seen & c),
        "source_intersection_symbols": sorted(seen & s),
        "clear_intersection_symbols": sorted(seen & c),
        "skipped_reason_counts": dict(reason_counts),
        "research_only": True,
        "broker_orders": 0,
        "caution": "BUY_WATCH is a pre-news signal, not a fully qualified executable recommendation",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scans-jsonl", required=True)
    p.add_argument("--source-symbols", required=True, help="comma-separated verified issuer coverage")
    p.add_argument("--clear-symbols", required=True, help="comma-separated fresh publisher-clear filenames")
    a = p.parse_args()
    scans = []
    with open(a.scans_jsonl, encoding="utf-8") as f:
        for line in f:
            try:
                scans.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    print(json.dumps(audit(scans, a.source_symbols.split(","), a.clear_symbols.split(",")), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

