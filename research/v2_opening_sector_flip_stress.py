"""V2 opening-sector-flip study: completed SIP five-minute bars, no broker IO.

Candidate is intentionally DISTINCT from owner's prior-close 2.5%/15m1% rule.
At 09:15 ET establish a directional SOXX+peer breadth preopen snapshot.
From 09:35-10:30 ET, alert on an opposite 1 percentage-point SOXX move,
1 pp stock move and 0.5 pp move in at least half the other peers, each
relative to its own prior completed regular-session close. All observations
must be completed bars. Future price marks are for retrospective scoring only.
"""
from __future__ import annotations
import argparse, json
from datetime import date, datetime, time, timedelta
from collections import defaultdict
from functools import lru_cache
from math import ceil
from pathlib import Path
from statistics import mean, median
from research.v2_stock_risk_dayphase import ET, ingest, collect
from research.v2_reversal_and_limit_stress import all_days
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_next_open_stop_stress import price_scenario

ETF = "SOXX"
PEERS = ("AMD","MU","SNDK","NVDA","AVGO","WDC","TSM","INTC")
LATER = date(2026,9,1)
T5 = timedelta(minutes=5)
ANCHOR = time(9,10)
CUTOFFS = tuple(time(m//60,m%60) for m in range(9*60+35,10*60+31,5))

def completed_returns(bars, closes, previous_day, target, start):
    """Require all nine peer bars at exact completed start and prior closes."""
    result = {}
    for sym in (*PEERS,ETF):
        row = bars.get(sym,{}).get(datetime.combine(target,start,ET))
        base = closes.get(sym,{}).get(previous_day)
        if not row or not base or row[3] <= 0 or base <= 0:
            return None
        result[sym] = 100*(row[3]/base-1)
    return result

def preopen_direction(returns):
    if returns is None:
        return 0
    for sign in (1,-1):
        if sign*returns[ETF] >= .5 and sum(sign*returns[p] >= .5 for p in PEERS) >= 4:
            return sign
    return 0

def first_open_flip(bars, closes, symbol, previous_day, target_day):
    """Return first causal flip event or None; side is movement OPPOSITE preopen."""
    if symbol not in (*PEERS,ETF):
        raise ValueError("unsupported symbol")
    pre = completed_returns(bars, closes, previous_day, target_day, ANCHOR)
    direction = preopen_direction(pre)
    if not direction:
        return None
    contra = -direction
    peer_names = [p for p in PEERS if p != symbol]
    for cutoff in CUTOFFS:
        asof = datetime.combine(target_day,cutoff,ET)
        current = completed_returns(bars,closes,previous_day,target_day,
                                    (asof - T5).time())
        if current is None:
            continue
        aligned = sum(contra*(current[p]-pre[p]) >= .5 for p in peer_names)
        if (contra*(current[ETF]-pre[ETF]) < 1.0 or
            contra*(current[symbol]-pre[symbol]) < 1.0 or
            aligned < ceil(len(peer_names)/2)):
            continue
        observation = bars[symbol][asof-T5][3]
        next_row = bars[symbol].get(asof)
        return {"asof":asof.isoformat(),"side":"down" if contra<0 else "up",
                "preopen_direction":"up" if direction>0 else "down",
                "price":observation,
                "next_bar_open":next_row[0] if next_row else None,
                "base_change_pct":round(current[symbol],4),
                "soxx_change_since_preopen_pp":round(current[ETF]-pre[ETF],4),
                "stock_change_since_preopen_pp":round(current[symbol]-pre[symbol],4),
                "peer_breadth":aligned,"peer_count":len(peer_names)}
    return None

def same_day_proxy(event,mark14,base):
    """Retrospective next-bar OPEN eligibility, not guaranteed fill."""
    nxt = event["next_bar_open"]
    if nxt is None or mark14 is None or min(base,nxt,mark14) <= 0:
        return None
    if event["side"] == "down":
        eligible = nxt*.9985 >= event["price"]*.997
        value = 100*(nxt-mark14)*.9985/base
    else:
        eligible = nxt*1.0015 <= event["price"]*1.003
        value = 100*(mark14*.9985/(nxt*1.0015)-1)
    return {"price_eligible":eligible,"bounded_advantage_14_pp":round(value,4) if eligible else 0.0}

def summarize(rows,side):
    subset = [r for r in rows if r["side"]==side]
    major = [r for r in subset if r["major"]]
    triggered = [r for r in subset if r["event"]]
    hits = [r for r in triggered if r["major"]]
    eligible = [r["score14"]["bounded_advantage_14_pp"] for r in triggered
                if r["score14"] is not None]
    nextopen = [r["score_next"]["bounded_advantage_nextopen_pp"]
                for r in triggered if r["score_next"] is not None]
    early = [r for r in hits if abs(r["event"]["base_change_pct"]) < 5]
    signs = [r["score14"]["bounded_advantage_14_pp"] for r in triggered
             if r["score14"] is not None and r["score14"]["price_eligible"]]
    early_strict = [r for r in hits if side=="down" and
                    (r["strict_any_asof"] is None or
                     r["event"]["asof"] < r["strict_any_asof"])]
    never_strict = [r for r in hits if side=="down" and
                    r["strict_any_asof"] is None]
    day_values = defaultdict(list)
    for r in triggered:
        if r["score14"] is not None:
            day_values[r["date"]].append(r["score14"]["bounded_advantage_14_pp"])
    per_day = [mean(v) for v in day_values.values()]
    ex_nov2 = [r["score14"]["bounded_advantage_14_pp"] for r in triggered
               if r["score14"] is not None and r["date"]!="2026-11-02"]
    return {"stock_days":len(subset),"major_days":len(major),
            "warnings":len(triggered),"major_hits":len(hits),
            "major_missed":len(major)-len(hits),
            "nonmajor_warnings":len(triggered)-len(hits),
            "major_hit_before_5pct":len(early),
            "major_hits_earlier_than_strict_or_not_detected_by_1030":len(early_strict) if side=="down" else None,
            "major_hits_no_strict_signal_by_1030":len(never_strict) if side=="down" else None,
            "price_scenarios_14":len(eligible),
            "price_eligible_14":len(signs),
            "mean_bounded_to14_pp":round(mean(eligible),4) if eligible else None,
            "median_bounded_to14_pp":round(median(eligible),4) if eligible else None,
            "signal_day_count":len(day_values),
            "day_equal_mean_to14_pp":round(mean(per_day),4) if per_day else None,
            "mean_to14_excluding_nov2_pp":round(mean(ex_nov2),4) if ex_nov2 else None,
            "positive_14_count":sum(v>0 for v in eligible),
            "negative_14_count":sum(v<0 for v in eligible),
            "next_open_scenarios":len(nextopen),
            "mean_bounded_to_nextopen_pp":round(mean(nextopen),4) if nextopen else None,
            "earliest_major_warnings":[{"symbol":r["symbol"],"date":r["date"],
                "at":r["event"]["asof"],"close_pct":r["close_pct"]}
                for r in sorted(hits,key=lambda r:r["event"]["asof"])[:7]],
            "missed_major_examples":[{"symbol":r["symbol"],"date":r["date"],
                "close_pct":r["close_pct"]} for r in sorted(major,
                key=lambda r:abs(r["close_pct"]),reverse=True) if not r["event"]][:7]}

def analyze(bars,daily):
    universe,days = all_days(bars,daily)
    calendar = [date.fromisoformat(d) for d in days]
    previous = dict(zip(calendar[1:],calendar[:-1]))
    following = dict(zip(calendar[:-1],calendar[1:]))
    closes = prior_regular_closes(bars)
    strict = {(r["symbol"],r["day"]):r for r in collect(bars,days)}
    @lru_cache(maxsize=6000)
    def cached(sym,day):
        return first_open_flip(bars,closes,sym,previous[day],day)
    out=[]
    for row in universe:
        sym = row["sym"]; day = date.fromisoformat(row["day"])
        event = cached(sym,day)
        next_day = following.get(day)
        opening = (bars[sym].get(datetime.combine(next_day,time(9,30),ET))
                   if next_day else None)
        next_open = opening[0] if opening else None
        # Preopen comparison is fixed at 09:15 and is decision-time only.
        pre = completed_returns(bars,closes,previous[day],day,ANCHOR)
        pre_side = ("up" if preopen_direction(pre)>0 else "down"
                    if preopen_direction(pre)<0 else None)
        for side in ("up","down"):
            signal = event if event and event["side"]==side else None
            base=row["previous_close"]
            out.append({"symbol":sym,"date":row["day"],"side":side,
                "major":row["big_up"] if side=="up" else row["big_down"],
                "close_pct":row["change_pct"],"event":signal,
                "preopen":pre_side==side,
                "strict_any_asof":(strict.get((sym,row["day"]),{}).get("any_asof")
                                   if side=="down" else None),
                "score14":same_day_proxy(signal,row["mark14"],base) if signal else None,
                "score_next":(price_scenario(signal,next_open,base,side)
                              if signal else None),
                "prior5_soxx_return":(100*(closes[ETF][calendar[calendar.index(day)-1]]/
                                            closes[ETF][calendar[calendar.index(day)-6]]-1)
                    if calendar.index(day)>=6 and
                        calendar[calendar.index(day)-1] in closes[ETF] and
                        calendar[calendar.index(day)-6] in closes[ETF] else None)})
    result={"period":"2025-11-10 through 2026-11-06",
        "dataset_stock_days":len(universe),
        "major_up":sum(r["big_up"] for r in universe),
        "major_down":sum(r["big_down"] for r in universe),
        "definition":"09:15 preopen SOXX+4/8 peers +/-0.5%; from 09:35 to 10:30 first opposite SOXX and stock >=1 percentage point and >=half other peers >=0.5 pp since 09:15; completed 5m bars only",
        "segments":{}}
    for segment in ("all","earlier","later"):
        records = [r for r in out if segment=="all" or
                   (date.fromisoformat(r["date"])>=LATER)==(segment=="later")]
        result["segments"][segment] = {side:summarize(records,side)
                                      for side in ("up","down")}
    for side in ("up","down"):
        result["segments"]["all"][side]["prior5_weak_soxx"]={
            label:{"warnings":len(s),"mean_to14_pp":round(mean(
                r["score14"]["bounded_advantage_14_pp"] for r in s
                if r["score14"] is not None),4) if any(
                r["score14"] is not None for r in s) else None}
            for label,s in (("down_at_least_5pct",[r for r in out if r["side"]==side
                   and r["event"] and r["prior5_soxx_return"] is not None
                   and r["prior5_soxx_return"]<=-5]),
                   ("other",[r for r in out if r["side"]==side and r["event"]
                   and r["prior5_soxx_return"] is not None
                   and r["prior5_soxx_return"]>-5]))}
    result["nov2_2026"]=[
        {"symbol":r["symbol"],"side":r["side"],
         "event":r["event"]["asof"],"close_pct":r["close_pct"],
         "signal_price_relative_prev_close_pct":r["event"]["base_change_pct"]}
        for r in out if r["date"]=="2026-11-02" and r["event"]]
    result["price_provenance"]="SIP 5-minute OHLC marks only; no NBBO, BOATS or executable fills"
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    parser.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    parser.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    parser.add_argument("--output")
    opt=parser.parse_args()
    res=analyze(ingest([opt.primary,opt.peers]),
                json.loads(Path(opt.daily).read_text())["split"])
    if opt.output:
        Path(opt.output).write_text(json.dumps(res,indent=2,sort_keys=True))
    print(json.dumps(res,indent=2,sort_keys=True))
if __name__=="__main__":
    main()
