"""Rolling, point-in-time sector confirmation replay for V2 research.

Unlike first-alert-only filtering, continue checking each newly completed
five-minute bar and allow later sector confirmation. No broker calls or orders.
Outcome labels and 14:00 marks are read solely for scoring, never decisions.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from statistics import mean
import argparse
import json

from research.v2_asof_sector_confirmation import (
    PEERS, ETF, prior_regular_closes, asof_context, gate)
from research.v2_reversal_and_limit_stress import (
    all_days, candidate, executable_proxy, WINDOW_START, WINDOW_LAST_START)
from research.v2_stock_risk_dayphase import ET, T5, T15, ingest

FAMILIES = ("up_close","up_reversal","down_close","down_reversal")
VARIANTS = ("baseline","etf","breadth","both","both_momentum")
LATER_START = date(2026, 9, 1)


def first_confirmed(*, bars: dict, previous_close: float, day: date,
                    family: str, variant: str, context_at):
    """Incremental event: only completed bars and as-of sector observations."""
    side, reference = family.split("_")
    high = low = None
    for start, row in sorted(bars.items()):
        if start.date() != day or not time(9, 30) <= start.time() <= WINDOW_LAST_START:
            continue
        high = row[1] if high is None else max(high, row[1])
        low = row[2] if low is None else min(low, row[2])
        if start.time() < WINDOW_START:
            continue
        older = bars.get(start - T15)
        if older is None:
            continue
        current, old_close = row[3], older[3]
        anchor = previous_close if reference == "close" else (
            high if side == "down" else low)
        if not candidate(side, previous_close, anchor, old_close, current):
            continue
        observed = start + T5
        if not gate(context_at(observed), side, variant):
            continue
        following = bars.get(observed)
        return {
            "asof": observed.isoformat(), "price": current,
            "base_change_pct": round(100*(current / previous_close - 1), 4),
            "anchor_change_pct": round(100*(current / anchor - 1), 4),
            "recent15_pct": round(100*(current / old_close - 1), 4),
            "next_bar_open": following[0] if following else None,
        }
    return None


def analyze_streaming(symbols: dict, daily: dict):
    rows, calendar = all_days(symbols, daily)
    closes = prior_regular_closes(symbols)
    calendar_dates = [date.fromisoformat(s) for s in calendar]
    prior_day = dict(zip(calendar_dates[1:],calendar_dates[:-1]))
    buckets = {sym: defaultdict(dict) for sym in symbols}
    for sym, bars in symbols.items():
        for at, row in bars.items():
            buckets[sym][at.date()][at] = row

    @lru_cache(maxsize=100000)
    def context(sym: str, day: date, at: datetime):
        return asof_context(symbols, closes, sym, day, prior_day[day], at)

    entries = []
    verified_baseline = 0
    for record in rows:
        sym = record["sym"]
        day = date.fromisoformat(record["day"])
        local = buckets[sym][day]
        for family in FAMILIES:
            original = record["signals"].get(family)
            if original is None:
                continue
            side = family.split("_")[0]
            for variant in VARIANTS:
                event = first_confirmed(
                    bars=local, previous_close=record["previous_close"], day=day,
                    family=family, variant=variant,
                    context_at=lambda at: context(sym,day,at))
                if variant == "baseline":
                    if event is None or event["asof"] != original["asof"]:
                        raise AssertionError("baseline first event diverges from existing audit")
                    verified_baseline += 1
                if event is None:
                    continue
                outcome = executable_proxy(event, record["mark14"], side, 30)
                entries.append({
                    "family": family, "variant": variant, "symbol": sym,
                    "day": record["day"], "later": day >= LATER_START,
                    "event": event, "major": record["big_up"] if side=="up" else record["big_down"],
                    "outcome": outcome,
                    "original_asof": original["asof"],
                })

    out = {}
    for family in FAMILIES:
        side = family.split("_")[0]
        out[family] = {}
        for period in ("earlier","later","all"):
            subset = [r for r in rows if period == "all" or r["later"] == (period == "later")]
            major_total = sum(r["big_up" if side=="up" else "big_down"] for r in subset)
            out[family][period] = {}
            for variant in VARIANTS:
                chosen = [v for v in entries if v["family"] == family and
                          v["variant"] == variant and
                          (period == "all" or v["later"] == (period=="later"))]
                hits = sum(v["major"] for v in chosen)
                proxies = [v["outcome"] for v in chosen if v["outcome"] is not None]
                lag = [
                    (datetime.fromisoformat(v["event"]["asof"]) -
                     datetime.fromisoformat(v["original_asof"])).total_seconds()/60
                    for v in chosen
                ]
                out[family][period][variant] = {
                    "signals": len(chosen),
                    "major_hits": hits,
                    "major_total": major_total,
                    "major_missed": major_total-hits,
                    "nonmajor_signals": len(chosen)-hits,
                    "early_before_5pct": sum(v["major"] and (
                        v["event"]["base_change_pct"] < 5 if side=="up"
                        else v["event"]["base_change_pct"] > -5) for v in chosen),
                    "mean_confirmation_lag_minutes": round(mean(lag),2) if lag else None,
                    "late_confirmations": sum(x>0 for x in lag),
                    "price_proxy_eligible": sum(x["price_eligible"] for x in proxies),
                    "price_proxy_count": len(proxies),
                    "avg_bounded_to14_pp": round(mean(
                        x["bounded_advantage_pp"] for x in proxies),4) if proxies else None,
                }
    return {
        "provenance": "split-adjusted SIP 5-minute OHLC; not BOATS/NBBO quotes or fills",
        "first": min(r["day"] for r in rows), "last": max(r["day"] for r in rows),
        "stock_days": len(rows), "major_up": sum(r["big_up"] for r in rows),
        "major_down": sum(r["big_down"] for r in rows),
        "baseline_equivalence_events_verified": verified_baseline,
        "event_families": out,
        "example_late_confirmation": [
            {k: v[k] for k in ("family","symbol","day","original_asof")} |
            {"variant": v["variant"], "confirmed_asof": v["event"]["asof"]}
            for v in entries if v["variant"]=="both" and
                v["event"]["asof"] > v["original_asof"]
        ][:12],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers", default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily", default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output")
    args = p.parse_args()
    result = analyze_streaming(
        ingest([args.primary,args.peers]),
        json.loads(Path(args.daily).read_text())["split"])
    if args.output:
        Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
