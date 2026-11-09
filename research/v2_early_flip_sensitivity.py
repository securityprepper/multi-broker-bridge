"""V2 research-only first-hour sector turn sensitivity and buy-veto stress.

No broker calls or timers. A proposed action only uses 09:15 ET preopen
completed bars plus completed regular-session five-minute bars at as-of.
Future closing and next-open marks are scoring outcomes, never signals.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from math import ceil, isfinite
from pathlib import Path
from statistics import mean, median

from research.v2_stock_risk_dayphase import ET, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_next_open_stop_stress import price_scenario

ETF = "SOXX"
PEERS = ("AMD", "MU", "SNDK", "NVDA", "AVGO", "WDC", "TSM", "INTC")
ANCHOR_START = time(9, 10)  # completed at 09:15 ET
FIRST_CHECKPOINT = time(9, 35)
LAST_CHECKPOINT = time(10, 30)
T5 = timedelta(minutes=5)
LATER = date(2026, 9, 1)
# Tentative sensitivity variants: do not tune against the late-period results.
VARIANTS = {"early_050": (0.5, 0.5, 0.25),
            "base_100": (1.0, 1.0, 0.50),
            "late_150": (1.5, 1.5, 0.75)}
FRICTION = 0.0015
LIMIT = 0.003


def point_in_time_returns(bars, closes, prior, today, start):
    """All nine must share the same *completed* bar and last regular close."""
    out = {}
    for sym in (*PEERS, ETF):
        row = bars.get(sym, {}).get(datetime.combine(today, start, ET))
        base = closes.get(sym, {}).get(prior)
        if row is None or base is None or not all(
                isfinite(v) and v > 0 for v in (row[3], base)):
            return None
        out[sym] = 100 * (row[3] / base - 1)
    return out


def direction_from_anchor(pre):
    """Classify the preopening broad trend before any opening observations."""
    if pre is None:
        return 0
    for sign in (1, -1):
        if sign * pre[ETF] >= .5 and sum(
                sign * pre[sym] >= .5 for sym in PEERS) >= 4:
            return sign
    return 0


def qualifying_flip(pre, current, sym, thresholds):
    """Return side and peer count; no future labels, future bars or order IO."""
    if pre is None or current is None or sym not in (*PEERS, ETF):
        return None
    original = direction_from_anchor(pre)
    if not original:
        return None
    contra = -original
    etf_min, own_min, peer_min = thresholds
    peers = [p for p in PEERS if p != sym]
    breadth = sum(contra * (current[p] - pre[p]) >= peer_min
                  for p in peers)
    if (contra * (current[ETF] - pre[ETF]) < etf_min or
        contra * (current[sym] - pre[sym]) < own_min or
            breadth < ceil(len(peers) / 2)):
        return None
    return ("down" if contra < 0 else "up", breadth)


def first_flip(bars, closes, sym, prior, today, thresholds,
               cutoff=LAST_CHECKPOINT):
    """Observations for 09:35 use ONLY the 09:30–09:35 completed candle."""
    if sym not in (*PEERS, ETF):
        raise ValueError("unknown symbol")
    if any(not (0 < x <= 10) for x in thresholds):
        raise ValueError("unsupported threshold")
    pre = point_in_time_returns(bars, closes, prior, today, ANCHOR_START)
    if direction_from_anchor(pre) == 0:
        return None
    for minutes in range(9 * 60 + 35, 10 * 60 + 31, 5):
        asof = datetime.combine(today, time(minutes // 60, minutes % 60), ET)
        if asof.time() > cutoff:
            break
        latest = point_in_time_returns(bars, closes, prior, today,
                                       (asof - T5).time())
        matched = qualifying_flip(pre, latest, sym, thresholds)
        if matched is None:
            continue
        row = bars[sym][asof - T5]
        nextbar = bars[sym].get(asof)
        return {"at": asof.isoformat(), "side": matched[0],
                "peer_breadth": matched[1], "price": row[3],
                "total_from_prior_pct": round(latest[sym], 4),
                "from_anchor_pp": round(latest[sym] - pre[sym], 4),
                "next_bar_open": nextbar[0] if nextbar else None}
    return None


def price_mark14(event, future_14, previous_close):
    """Next-bar limit eligibility is a scenario, not a demonstrated fill."""
    nxt = event["next_bar_open"]
    if nxt is None or future_14 is None or min(nxt, future_14, previous_close) <= 0:
        return None
    if event["side"] == "down":
        eligible = nxt * (1 - FRICTION) >= event["price"] * (1 - LIMIT)
        advantage = (100 * (nxt - future_14) * (1 - FRICTION) /
                     previous_close) if eligible else 0.
    else:
        eligible = nxt * (1 + FRICTION) <= event["price"] * (1 + LIMIT)
        advantage = (100 * (future_14 * (1 - FRICTION) /
                           (nxt * (1 + FRICTION)) - 1)) if eligible else 0.
    return {"price_eligible": eligible,
            "bounded_advantage_14_pp": round(advantage, 4)}


def prior5_return(closes, days, i, sym=ETF):
    """Only the FIVE complete daily close-to-close steps BEFORE target i."""
    if i < 6:
        return None
    old, last = days[i - 6], days[i - 1]
    if old not in closes[sym] or last not in closes[sym]:
        return None
    return 100 * (closes[sym][last] / closes[sym][old] - 1)


def stats(rows, side, variant, period):
    selected = [r for r in rows if r["side"] == side and
                r["variant"] == variant and
                (period == "all" or r["later"] == (period == "later"))]
    events = [r for r in selected if r["event"]]
    hit = [r for r in events if r["major"]]
    score = [r["score14"]["bounded_advantage_14_pp"] for r in events
             if r["score14"] is not None]
    nextscore = [r["score_next"]["bounded_advantage_nextopen_pp"] for r in events
                 if r["score_next"] is not None]
    valid = [r for r in events if r["score14"] is not None]
    days = defaultdict(list)
    for r in valid:
        days[r["day"]].append(r["score14"]["bounded_advantage_14_pp"])
    before5 = sum(abs(r["event"]["total_from_prior_pct"]) < 5 for r in hit)
    early = [r for r in hit if r["event"]["at"][11:16] <= "09:45"]
    eligible = sum(r["score14"]["price_eligible"] for r in valid)
    earliest = min((r["event"]["at"] for r in hit), default=None)
    misses = [r for r in selected if r["major"] and not r["event"]]
    worst = sorted(misses, key=lambda r: abs(r["close_pct"]), reverse=True)[:5]
    return {"stock_days": len(selected),
            "major_days": sum(r["major"] for r in selected),
            "alerts": len(events),
            "major_hits": len(hit),
            "nonmajor_alerts": len(events) - len(hit),
            "major_missed": len(misses),
            "hits_before_5pct": before5, "hits_by_0945": len(early),
            "earliest_major_alert": earliest,
            "scored_nextbar": len(valid), "nextbar_price_eligible": eligible,
            "mean_to14_pp": round(mean(score), 4) if score else None,
            "median_to14_pp": round(median(score), 4) if score else None,
            "day_equal_mean_to14_pp": round(mean(map(mean, days.values())), 4)
                if days else None,
            "mean_to_next_regular_open_pp": round(mean(nextscore), 4)
                if nextscore else None,
            "positive_vs_14": sum(x > 0 for x in score),
            "negative_vs_14": sum(x < 0 for x in score),
            "missed_worst": [{"day": r["day"], "symbol": r["symbol"],
                              "close_pct": r["close_pct"]} for r in worst]}


def analyze(bars, daily):
    universe, daystrings = all_days(bars, daily)
    dates = [date.fromisoformat(s) for s in daystrings]
    idx = {v: k for k, v in enumerate(dates)}
    closes = prior_regular_closes(bars)
    prior = {dates[i]: dates[i - 1] for i in range(1, len(dates))}
    after = {dates[i]: dates[i + 1] for i in range(len(dates) - 1)}
    @lru_cache(maxsize=50000)
    def find(sym, d, variant):
        return first_flip(bars, closes, sym, prior[d], d, VARIANTS[variant])
    @lru_cache(maxsize=500)
    def pre_dir(d):
        return direction_from_anchor(
            point_in_time_returns(bars, closes, prior[d], d, ANCHOR_START))
    out = []
    for row in universe:
        sym, day = row["sym"], date.fromisoformat(row["day"])
        nd = after.get(day)
        next_row = bars[sym].get(datetime.combine(nd, time(9, 30), ET)) if nd else None
        next_regular_open = next_row[0] if next_row else None
        for variant in VARIANTS:
            event = find(sym, day, variant)
            for side in ("up", "down"):
                chosen = event if event and event["side"] == side else None
                score14 = (price_mark14(chosen, row["mark14"],
                                       row["previous_close"]) if chosen else None)
                score_next = (price_scenario(chosen, next_regular_open,
                              row["previous_close"], side) if chosen else None)
                out.append({"symbol": sym, "day": row["day"], "side": side,
                            "variant": variant, "later": day >= LATER,
                            "preopen_direction": pre_dir(day),
                            "prior5_soxx_pct": prior5_return(closes, dates, idx[day]),
                            "close_pct": row["change_pct"],
                            "major": row["big_up"] if side == "up" else row["big_down"],
                            "event": chosen, "score14": score14,
                            "score_next": score_next})
    res = {"universe_stock_days": len(universe), "major_up": sum(r["big_up"] for r in universe),
           "major_down": sum(r["big_down"] for r in universe),
           "period": f"{dates[0].isoformat()} through {dates[-1].isoformat()}",
           "thresholds_soxx_stock_peer_pp": VARIANTS,
           "segments": {}, "early_buy_veto": {}, "nov2": [], "prior5": {}}
    for segment in ("all", "earlier", "later"):
        res["segments"][segment] = {
            variant: {side: stats(out, side, variant, segment)
                      for side in ("down", "up")} for variant in VARIANTS}
    for variant in VARIANTS:
        # Prevent buying on a preopen-up day only IF an opposite flip
        # is actually observable by 09:45; no "lookahead buy prevention".
        bullish = [r for r in out if r["variant"] == variant and
                   r["side"] == "down" and r["preopen_direction"] == 1]
        veto = [r for r in bullish if r["event"] and
                r["event"]["at"][11:16] <= "09:45"]
        res["early_buy_veto"][variant] = {
            "preopen_bullish_stockdays": len(bullish),
            "early_flip_vetoes": len(veto),
            "major_declines_vetoed": sum(r["major"] for r in veto),
            "other_days_vetoed": sum(not r["major"] for r in veto),
            "preopen_bullish_major_declines": sum(r["major"] for r in bullish),
            "major_up_days_vetoed": sum(r["close_pct"] >= 5 for r in veto),
            "major_up_days_in_bullish_cohort": sum(r["close_pct"] >= 5 for r in bullish),
            "earliest_veto": min((r["event"]["at"] for r in veto), default=None)}
        for side in ("down", "up"):
            records = [r for r in out if r["variant"] == variant and
                       r["side"] == side and r["event"] and
                       r["prior5_soxx_pct"] is not None]
            res["prior5"][variant + "_" + side] = {
                "complete_histories": len(records),
                "weak_5day": sum(r["prior5_soxx_pct"] <= -5 for r in records),
                "weak_5day_early_mean_pp": round(mean(
                    r["score14"]["bounded_advantage_14_pp"] for r in records
                    if r["prior5_soxx_pct"] <= -5 and r["score14"] is not None), 4)
                    if any(r["prior5_soxx_pct"] <= -5 and r["score14"] is not None
                           for r in records) else None}
    res["nov2"] = [{"symbol": r["symbol"], "variant": r["variant"],
                    "at": r["event"]["at"], "close_pct": r["close_pct"]}
                   for r in out if r["day"] == "2026-11-02" and
                   r["side"] == "down" and r["event"] and r["major"]]
    res["execution_limit"] = ("5m SIP OHLC next-bar opening marks only; no NBBO, "
                               "BOATS, bid sizes, queue or actual fill evidence")
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers", default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily", default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output")
    args = p.parse_args()
    r = analyze(ingest([args.primary, args.peers]),
                json.loads(Path(args.daily).read_text())["split"])
    if args.output:
        Path(args.output).write_text(json.dumps(r, indent=2, sort_keys=True))
    print(json.dumps(r, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()