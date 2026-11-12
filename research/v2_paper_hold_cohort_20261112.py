"""Offline, account-scoped Alpaca PAPER round-trip holding-duration attribution.

Input is previously broker-verified completed ORDER/FILL pair data, never order
acceptances or raw fill activity counts. This script makes no network calls.
Private order UUIDs are used only to verify uniqueness and never output.
"""
from __future__ import annotations
import collections
import json
import statistics
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
BINS = ("<=2m", ">2-5m", ">5-10m", ">10-30m", ">30m")

def timestamp(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Timestamp must contain a timezone")
    return d.astimezone(CT)

def cohort(t: dict) -> dict:
    start, end = timestamp(t["entry_at"]), timestamp(t["exit_at"])
    minutes = (end - start).total_seconds() / 60
    if minutes < 0:
        raise ValueError("Exit before entry")
    entry, exit_ = Decimal(str(t["entry"])), Decimal(str(t["exit"]))
    qty = Decimal(str(t["qty"]))
    if not all(x.is_finite() and x > 0 for x in (entry, exit_, qty)):
        raise ValueError("Nonpositive/nonfinite price or quantity")
    if t["day"] != start.date().isoformat():
        raise ValueError("Trade day disagrees with Chicago entry")
    label = (
        BINS[0] if minutes <= 2 else BINS[1] if minutes <= 5
        else BINS[2] if minutes <= 10 else BINS[3] if minutes <= 30
        else BINS[4]
    )
    if start.hour >= 19 or start.hour < 3:
        session = "overnight"
    elif (start.hour, start.minute) < (8, 30):
        session = "premarket"
    else:
        session = "RTH_or_later"
    return {
        "source": t["source"], "day": t["day"], "symbol": t["symbol"],
        "hold_bucket": label, "minutes": minutes, "session": session,
        "pnl": (exit_ - entry) * qty,
        "pct": float((exit_ - entry) * 100 / entry),
    }

def stats(rows):
    total = sum((r["pnl"] for r in rows), Decimal(0))
    n = len(rows)
    return {
        "n": n, "winning": sum(r["pnl"] > 0 for r in rows),
        "losing": sum(r["pnl"] < 0 for r in rows),
        "flat": sum(r["pnl"] == 0 for r in rows),
        "broker_fill_gross_usd": str(total.quantize(Decimal("0.01"))),
        "median_fill_return_pct": round(statistics.median(r["pct"] for r in rows), 4) if n else None,
    }

def analyze(trades: list[dict]) -> dict:
    seen_entry, seen_exit = set(), set()
    rows = []
    for t in trades:
        buy, sell = t["entry_order_id"], t["exit_order_id"]
        if not buy or not sell or buy == sell or buy in seen_entry or sell in seen_exit:
            raise ValueError("Missing, crossed or duplicate order UUID")
        seen_entry.add(buy)
        seen_exit.add(sell)
        rows.append(cohort(t))
    by_duration = {b: stats([r for r in rows if r["hold_bucket"] == b]) for b in BINS}
    m = [r for r in rows if r["source"] == "MBB"]
    f = [r for r in rows if r["source"] == "FDR"]
    early = [r for r in m if r["minutes"] <= 10]
    late = [r for r in m if r["minutes"] > 10]
    return {
        "scope": "one previously authenticated Alpaca PAPER account, bounded completed broker-filled pairs",
        "all_completed": stats(rows), "by_duration": by_duration,
        "by_source": {"MBB": stats(m), "FDR": stats(f)},
        "mbb_under_or_equal_10m": stats(early),
        "mbb_over_10m": stats(late),
        "mbb_rapid_by_day": {day: stats([r for r in early if r["day"] == day]) for day in sorted({r["day"] for r in rows})},
        "mbb_rapid_by_session": {s: stats([r for r in early if r["session"] == s]) for s in ("overnight", "premarket", "RTH_or_later")},
        "hold_duration_is_outcome_associated_not_proven_exit_trigger": True,
        "exit_trigger_for_ordinary_mbb": "UNKNOWN",
        "commissions": "UNKNOWN",
        "qualified_parameter_change": False,
        "broker_orders_submitted": 0,
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python v2_paper_hold_cohort_20261112.py PRIVATE_BROKER_VERIFIED_JSON")
    d = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(analyze(d["trades"]), indent=2))

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]