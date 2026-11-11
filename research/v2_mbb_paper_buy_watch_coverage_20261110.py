"""Research-only, read-only MBB buy-watch diagnostic audit.
Consumes journalctl -o json lines on stdin; emits only symbol/reason aggregates.
Does not contact broker, DB, or network; never emits raw journal messages.
Counts are scan mentions, NOT independent opportunities or missing fills.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import re
import sys
from zoneinfo import ZoneInfo

SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,7}$")
REASONS = frozenset({
    "NO_FRESH_BID_ASK", "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY",
    "BROKER_ORDER_ALREADY_OPEN", "EXISTING_BROKER_POSITION",
    "HOLIDAY_GATE_BLOCKED", "AFTER_ENTRY_CUTOFF", "PER_ORDER_NOTIONAL_CAP",
    "PAPER_CASH_INSUFFICIENT",
})


def _valid_symbol(x):
    return isinstance(x, str) and bool(SYMBOL.fullmatch(x))


def audit(lines):
    counters = collections.Counter()
    reasons = collections.Counter()
    per_symbol = collections.defaultdict(collections.Counter)
    minute_symbols = set()
    min_time = max_time = None
    for raw in lines:
        try:
            outer = json.loads(raw)
            obj = json.loads(outer.get("MESSAGE", ""))
        except (TypeError, ValueError, AttributeError):
            continue
        if not isinstance(obj, dict) or not isinstance(obj.get("buy_watch_symbols"), list):
            continue
        counters["diagnostic_scans"] += 1
        ts = outer.get("__REALTIME_TIMESTAMP")
        try:
            when = dt.datetime.fromtimestamp(
                int(ts) / 1_000_000, ZoneInfo("America/Chicago")
            )
        except (ValueError, TypeError, OverflowError, OSError):
            when = None
        if when:
            min_time = min(min_time, when) if min_time else when
            max_time = max(max_time, when) if max_time else when
        candidates = {
            x for x in obj["buy_watch_symbols"] if _valid_symbol(x)
        }
        counters["candidate_mentions"] += len(candidates)
        for s in candidates:
            per_symbol[s]["candidate_mentions"] += 1
            if when:
                minute_symbols.add((when.strftime("%Y-%m-%d %H:%M"), s))
        skip_symbols = set()
        for record in obj.get("skipped_buy_reasons", []):
            if not isinstance(record, dict):
                continue
            s, reason = record.get("symbol"), record.get("reason")
            if s not in candidates:
                continue
            if s in skip_symbols:
                counters["duplicate_skip_symbol_same_scan"] += 1
                continue
            skip_symbols.add(s)
            reason = reason if reason in REASONS else "OTHER_OR_UNKNOWN"
            reasons[reason] += 1
            per_symbol[s][reason] += 1
        counters["unexplained_candidate_mentions"] += len(candidates - skip_symbols)
        # Explicitly flag truncated diagnostics rather than implying a complete audit.
        if len(candidates) >= 48 or len(obj.get("skipped_buy_reasons", [])) >= 48:
            counters["potentially_truncated_scans"] += 1
    ordered = sorted(per_symbol.items(), key=lambda kv: (-kv[1]["candidate_mentions"], kv[0]))
    return {
        "scan_level_only_not_fills": True,
        "period_CT": [min_time.isoformat() if min_time else None,
                      max_time.isoformat() if max_time else None],
        "diagnostic_scans": counters["diagnostic_scans"],
        "candidate_mentions": counters["candidate_mentions"],
        "distinct_symbol_minutes": len(minute_symbols),
        "skipped_by_reason": dict(sorted(reasons.items())),
        "unexplained_candidate_mentions": counters["unexplained_candidate_mentions"],
        "potentially_truncated_scans": counters["potentially_truncated_scans"],
        "duplicate_skip_symbol_same_scan": counters["duplicate_skip_symbol_same_scan"],
        "top_symbols": [
            {"symbol": s, "candidate_mentions": x["candidate_mentions"],
             "no_fresh_bid_ask": x["NO_FRESH_BID_ASK"],
             "reentry_ineligible": x["PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"]}
            for s, x in ordered[:15]
        ],
    }


if __name__ == "__main__":
    print(json.dumps(audit(sys.stdin), sort_keys=True))