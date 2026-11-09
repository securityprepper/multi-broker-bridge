"""Research-only sector/peer confirmation of causal five-minute reversal signals.

Uses only five-minute bars completed by each event's timestamp and prior
regular-session closes. Retrospective >=5% close labels are used for scoring,
never for a decision. Price proxy is not an executable bid/ask quote or fill.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, time, timedelta, date
import json
from math import ceil, isfinite
from pathlib import Path
from statistics import mean

from research.v2_stock_risk_dayphase import ET, T5, T15, ingest
from research.v2_reversal_and_limit_stress import all_days, executable_proxy

PEERS = ("AMD", "MU", "SNDK", "NVDA", "AVGO", "WDC", "TSM", "INTC")
ETF = "SOXX"
EVENTS = ("down_close", "down_reversal", "up_close", "up_reversal")
CUTOFF = date(2026, 8, 31)


def prior_regular_closes(bars: dict) -> dict:
    return {sym: {dt.date(): row[3] for dt, row in times.items()
                  if dt.time() == time(15, 55)}
            for sym, times in bars.items()}


def asof_context(bars: dict, closes: dict, symbol: str, day: date,
                 prior: date, asof: datetime):
    """Return complete strictly as-of sector context, or None on missing data.

    The event must have been observed at the END of a 5m bar. All price
    observations are from that completed bar or earlier, not future outcomes.
    """
    if symbol not in (*PEERS, ETF) or asof.tzinfo is None:
        return None
    local = asof.astimezone(ET)
    if local.date() != day or local.minute % 5 or local.second or local.microsecond:
        return None
    finished_start = local - T5
    if finished_start.date() != day or not (time(9, 30) <= finished_start.time() <= time(15, 55)):
        return None
    required = (*PEERS, ETF)
    current, prev = {}, {}
    for s in required:
        row = bars.get(s, {}).get(finished_start)
        c = closes.get(s, {}).get(prior)
        if row is None or c is None or not isfinite(row[3]) or not isfinite(c) or min(row[3], c) <= 0:
            return None
        current[s], prev[s] = row[3], c
    old_etf = bars[ETF].get(finished_start - T15)
    if old_etf is None or not isfinite(old_etf[3]) or old_etf[3] <= 0:
        return None
    etf_ret = current[ETF] / prev[ETF] - 1
    etf_recent = current[ETF] / old_etf[3] - 1
    peer_list = [s for s in PEERS if s != symbol]
    peer_returns = [current[s] / prev[s] - 1 for s in peer_list]
    return {
        "etf_pct": round(etf_ret * 100, 4),
        "etf_15m_pct": round(etf_recent * 100, 4),
        "peer_count": len(peer_returns),
        "peer_up": sum(v >= 0.0025 for v in peer_returns),
        "peer_down": sum(v <= -0.0025 for v in peer_returns),
    }


def gate(context: dict | None, side: str, variant: str) -> bool:
    if side not in ("up", "down"):
        raise ValueError("unknown direction")
    if variant not in ("baseline", "etf", "breadth", "both", "both_momentum"):
        raise ValueError("unknown gate")
    if variant == "baseline":
        return True
    if context is None:
        return False
    direction = 1 if side == "up" else -1
    etf_pct = context["etf_pct"] * direction
    recent = context["etf_15m_pct"] * direction
    breadth = context["peer_up" if side == "up" else "peer_down"]
    minimum = ceil(context["peer_count"] / 2)
    if variant == "etf":
        return etf_pct >= 0.25
    if variant == "breadth":
        return breadth >= minimum
    if variant == "both":
        return etf_pct >= 0.25 and breadth >= minimum
    if variant == "both_momentum":
        return etf_pct >= 0.25 and breadth >= minimum and recent >= 0.20
    raise ValueError("unknown gate")


def analyze(bars: dict, daily: dict) -> dict:
    rows, calendar = all_days(bars, daily)
    closes = prior_regular_closes(bars)
    prior_day = {date.fromisoformat(calendar[i]): date.fromisoformat(calendar[i-1])
                 for i in range(1, len(calendar))}
    contexts = {}
    for row in rows:
        day, sym = date.fromisoformat(row["day"]), row["sym"]
        for name in EVENTS:
            event = row["signals"].get(name)
            if event:
                asof = datetime.fromisoformat(event["asof"])
                contexts[(sym, day, name)] = asof_context(
                    bars, closes, sym, day, prior_day[day], asof)
    summaries = {}
    for name in EVENTS:
        side = name.split("_")[0]
        major = "big_up" if side == "up" else "big_down"
        summaries[name] = {}
        for period in ("earlier", "later", "all"):
            subset = [r for r in rows if (
                period == "all" or
                (period == "earlier" and date.fromisoformat(r["day"]) <= CUTOFF) or
                (period == "later" and date.fromisoformat(r["day"]) > CUTOFF)
            )]
            maj_total = sum(r[major] for r in subset)
            baseline = [r for r in subset if name in r["signals"]]
            missing = sum(contexts[(r["sym"], date.fromisoformat(r["day"]), name)] is None for r in baseline)
            variants = {}
            for variant in ("baseline", "etf", "breadth", "both", "both_momentum"):
                selected = []
                for r in baseline:
                    ctx = contexts[(r["sym"], date.fromisoformat(r["day"]), name)]
                    if gate(ctx, side, variant):
                        selected.append(r)
                hits = sum(r[major] for r in selected)
                tested = [executable_proxy(r["signals"][name], r["mark14"], side, 30)
                          for r in selected]
                tested = [x for x in tested if x is not None]
                vals = [x["bounded_advantage_pp"] for x in tested]
                early = sum(
                    r[major] and (
                        r["signals"][name]["base_change_pct"] < 5 if side == "up"
                        else r["signals"][name]["base_change_pct"] > -5
                    ) for r in selected)
                variants[variant] = {
                    "signals": len(selected), "major_hits": hits,
                    "major_missed": maj_total - hits, "nonmajor_signals": len(selected)-hits,
                    "major_early_pre5pct": early,
                    "major_recall_pct": round(hits / maj_total * 100, 3) if maj_total else None,
                    "major_precision_pct": round(hits / len(selected)*100, 3) if selected else None,
                    "price_proxy_count": len(vals),
                    "avg_bounded_to14_pp": round(mean(vals), 4) if vals else None,
                    "price_eligible_count": sum(x["price_eligible"] for x in tested),
                    "favorable_bounded_count": sum(x > 0 for x in vals),
                    "adverse_bounded_count": sum(x < 0 for x in vals),
                }
            summaries[name][period] = {
                "stock_days": len(subset), "major_days": maj_total,
                "missing_peer_context_among_baseline_alerts": missing,
                "strategies": variants,
            }
    missed = []
    for side in ("up", "down"):
        major = "big_up" if side == "up" else "big_down"
        for r in rows:
            if not r[major]:
                continue
            accepted = any(name in r["signals"] and gate(
                contexts[(r["sym"], date.fromisoformat(r["day"]), name)],
                side, "both") for name in (f"{side}_close", f"{side}_reversal"))
            if not accepted:
                missed.append({"symbol": r["sym"], "day": r["day"],
                               "close_change_pct": r["change_pct"], "side": side,
                               "original_signal": any(f"{side}_{k}" in r["signals"]
                                                      for k in ("close", "reversal"))})
    return {
        "provenance": "52-week split-adjusted five-minute SIP OHLC; not NBBO, not BOATS quotes",
        "stocks": sorted(bars), "stock_days": len(rows),
        "first": min(r["day"] for r in rows), "last": max(r["day"] for r in rows),
        "total_big_up": sum(r["big_up"] for r in rows),
        "total_big_down": sum(r["big_down"] for r in rows),
        "split_cutoff": CUTOFF.isoformat(),
        "signal_confirmation": summaries,
        "examples_major_missed_by_both": {
            "up": [r for r in missed if r["side"] == "up"][:12],
            "down": [r for r in missed if r["side"] == "down"][:12],
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers", default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily", default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output", default=None)
    args = p.parse_args()
    bars = ingest([args.primary, args.peers])
    daily = json.loads(Path(args.daily).read_text())["split"]
    result = analyze(bars, daily)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
