"""Five completed days prior to each V2 signal: two-sided causal cohort stress.

Research only. No broker, scheduling, or network calls. Outcomes are later
retrospective labels. Limit eligibility uses next five-minute bar opens, NOT
NBBO/fill prices. Criteria are prespecified rather than fit to later sample.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path
from statistics import mean
import argparse
import json

from research.v2_asof_sector_confirmation import prior_regular_closes, asof_context
from research.v2_next_open_stop_stress import price_scenario
from research.v2_reversal_and_limit_stress import all_days
from research.v2_sector_confirmation_retrigger import first_confirmed, LATER_START
from research.v2_stock_risk_dayphase import ET, ingest

FAMILIES = ("up_close", "down_reversal")
SECTOR_WEAK = -5.0
SECTOR_STRONG = 5.0
RELATIVE_LAG = -3.0
RELATIVE_LEAD = 3.0


def five_completed_return(closes, calendar, current):
    """Five session-to-session returns ending PREVIOUS trading day.

    Requires six consecutive completed close observations: prior close
    divided by close six calendar positions earlier. Never today's close.
    """
    try:
        i = calendar.index(current)
    except ValueError:
        return None
    if i < 6:
        return None
    observed = [closes.get(day) for day in calendar[i - 6:i]]
    if any(value is None or value <= 0 for value in observed):
        return None
    return 100 * (observed[-1] / observed[0] - 1)


def cohort(sector5, stock5):
    if sector5 is None or stock5 is None:
        return None
    sector = ("weak" if sector5 <= SECTOR_WEAK else
              "strong" if sector5 >= SECTOR_STRONG else "neutral")
    relative = stock5 - sector5
    lead = ("lagging" if relative <= RELATIVE_LAG else
            "leading" if relative >= RELATIVE_LEAD else "neutral")
    return {"sector": sector, "relative": lead,
            "sector5_pct": round(sector5,4), "stock5_pct": round(stock5,4)}


def summarise(records, side, period, cohort_field, cohort_value):
    subset = [r for r in records if r["side"] == side and
              (period == "all" or r["later"] == (period == "later")) and
              (cohort_field == "all" or r["cohort"][cohort_field] == cohort_value)]
    warned = [r for r in subset if r["event"] is not None]
    scored = [r for r in warned if r["score"] is not None]
    eligible = [r for r in scored if r["score"]["price_eligible"]]
    values = [r["score"]["bounded_advantage_nextopen_pp"] for r in scored]
    hits = sum(r["major"] for r in warned)
    return {"stock_days":len(subset),
            "major_days":sum(r["major"] for r in subset),
            "warnings":len(warned), "major_hits":hits,
            "major_missed":sum(r["major"] for r in subset)-hits,
            "nonmajor_warnings":len(warned)-hits,
            "scorable_next_open":len(scored),
            "price_proxy_eligible":len(eligible),
            "mean_bounded_nextopen_pp_or_pct":round(mean(values),4) if values else None,
            "positive_vs_hold":sum(v>0 for v in values),
            "negative_vs_hold":sum(v<0 for v in values)}


def analyze(bars, daily):
    rows, days = all_days(bars,daily)
    calendar = [date.fromisoformat(d) for d in days]
    prevday = dict(zip(calendar[1:],calendar[:-1]))
    nextday = dict(zip(calendar[:-1],calendar[1:]))
    closes = prior_regular_closes(bars)
    daily_groups = {sym: defaultdict(dict) for sym in bars}
    for symbol, data in bars.items():
        for at, record in data.items():
            daily_groups[symbol][at.date()][at] = record

    @lru_cache(maxsize=100000)
    def context(symbol, day, observed):
        return asof_context(bars, closes, symbol, day, prevday[day], observed)

    records = []
    omitted = 0
    for row in rows:
        symbol, day = row["sym"],date.fromisoformat(row["day"])
        prior5_sector = five_completed_return(closes["SOXX"],calendar,day)
        prior5_stock = five_completed_return(closes[symbol],calendar,day)
        category = cohort(prior5_sector,prior5_stock)
        if category is None or day not in prevday:
            omitted += 1
            continue
        following = nextday.get(day)
        next_open_bar = (bars[symbol].get(datetime.combine(following,time(9,30),ET))
                         if following is not None else None)
        next_open = next_open_bar[0] if next_open_bar else None
        for family in FAMILIES:
            side = family.split("_")[0]
            event = first_confirmed(
                bars=daily_groups[symbol][day],
                previous_close=row["previous_close"],
                day=day, family=family, variant="both",
                context_at=lambda at:context(symbol,day,at))
            score = price_scenario(event,next_open,row["previous_close"],side) if event else None
            records.append({"symbol":symbol,"day":day.isoformat(),"family":family,
                            "side":side,"major":row["big_up"] if side=="up" else row["big_down"],
                            "later":day>=LATER_START,"cohort":category,
                            "event":event,"score":score})
    results={}
    for side in ("up","down"):
        results[side]={}
        for period in ("all","earlier","later"):
            summaries={"all":summarise(records,side,period,"all",None)}
            for field, categories in (("sector",("weak","neutral","strong")),
                                      ("relative",("lagging","neutral","leading"))):
                for category in categories:
                    summaries[f"{field}_{category}"] = summarise(
                        records,side,period,field,category)
            results[side][period]=summaries
    return {"sample":"Split-adjusted SIP five-minute OHLC; bid/ask and BOATS not in file",
            "calendar_first":str(calendar[0]),"calendar_last":str(calendar[-1]),
            "stock_days_with_complete_prior5":len(records)//len(FAMILIES),
            "stock_days_omitted_missing_prior5":omitted,
            "cohort_cutoffs_pct":{"sector_weak":SECTOR_WEAK,"sector_strong":SECTOR_STRONG,
                                  "stock_lag":RELATIVE_LAG,"stock_lead":RELATIVE_LEAD},
            "results":results,
            "warnings":"Cohort differences are observational; sectors other than semiconductors absent. "
                       "No NBBO/BOATS, real fills, or independently tuned/tested thresholds."}


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
