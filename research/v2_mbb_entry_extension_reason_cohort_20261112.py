"""Read-only, no-network study of MBB buy-watch extension rejection evidence.

Input: journalctl -o json or journalctl -o cat JSON lines on stdin.
No credentials, live broker access, order API, filesystem mutation or execution.
Counts scan-level symbol *appearances*, never prospective trades or profits.
"""
from __future__ import annotations
import json
import re
import statistics
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation

CAPS = tuple(Decimal(str(v)) for v in ("0.5", "1", "1.5", "2", "2.5", "3", "4", "5"))
EXT = re.compile(r"^ENTRY_EXTENSION_BLOCKED_\+([0-9]+(?:\.[0-9]+)?)%_CAP_2\.0%$")

def messages(lines):
    for line in lines:
        try:
            item = json.loads(line)
            if isinstance(item, dict) and "MESSAGE" in item:
                item = json.loads(item["MESSAGE"])
            if isinstance(item, dict):
                yield item
        except (ValueError, TypeError, KeyError):
            continue

def study(records):
    totals = Counter()
    seen_watch, seen_extension, seen_prior = set(), set(), set()
    values, other = [], Counter()
    for message in records:
        status = message.get("status")
        totals["json_status_" + str(status)] += 1
        if status != "SCAN_COMPLETE":
            continue
        totals["completed_scans"] += 1
        watch = message.get("buy_watch_symbols") or []
        if not isinstance(watch, list):
            totals["malformed_watch_scans"] += 1
            continue
        totals["buy_watch_appearances"] += len(watch)
        seen_watch.update(x for x in watch if isinstance(x, str))
        skips = message.get("skipped_buy_reasons") or []
        if not isinstance(skips, list):
            totals["malformed_skips"] += 1
            continue
        for skip in skips:
            if not isinstance(skip, dict):
                totals["malformed_skip_entries"] += 1
                continue
            symbol, reason = skip.get("symbol"), skip.get("reason")
            if reason == "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY":
                totals["prior_entry_appearances"] += 1
                if isinstance(symbol, str):
                    seen_prior.add(symbol)
                continue
            m = EXT.fullmatch(str(reason))
            if m:
                try:
                    pct = Decimal(m.group(1))
                    if not pct.is_finite() or pct <= Decimal("2"):
                        raise ValueError("bad extension")
                    values.append(pct)
                    if isinstance(symbol, str):
                        seen_extension.add(symbol)
                except (InvalidOperation, ValueError):
                    totals["bad_extension_reason"] += 1
                continue
            other[str(reason)] += 1
        orders = message.get("orders") or []
        if isinstance(orders, list):
            totals["order_reply_records_NOT_FILLS"] += len(orders)
    totals["extension_appearances"] = len(values)
    totals["watch_unique_symbols"] = len(seen_watch)
    totals["extension_unique_symbols"] = len(seen_extension)
    totals["prior_entry_unique_symbols"] = len(seen_prior)
    output = {
        "counts": dict(totals),
        "other_reasons": dict(other),
        "extension_range_pct": (
            {"min": str(min(values)), "median": str(statistics.median(values)),
             "max": str(max(values))} if values else None),
        "extension_rejection_only_cap_sensitivity": {
            str(cap): {"rejected_appearances_at_or_below_cap": sum(x <= cap for x in values),
                       "rejected_appearances_still_above_cap": sum(x > cap for x in values)}
            for cap in CAPS},
        "important_limits": [
            "Repeated scan appearances are NOT distinct potential orders or days.",
            "Only the >2% rejected subset has historical extension percentages in reason logs.",
            "Loosening an extension cap does not prove entry eligibility: the subsequent prior-entry, news, broker, session and risk gates must still pass.",
            "No original recommendation ask, news publication/first-seen time, live quote at original recommendation, or broker fill for rejected candidates is established.",
            "Two-decimal reason strings are rounded, so apparent ties near a proposed threshold are uncertain.",
            "No post-signal profit, after-fee performance, latency-to-fill, or LIVE/PAPER modification is inferred."
        ]
    }
    return output

if __name__ == "__main__":
    print(json.dumps(study(messages(sys.stdin)), indent=2, sort_keys=True))
