"""Research-only causal five-minute late-reversal alerts and bounded-limit stress.

Never accesses broker credentials or places orders. Five-minute split-adjusted
SIP OHLC cannot verify streaming fills, NBBO spreads, depth or intrabar ordering.
A "limit-eligible" next bar is only a favorable price proxy, NOT a confirmed fill.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from statistics import mean, median

from research.v2_stock_risk_dayphase import ET, T5, T15, ingest

SPLIT_DATE = "2026-08-31"
WINDOW_START = time(9, 45)
WINDOW_LAST_START = time(12, 55)
TARGET_TIME = time(14, 0)
REG_CLOSE_START = time(15, 55)
THRESHOLD_TOTAL = 0.025
THRESHOLD_15 = 0.010
FRICTION = 0.0015


def candidate(side: str, base: float, anchor: float, old_close: float, now: float):
    """Both changes known at current completed-bar close, overlapping not additive."""
    if min(base, anchor, old_close, now) <= 0:
        return False
    if side == "down":
        return now / anchor <= (1 - THRESHOLD_TOTAL) and now / old_close <= (1 - THRESHOLD_15)
    if side == "up":
        return now / anchor >= (1 + THRESHOLD_TOTAL) and now / old_close >= (1 + THRESHOLD_15)
    raise ValueError(side)


def first_day_signals(bars: dict, day: date, previous_close: float,
                      last_start: time = WINDOW_LAST_START):
    """Return first observed four signals; running extrema update only after a bar completes."""
    rth = sorted((t, b) for t, b in bars.items() if t.date() == day
                 and time(9, 30) <= t.time() <= last_start)
    top = None
    bottom = None
    alerts = {}
    for start, row in rth:
        top = max(top, row[1]) if top is not None else row[1]
        bottom = min(bottom, row[2]) if bottom is not None else row[2]
        if start.time() < WINDOW_START:
            continue
        earlier = bars.get(start - T15)
        if earlier is None:
            continue
        now, old = row[3], earlier[3]
        for side in ("down", "up"):
            anchor = previous_close
            other_anchor = top if side == "down" else bottom
            for kind, reference in (("close", anchor), ("reversal", other_anchor)):
                name = f"{side}_{kind}"
                if name in alerts or not candidate(side, anchor, reference, old, now):
                    continue
                action_time = start + T5
                following = bars.get(action_time)
                alerts[name] = dict(
                    asof=action_time.isoformat(), price=now,
                    base_change_pct=round((now / anchor - 1) * 100, 4),
                    anchor_change_pct=round((now / reference - 1) * 100, 4),
                    recent15_pct=round((now / old - 1) * 100, 4),
                    next_bar_open=following[0] if following else None,
                )
    return alerts


def all_days(symbols: dict, daily: dict):
    cal = sorted(set.intersection(*(set(row[0][:10] for row in daily[s])
                                   for s in ("AMD", "MU", "SNDK", "SOXX"))))
    calendar = [date.fromisoformat(day) for day in cal]
    results = []
    for sym, bars in sorted(symbols.items()):
        by_date = defaultdict(dict)
        closes = {}
        for dt, row in bars.items():
            by_date[dt.date()][dt] = row
            if dt.time() == REG_CLOSE_START:
                closes[dt.date()] = row[3]
        for i in range(1, len(calendar)):
            d, prior = calendar[i], calendar[i-1]
            if d not in closes or prior not in closes:
                continue
            prev_close = closes[prior]
            today = by_date.get(d, {})
            day_mark = today.get(datetime.combine(d, TARGET_TIME, ET))
            changes = closes[d] / prev_close - 1
            events = first_day_signals(today, d, prev_close)
            late_events = first_day_signals(today, d, prev_close, time(15, 45))
            results.append(dict(
                sym=sym, day=d.isoformat(), later=d.isoformat() > SPLIT_DATE,
                big_down=changes <= -0.05, big_up=changes >= 0.05,
                change_pct=round(changes * 100, 4), previous_close=prev_close,
                mark14=day_mark[0] if day_mark else None, signals=events,
                full_day_signals=late_events))
    return results, cal


def executable_proxy(event: dict, mark14: float | None, side: str, bps: int = 30):
    """Observed next-bar OPEN is just a scenario price; neither a quote nor a fill.

    A bounded limit cannot be assumed filled when next-bar unfavorable-price
    assumption is worse than the limit. If unfilled, keep holding (down side)
    or skip entry (up side). Do not use the future bar HIGH to assign a fill.
    """
    nxt = event.get("next_bar_open")
    if nxt is None or mark14 is None:
        return None
    signal_close = event["price"]
    if side == "down":
        bound = signal_close * (1 - bps / 10000)
        modeled_sell = nxt * (1 - FRICTION)
        eligible = modeled_sell >= bound
        gain_pp = 100 * (modeled_sell - mark14 * (1 - FRICTION)) / signal_close
        return dict(price_eligible=eligible,
                    proxy_unbounded_advantage_pp=gain_pp,
                    bounded_advantage_pp=gain_pp if eligible else 0.0,
                    next_open_beyond_limit=nxt < bound)
    if side == "up":
        ceiling = signal_close * (1 + bps / 10000)
        modeled_buy = nxt * (1 + FRICTION)
        eligible = modeled_buy <= ceiling
        gain_pp = 100 * (mark14 * (1 - FRICTION) / modeled_buy - 1)
        return dict(price_eligible=eligible,
                    proxy_unbounded_advantage_pp=gain_pp,
                    bounded_advantage_pp=gain_pp if eligible else 0.0,
                    next_open_beyond_limit=nxt > ceiling)
    raise ValueError(side)


def stats(rows: list[dict], name: str, *, side: str, subset: str = "all"):
    sample = [r for r in rows if subset == "all" or
              (subset == "earlier" and not r["later"]) or
              (subset == "later" and r["later"])]
    major_key = "big_down" if side == "down" else "big_up"
    positives = sum(r[major_key] for r in sample)
    alarms = [r for r in sample if name in r["signals"]]
    hits = [r for r in alarms if r[major_key]]
    trades = [(r, executable_proxy(r["signals"][name], r["mark14"], side))
              for r in alarms]
    trades = [(r, result) for r, result in trades if result is not None]
    def summary_values(key):
        values = [x[key] for _, x in trades]
        return round(mean(values), 4) if values else None
    return dict(days=len(sample), major_days=positives, alerts=len(alarms),
                hits=len(hits), missed=positives-len(hits), false_alarms=len(alarms)-len(hits),
                recall_pct=round(100 * len(hits) / positives, 2) if positives else None,
                valid_price_proxies=len(trades),
                bounded_limit_price_eligible=sum(x["price_eligible"] for _, x in trades),
                next_open_beyond_limit=sum(x["next_open_beyond_limit"] for _, x in trades),
                avg_unbounded_advantage_pp=summary_values("proxy_unbounded_advantage_pp"),
                avg_bounded_advantage_pp=summary_values("bounded_advantage_pp"),
                favorable_bounded_count=sum(x["bounded_advantage_pp"] > 0 for _, x in trades),
                adverse_bounded_count=sum(x["bounded_advantage_pp"] < 0 for _, x in trades))


def supplemental(rows, side: str, early="close", added="reversal"):
    base = f"{side}_{early}"
    new = f"{side}_{added}"
    major = "big_down" if side == "down" else "big_up"
    return {
        "major_days_missed_by_close_rule": sum(r[major] and base not in r["signals"] for r in rows),
        "major_days_added_by_reversal": sum(r[major] and base not in r["signals"] and
                                            new in r["signals"] for r in rows),
        "nonmajor_days_added_by_reversal": sum(not r[major] and base not in r["signals"] and
                                               new in r["signals"] for r in rows),
        "major_days_missed_by_both": sum(r[major] and base not in r["signals"] and
                                         new not in r["signals"] for r in rows),
        "examples": [
            dict(day=r["day"], symbol=r["sym"], close_change_pct=r["change_pct"],
                 first_reversal_asof=r["signals"][new]["asof"],
                 first_reversal_total_pct=r["signals"][new]["base_change_pct"],
                 first_reversal_anchor_pct=r["signals"][new]["anchor_change_pct"])
            for r in rows if r[major] and base not in r["signals"] and new in r["signals"]
        ][:12],
    }


def early_reversal_leads(rows, side: str):
    close_name, reverse_name = f"{side}_close", f"{side}_reversal"
    major_key = "big_down" if side == "down" else "big_up"
    paired = []
    for r in rows:
        standard, reversal = r["signals"].get(close_name), r["signals"].get(reverse_name)
        if not standard or not reversal or reversal["asof"] >= standard["asof"]:
            continue
        delta = (datetime.fromisoformat(standard["asof"]) -
                 datetime.fromisoformat(reversal["asof"])).total_seconds()/60
        # Positive for selling earlier at a higher price; positive for buying
        # earlier at a lower price. All proxy comparisons are hypothetical.
        first_open, later_open = reversal["next_bar_open"], standard["next_bar_open"]
        advantage_pp = (100 * (first_open - later_open) / r["previous_close"]
                        if side == "down" else
                        100 * (later_open - first_open) / r["previous_close"]) if (
                            first_open is not None and later_open is not None) else None
        paired.append((r,delta,advantage_pp))
    hits=[x for x in paired if x[0][major_key]]
    examples=sorted(hits,key=lambda x:x[2] if x[2] is not None else float('-inf'),reverse=True)
    out=dict(paired_days=len(paired), major_days=len(hits),
             nonmajor_days=len(paired)-len(hits),
             avg_lead_minutes=round(mean(x[1] for x in paired),2) if paired else None,
             avg_major_lead_minutes=round(mean(x[1] for x in hits),2) if hits else None,
             avg_major_extra_exit_or_entry_pp=round(mean(x[2] for x in hits if x[2] is not None),3)
                 if any(x[2] is not None for x in hits) else None,
             major_best_examples=[
                 dict(day=r["day"],sym=r["sym"],close_change_pct=r["change_pct"],
                      reversal_asof=r["signals"][reverse_name]["asof"],
                      original_asof=r["signals"][close_name]["asof"],
                      lead_minutes=delta, hypothetical_price_improvement_pp=round(adv,3))
                 for r,delta,adv in examples[:8] if adv is not None])
    return out


def afternoon_coverage(rows, side: str):
    major = "big_down" if side == "down" else "big_up"
    families = (f"{side}_close", f"{side}_reversal")
    # All-day warning decisions start at completed bars through 15:50.
    # Their closing outcomes are labels only; not order fill or 14:00 exits.
    old = [r for r in rows if r[major] and not any(
        f in r["signals"] for f in families)]
    late = [r for r in old if any(f in r["full_day_signals"] for f in families)]
    nonmajor = [r for r in rows if not r[major] and not any(
        f in r["signals"] for f in families) and any(
        f in r["full_day_signals"] for f in families)]
    def first_event(r):
        return min((r["full_day_signals"][f] for f in families
                    if f in r["full_day_signals"]), key=lambda e:e["asof"])
    return dict(major_missed_before_13=len(old),
                major_first_detected_after_13=len(late),
                major_still_missed_by_15_50=len(old)-len(late),
                additional_nonmajor_warnings=len(nonmajor),
                major_late_examples=[
                    dict(day=r["day"], sym=r["sym"], close_pct=r["change_pct"],
                         first_asof=first_event(r)["asof"],
                         total_at_warning_pct=first_event(r)["base_change_pct"])
                    for r in late[:15]])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--primary", default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers", default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily", default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output", default=None)
    args = p.parse_args()
    data = json.loads(Path(args.daily).read_text())["split"]
    bars = ingest([args.primary, args.peers])
    rows, calendar = all_days(bars, data)
    output = dict(
        coverage=dict(stock_days=len(rows), first_day=min(r["day"] for r in rows),
                      last_day=max(r["day"] for r in rows), symbols=sorted(bars),
                      big_up=sum(r["big_up"] for r in rows),
                      big_down=sum(r["big_down"] for r in rows)),
        event_families={name:{period:stats(rows,name,side=name.split("_")[0],subset=period)
                              for period in ("all","earlier","later")}
                        for name in ("down_close","down_reversal","up_close","up_reversal")},
        added_detection={side:supplemental(rows, side) for side in ("up","down")},
        afternoon_coverage={side:afternoon_coverage(rows, side) for side in ("up","down")},
        earlier_reversal_warnings={side:early_reversal_leads(rows, side) for side in ("up","down")},
        limit_sensitivity={
            f"{bps}bps": {
                side: {k:round(mean(v),4) if v else None for k,v in (
                    ("price_eligible_rate_pct",[
                      100 * executable_proxy(r["signals"][f"{side}_reversal"],r["mark14"],side,bps)["price_eligible"]
                      for r in rows if f"{side}_reversal" in r["signals"] and
                      executable_proxy(r["signals"][f"{side}_reversal"],r["mark14"],side,bps) is not None]),
                    ("avg_bounded_advantage_pp",[
                      executable_proxy(r["signals"][f"{side}_reversal"],r["mark14"],side,bps)["bounded_advantage_pp"]
                      for r in rows if f"{side}_reversal" in r["signals"] and
                      executable_proxy(r["signals"][f"{side}_reversal"],r["mark14"],side,bps) is not None])
                )} for side in ("up","down")
            } for bps in (15,30,50,100)
        },
    )
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
