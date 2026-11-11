"""Read-only, redacted V1 MBB journal scan-reason audit.

Accepts journalctl -o json records from STDIN and outputs ONLY daily aggregate
reason counts; never displays broker account, cash, positions, raw quotes or
client IDs. This is a reporting audit, not order execution or an entry signal.
"""
from __future__ import annotations

import collections
import datetime
import json
import sys
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
KNOWN = frozenset({
    "NO_FRESH_BID_ASK",
    "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY",
    "BROKER_ORDER_ALREADY_OPEN",
    "POSITION_ALREADY_HELD",
    "ORDER_PENDING",
    "INSUFFICIENT_OWN_BUYING_POWER",
})
def parse_journal(line):
    """Return only date, count and normalized rejection categories."""
    try:
        wrapper = json.loads(line)
        if not isinstance(wrapper, dict):
            return None
        micros = int(wrapper["__REALTIME_TIMESTAMP"])
        if micros <= 0:
            return None
        payload = wrapper["MESSAGE"]
        if not isinstance(payload, str) or "{" not in payload:
            return None
        report = json.loads(payload[payload.index("{"):])
        if not isinstance(report, dict) or report.get("status") != "SCAN_COMPLETE":
            return None
        dt = datetime.datetime.fromtimestamp(micros / 1_000_000, datetime.timezone.utc).astimezone(CT)
        skipped = report.get("skipped_buy_reasons", [])
        watched = report.get("buy_watch_symbols", [])
        orders = report.get("orders", [])
        if not isinstance(skipped, list) or not isinstance(watched, list) or not isinstance(orders, list):
            return None
        reasons = []
        for item in skipped:
            if not isinstance(item, dict):
                reasons.append("OTHER_UNRECOGNIZED")
                continue
            reason = item.get("reason", "")
            reasons.append(reason if isinstance(reason, str) and reason in KNOWN else "OTHER_UNRECOGNIZED")
        candidates = report.get("candidate_count", 0)
        if not isinstance(candidates, int) or candidates < 0:
            return None
        return dt.date().isoformat(), {
            "scans": 1,
            "decision_candidates": candidates,
            "buy_watch_symbol_appearances": len(watched),
            "skip_reason_appearances": len(skipped),
            "reported_order_objects_not_fills": len(orders),
            "reasons": reasons
        }
    except (ValueError, TypeError, KeyError, OverflowError, json.JSONDecodeError):
        return None

def aggregate(lines):
    days = collections.defaultdict(collections.Counter)
    for line in lines:
        parsed = parse_journal(line)
        if parsed is None:
            continue
        day, row = parsed
        count = days[day]
        for field in ("scans", "decision_candidates", "buy_watch_symbol_appearances",
                      "skip_reason_appearances", "reported_order_objects_not_fills"):
            count[field] += row[field]
        for reason in row["reasons"]:
            count["skip_reason_" + reason] += 1
        if row["reasons"]:
            count["scans_with_skips"] += 1
        if "NO_FRESH_BID_ASK" in row["reasons"]:
            count["scans_with_quote_skip"] += 1
    return {day: dict(sorted(c.items())) for day, c in sorted(days.items())}

if __name__ == "__main__":
    print(json.dumps({
        "kind": "read_only_journal_decision_diagnostics",
        "counts_are_symbol_appearances_not_independent_trades": True,
        "orders_are_report_objects_not_broker_verified_fills": True,
        "source_is_host_journal_not_quote_response_archive": True,
        "days": aggregate(sys.stdin)
    }, sort_keys=True, indent=2))