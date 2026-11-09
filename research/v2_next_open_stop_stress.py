"""Next-regular-open hold-vs-signal exit study, V2 research only.

Uses next session opening print strictly as a retrospective outcome; never an
alert input. Five-minute OHLC next-bar opens are *not* bid/ask executable fills.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, date, time
from functools import lru_cache
import json
from pathlib import Path
from statistics import mean, median

from research.v2_asof_sector_confirmation import asof_context, prior_regular_closes
from research.v2_sector_confirmation_retrigger import first_confirmed, FAMILIES, LATER_START
from research.v2_reversal_and_limit_stress import all_days
from research.v2_stock_risk_dayphase import ET, ingest

FRICTION = 0.0015
LIMIT_BPS = 30


def price_scenario(event: dict, next_session_open: float | None, previous_close: float,
                   side: str, limit_bps: int = LIMIT_BPS):
    """Sell: advantage vs holding to next regular open. Buy: next-open P&L.

    Non-price-eligible next-bar orders are modeled as unfilled; zero benefit
    for a sell, no entry for a buy. No assumption about later cancel/replace.
    """
    intraday_open = event["next_bar_open"]
    if intraday_open is None or next_session_open is None or min(
            previous_close, intraday_open, next_session_open) <= 0:
        return None
    ref = event["price"]
    if side == "down":
        bound = ref * (1 - limit_bps / 10000)
        price_eligible = intraday_open * (1-FRICTION) >= bound
        saved_pp = (100 * (intraday_open - next_session_open) *
                    (1-FRICTION) / previous_close) if price_eligible else 0
        return {"price_eligible": price_eligible,
                "bounded_advantage_nextopen_pp": saved_pp,
                "unbounded_advantage_nextopen_pp":
                    100 * (intraday_open - next_session_open) *
                    (1-FRICTION) / previous_close}
    if side == "up":
        bound = ref * (1 + limit_bps / 10000)
        price_eligible = intraday_open * (1+FRICTION) <= bound
        gain_pct = (100 * (next_session_open*(1-FRICTION) /
                           (intraday_open*(1+FRICTION)) - 1)
                    if price_eligible else 0)
        return {"price_eligible": price_eligible,
                "bounded_advantage_nextopen_pp": gain_pct}
    raise ValueError(side)


def analyze(bars: dict, daily: dict):
    rows, days = all_days(bars, daily)
    calendar = [date.fromisoformat(d) for d in days]
    previous = dict(zip(calendar[1:],calendar[:-1]))
    next_day = dict(zip(calendar[:-1],calendar[1:]))
    closes = prior_regular_closes(bars)
    buckets = {sym: defaultdict(dict) for sym in bars}
    for sym, times in bars.items():
        for at, row in times.items():
            buckets[sym][at.date()][at] = row
    @lru_cache(maxsize=100000)
    def context(sym, day, at):
        return asof_context(bars, closes, sym, day, previous[day], at)
    records = []
    for row in rows:
        day, sym = date.fromisoformat(row["day"]), row["sym"]
        next_d = next_day.get(day)
        next_bar = (bars[sym].get(datetime.combine(next_d,time(9,30), ET))
                    if next_d else None)
        next_open = next_bar[0] if next_bar else None
        today = buckets[sym][day]
        for family in FAMILIES:
            if family not in row["signals"]:
                continue
            side = family.split("_")[0]
            major = row["big_up"] if side=="up" else row["big_down"]
            for variant in ("baseline","both"):
                event = first_confirmed(
                    bars=today, previous_close=row["previous_close"], day=day,
                    family=family, variant=variant,
                    context_at=lambda asof: context(sym,day,asof))
                if event is None:
                    continue
                score = price_scenario(event,next_open,row["previous_close"],side)
                records.append({"symbol":sym, "day":row["day"], "family":family,
                                "variant":variant, "major":major,
                                "later":day>=LATER_START,
                                "event_asof":event["asof"], "next_regular_open":next_open,
                                "score":score})
    out={}
    for family in FAMILIES:
        out[family]={}
        for period in ("all","earlier","later"):
            out[family][period]={}
            for variant in ("baseline","both"):
                ev=[r for r in records if r["family"]==family and
                    r["variant"]==variant and (period=="all" or
                    r["later"]==(period=="later"))]
                scored=[r for r in ev if r["score"] is not None]
                edges=[r["score"]["bounded_advantage_nextopen_pp"] for r in scored]
                eligible=[r for r in scored if r["score"]["price_eligible"]]
                eligible_edges=[r["score"]["bounded_advantage_nextopen_pp"]
                                for r in eligible]
                out[family][period][variant]={
                    "warnings":len(ev), "major_closing_days":sum(r["major"] for r in ev),
                    "next_regular_open_observed":len(scored),
                    "next_open_missing":len(ev)-len(scored),
                    "next_bar_price_eligible":len(eligible),
                    "mean_bounded_vs_nextopen_pp_or_pct":round(mean(edges),4) if edges else None,
                    "median_bounded_vs_nextopen_pp_or_pct":round(median(edges),4) if edges else None,
                    "positive_improvement_count":sum(v>0 for v in edges),
                    "negative_improvement_count":sum(v<0 for v in edges),
                    "mean_eligible_only_pp_or_pct":round(mean(eligible_edges),4)
                      if eligible_edges else None,
                }
    illustrations={}
    for side in ("up","down"):
        family="down_reversal" if side=="down" else "up_close"
        eligible=[r for r in records if r["family"]==family and
                  r["variant"]=="both" and r["major"] and
                  r["score"] and r["score"]["price_eligible"]]
        eligible.sort(key=lambda r: r["score"]["bounded_advantage_nextopen_pp"],
                      reverse=True)
        illustrations[side]=[
            dict(day=r["day"],symbol=r["symbol"],first_warning=r["event_asof"],
                 next_regular_open=r["next_regular_open"],
                 bounded_advantage=round(
                     r["score"]["bounded_advantage_nextopen_pp"],3))
            for r in eligible[:5]]
    return {"dataset_stock_days":len(rows), "next_open_provenance":
            "Next trading day 09:30 ET 5m SIP bar OPEN, never a bid/ask fill",
            "friction_per_side_pct":FRICTION*100,"limit_buffer_bps":LIMIT_BPS,
            "per_family":out, "major_examples":illustrations}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output")
    args=p.parse_args()
    result=analyze(ingest([args.primary,args.peers]),
        json.loads(Path(args.daily).read_text())["split"])
    if args.output:
        Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
