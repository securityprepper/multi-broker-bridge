"""Offline MBB PAPER scan evidence counter; never connects to brokers or edits state."""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import json
import sys
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
CUTOFF = dt.time(13, 15)

def classify(reason: str) -> str:
    if reason == "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE":
        return "NEWS_UNKNOWN"
    if reason == "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY":
        return "PRIOR_TRACKED"
    if reason.startswith("ENTRY_EXTENSION_BLOCKED_"):
        return "EXTENSION"
    return "OTHER"

def evaluate(records, day: str) -> dict:
    target = dt.date.fromisoformat(day)
    seen_cursors = set()
    counts = collections.Counter()
    symbols = collections.defaultdict(set)
    modes = collections.Counter()
    first = {}
    last = {}
    scans = 0
    watches = 0
    intents = 0
    incomplete = 0
    gate_true = 0
    for record in records:
        cursor = record.get("__CURSOR")
        if cursor and cursor in seen_cursors:
            continue
        if cursor:
            seen_cursors.add(cursor)
        try:
            local = dt.datetime.fromtimestamp(
                int(record["__REALTIME_TIMESTAMP"]) / 1_000_000, dt.timezone.utc
            ).astimezone(CT)
            if local.date() != target or local.time() >= CUTOFF:
                continue
            message = record["MESSAGE"]
            payload = json.loads(message) if isinstance(message, str) and message.lstrip().startswith("{") else None
            if not isinstance(payload, dict) or payload.get("status") != "SCAN_COMPLETE":
                continue
            if payload.get("mode") != "PAPER_EXECUTION":
                continue
        except (KeyError, ValueError, TypeError, OverflowError):
            incomplete += 1
            continue
        scans += 1
        modes[str(payload.get("mode"))] += 1
        gate_true += payload.get("gate_allows_new_entries") is True
        orders = payload.get("orders")
        watched = payload.get("buy_watch_symbols")
        reasons = payload.get("skipped_buy_reasons")
        if not isinstance(orders, list) or not isinstance(watched, list) or not isinstance(reasons, list):
            incomplete += 1
            continue
        intents += len(orders)
        watches += len(watched)
        for item in reasons:
            if not isinstance(item, dict):
                incomplete += 1
                continue
            symbol = item.get("symbol")
            reason = item.get("reason")
            if not isinstance(symbol, str) or not isinstance(reason, str):
                incomplete += 1
                continue
            category = classify(reason)
            counts[category] += 1
            symbols[category].add(symbol)
            iso = local.isoformat()
            first[category] = min(first.get(category, iso), iso)
            last[category] = max(last.get(category, iso), iso)
    return {
        "day_ct": day,
        "scope": "ONE JOURNAL UNIT; SCAN DECISIONS NOT BROKER FILL READBACK",
        "scan_count": scans,
        "scans_gate_true": gate_true,
        "buy_watch_appearances": watches,
        "order_intents_recorded": intents,
        "skipped_appearances": dict(sorted(counts.items())),
        "unique_symbols_by_reason": {k: len(v) for k, v in sorted(symbols.items())},
        "first_skip_by_reason_ct": dict(sorted(first.items())),
        "last_skip_by_reason_ct": dict(sorted(last.items())),
        "incomplete_records": incomplete,
        "all_watch_appearances_accounted_for": sum(counts.values()) == watches and incomplete == 0,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True, help="America/Chicago YYYY-MM-DD")
    parser.add_argument("--input", default="-", help="journalctl -o json JSONL; '-' stdin")
    args = parser.parse_args()
    try:
        if args.input == "-":
            stream = sys.stdin
        else:
            stream = open(args.input, encoding="utf-8")
        with stream if args.input != "-" else __import__("contextlib").nullcontext(stream) as f:
            records = (json.loads(line) for line in f if line.strip())
            result = evaluate(records, args.day)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["all_watch_appearances_accounted_for"] else 2
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "AUDIT_INCOMPLETE", "reason_type": type(exc).__name__}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())