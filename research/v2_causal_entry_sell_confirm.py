"""V2 isolated two-sided as-of gates. NO broker/production I/O.

Research studies how to reject weak first-hour BUY setups and confirm SELL warnings
after exactly one additional completed five-minute bar. Historical future outcomes
are used ONLY for scoring; not for filtering or event creation.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean

from research.v2_stock_risk_dayphase import ET, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_rth_open_momentum import first_signal
from research.v2_locked_exit_policy_walkforward import policy_outcome
from research.v2_downside_early_sell_opportunity_cost import (
    analyze as downside_replay, price_scenario
)
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_early_flip_sensitivity import LATER, prior5_return

T5 = timedelta(minutes=5)
FILTERS = ("baseline", "sector_5m", "stock_sector_5m",
           "sector_5m_020", "no_weak_prior5", "sector_5m_no_weak_prior5")
CONFIRMS = ("base", "stock_down_010", "sector_down_000",
            "stock_sector_down_000", "stock_sector_down_010")

def prior_close_asof(closes, sym, previous_day, target_day):
    """Prevents same-day final close from entering any live feature."""
    if previous_day is None:
        return None
    if previous_day >= target_day:
        raise ValueError("reference close must be a strictly earlier session")
    return closes.get(sym, {}).get(previous_day)

def observed_close(bars, sym, observed_at):
    """Five-minute bars are indexed by BAR START; must finish by observed_at."""
    bar = bars.get(sym, {}).get(observed_at - T5)
    return bar[3] if bar and bar[3] > 0 else None

def five_minute_move(bars, sym, observed_at, ref_close):
    """Return 5m move in percentage POINTS of previous regular-session close."""
    if ref_close is None or ref_close <= 0:
        return None
    now = observed_close(bars, sym, observed_at)
    before = observed_close(bars, sym, observed_at - T5)
    return 100*(now-before)/ref_close if now is not None and before is not None else None

def has_upside_filter(which, sector5, stock5, prior5):
    """Only observed, as-of inputs. Strict missing-data rejection."""
    if which not in FILTERS:
        raise ValueError("unknown upside filter")
    if which == "baseline":
        return True
    if which == "sector_5m":
        return sector5 is not None and sector5 >= 0
    if which == "stock_sector_5m":
        return sector5 is not None and stock5 is not None and sector5 >= 0 and stock5 >= 0
    if which == "sector_5m_020":
        return sector5 is not None and sector5 >= 0.20
    if which == "no_weak_prior5":
        return prior5 is not None and prior5 > -5
    return sector5 is not None and prior5 is not None and sector5 >= 0 and prior5 > -5

def confirmed_five_minute(which, bar_start, start_signal, 
                          prev_stock_close, prev_soxx_close,
                          sector_bar_start=None,sector_before=None):
    """Completed following 5m candle; no high/low within candle used.

    Caller MUST provide bar_start (the candle starting at original alert time)
    and its immediately preceding completed close (start_signal). The first
    confirm event is at original alert + 5 minutes, never at alert itself.
    """
    if which not in CONFIRMS:
        raise ValueError("unknown confirmation variant")
    if which == "base":
        return True
    if (bar_start is None or start_signal is None or
            prev_stock_close is None or prev_stock_close <= 0 or
            bar_start[3] <= 0 or start_signal <= 0):
        return False
    stock_delta=100*(bar_start[3]-start_signal)/prev_stock_close
    if which == "stock_down_010":
        return stock_delta <= -.10+1e-8
    if (sector_bar_start is None or prev_soxx_close is None or
            prev_soxx_close <= 0 or sector_bar_start[3] <= 0 or
            sector_before is None or sector_before <= 0):
        return False
    # The preceding SOXX close is provided explicitly by caller below,
    # aligned with the original alert completed-bar timestamp.
    soxx_delta=100*(sector_bar_start[3]-sector_before)/prev_soxx_close
    if which == "sector_down_000":
        return soxx_delta <= 0
    if which == "stock_sector_down_000":
        return stock_delta <= 0 and soxx_delta <= 0
    return stock_delta <= -.10+1e-8 and soxx_delta <= -.10+1e-8

def day_equal(rows, value_key, days):
    g=defaultdict(list)
    for r in rows:
        g[r["day"]].append(r[value_key])
    return mean(mean(g[d]) if d in g else 0 for d in days) if days else None

def entry_study(bars, daily):
    universe, sessions=all_days(bars,daily)
    closes=prior_regular_closes(bars)
    sdates=[date.fromisoformat(s) for s in sessions]
    idx={d:i for i,d in enumerate(sdates)}
    records=[]
    previous_dates=dict(zip(sdates[1:],sdates[:-1]))
    for row in universe:
        day=date.fromisoformat(row["day"])
        sym=row["sym"]
        ev=first_signal(bars,day,sym,"early_1030")
        if not ev:
            continue
        at=datetime.fromisoformat(ev["at"]).astimezone(ET)
        prior=row["previous_close"]
        sector_prior=prior_close_asof(closes,"SOXX",previous_dates.get(day),day)
        score=policy_outcome(bars[sym],ev,row["mark14"],"hold_1400")
        if score is None:
            continue
        sector5=five_minute_move(bars,"SOXX",at,sector_prior)
        stock5=five_minute_move(bars,sym,at,prior)
        p5=prior5_return(closes,sdates,idx[day])
        records.append(dict(day=row["day"],sym=sym,at=ev["at"],
                            up=row["big_up"],down=row["big_down"],
                            score=score["net_pct"], eligible=score["eligible_entry"],
                            sector5=sector5,stock5=stock5,prior5=p5,
                            selected={p:has_upside_filter(p,sector5,stock5,p5)
                                      for p in FILTERS}))
    out={"overall_stockdays":len(universe),"major_up":sum(r["big_up"] for r in universe),
         "major_down":sum(r["big_down"] for r in universe),
         "baseline_signals":len(records),"policies":{}}
    for name in FILTERS:
        out["policies"][name]={}
        for period,eligible in (("all",lambda x:True),("earlier",lambda x:x<LATER),
                                ("later",lambda x:x>=LATER)):
            base=[r for r in records if eligible(date.fromisoformat(r["day"]))]
            sub=[r for r in base if r["selected"][name]]
            days=sorted({r["day"] for r in base})
            # Daily-zero metric uses SAME baseline signal dates (avoid changing
            # denominator to only the days on which a filtered entry wins).
            g=defaultdict(list)
            for r in sub:g[r["day"]].append(r["score"])
            daily_mean=mean([mean(g[d]) if g[d] else 0 for d in days]) if days else None
            out["policies"][name][period]={
                "signals":len(sub),"independent_days":len(g),
                "retained_major_up":sum(r["up"] for r in sub),
                "retained_major_down":sum(r["down"] for r in sub),
                "major_winners_excluded_from_baseline":sum(r["up"] for r in base)-sum(r["up"] for r in sub),
                "mean_signal_pct":round(mean(r["score"] for r in sub),4) if sub else None,
                "same_baseline_days_zero_if_no_trade_pct":round(daily_mean,4) if daily_mean is not None else None,
                "price_eligible_entries":sum(r["eligible"] for r in sub)}
    return out,records

def downside_study(bars,daily):
    _,rows=downside_replay(bars,daily)
    _,calendar=all_days(bars,daily)
    session_days=sorted(set(r["day"] for r in rows))
    next_day=dict(zip(calendar[:-1],calendar[1:]))
    previous_day=dict(zip(calendar[1:],calendar[:-1]))
    closes=prior_regular_closes(bars)
    results={k:[] for k in CONFIRMS}
    for r in rows:
        h=r["all_union"]
        if not h:continue
        at=datetime.fromisoformat(h["asof"]).astimezone(ET)
        day=date.fromisoformat(r["day"])
        sym=r["sym"]
        prior=previous_day.get(r["day"])
        prior_date=date.fromisoformat(prior) if prior else None
        prev_close=prior_close_asof(closes,sym,prior_date,day)
        prev_soxx=prior_close_asof(closes,"SOXX",prior_date,day)
        if prev_close is None or prev_soxx is None:
            continue
        original=observed_close(bars,sym,at)
        nxt=bars[sym].get(at)
        soxx_at=bars.get("SOXX",{}).get(at)
        soxx_original=observed_close(bars,"SOXX",at)
        # Required future/point-in-time prices for scoring only.
        nextd=next_day.get(r["day"])
        nextbar=bars[sym].get(at+T5)
        morning=bars[sym].get(datetime.combine(day,time(9,30),ET))
        following=bars[sym].get(datetime.combine(
            date.fromisoformat(nextd),time(9,30),ET)) if nextd else None
        for name in CONFIRMS:
            if name=="base":
                hit=h
            else:
                if not nxt or original is None or soxx_original is None:
                    continue
                if not confirmed_five_minute(name,nxt,original,prev_close,
                                              prev_soxx,soxx_at,soxx_original):
                    continue
                now=at+T5
                hit={"asof":now.isoformat(),"source":name,
                     "signal_price":nxt[3],
                     "next_bar_open":nextbar[0] if nextbar else None,
                     "total_pct":100*(nxt[3]/prev_close-1)}
            sc=price_scenario(hit,prev_close,following[0] if following else None,
                   morning[0] if morning and 
                   datetime.fromisoformat(hit["asof"]).astimezone(ET)<
                   datetime.combine(day,time(9,30),ET) else None)
            results[name].append({"day":r["day"],"sym":sym,"asof":hit["asof"],
                "source":hit["source"],"down":r["major_down"],"up":r["major_up"],
                "close_pct":r["close_pct"],"gap_down5":r["gap_down5"],
                "pct_at":hit["total_pct"],
                "score":sc["advantage_to_next_open_pp"] if sc else None,
                "eligible":sc["eligible_price_proxy"] if sc else None})
    out={"overall_stockdays":len(rows),
         "major_down":sum(r["major_down"] for r in rows),
         "major_up":sum(r["major_up"] for r in rows),
         "rules":{}}
    base_days=sorted(set(r["day"] for r in results["base"]))
    for name,rr in results.items():
        out["rules"][name]={}
        for period,valid in (("all",lambda x:True),("earlier",lambda x:x<LATER),
                             ("later",lambda x:x>=LATER)):
            subset=[r for r in rr if valid(date.fromisoformat(r["day"]))]
            days=[d for d in base_days if valid(date.fromisoformat(d))]
            scores=[r["score"] for r in subset if r["score"] is not None]
            hits=[r for r in subset if r["down"]]
            nonmajor=[r for r in subset if not r["down"]]
            mean_same=day_equal([r for r in subset if r["score"] is not None],"score",days)
            out["rules"][name][period]={
                "warnings":len(subset),"warning_days":len(set(r["day"] for r in subset)),
                "major_down_hits":len(hits),"major_down_missed":sum(
                    r["major_down"] for r in rows if valid(date.fromisoformat(r["day"])))-len(hits),
                "major_down_warn_before5":sum(r["pct_at"]>-5 for r in hits),
                "nonmajor_down_warnings":len(nonmajor),
                "major_up_warning":sum(r["up"] for r in subset),
                "preopen_warnings":sum(
                    datetime.fromisoformat(r["asof"]).astimezone(ET) <
                    datetime.combine(date.fromisoformat(r["day"]),time(9,30),ET)
                    for r in subset),
                "preceding_evening_warnings":sum(
                    datetime.fromisoformat(r["asof"]).astimezone(ET).date() <
                    date.fromisoformat(r["day"]) for r in subset),
                "earliest_severe":min((r["asof"] for r in hits),default=None),
                "benefit_count":sum(v>0 for v in scores),
                "harm_count":sum(v<0 for v in scores),
                "price_eligible_proxy":sum(r["eligible"] is True for r in subset),
                "scorable_with_next_open":len(scores),
                "mean_sale_vs_next_open_pp":round(mean(scores),4) if scores else None,
                "day_equal_with_zero_on_baseline_warn_dates_pp":round(mean_same,4) if mean_same is not None else None}
    return out,results,rows

def analyze(bars,daily):
    buys,buys_raw=entry_study(bars,daily)
    sells,sells_raw,daily_rows=downside_study(bars,daily)
    return {"buy_track":buys,"sell_track":sells,
            "period":"2025-11-10 to 2026-11-06",
            "limits":"SIP 5m OHLC proxy (not executable bid/ask); prior five completed only; no QQQ/futures/news/V1 fills; 15bp sell and buy friction, 30bp limit envelope"}, buys_raw,sells_raw,daily_rows

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--output")
    a.add_argument("--audit-output")
    z=a.parse_args()
    bars=ingest(["/tmp/semis_52wk_5min_sip_adjusted.json",
                 "/tmp/semis_peers_52wk_5min_adjusted.json"])
    daily=json.loads(Path("/tmp/semis_52weeks_alpaca_daily.json").read_text())["split"]
    r,buys,sells,rows=analyze(bars,daily)
    if z.output:Path(z.output).write_text(json.dumps(r,indent=2,sort_keys=True))
    if z.audit_output:
        buy_index={(b["day"],b["sym"]):b for b in buys}
        sell_index=defaultdict(dict)
        for variant,evs in sells.items():
            for e in evs:sell_index[e["day"],e["sym"]][variant]=e
        for row in rows:
            d=date.fromisoformat(row["day"])
            points=[v for at,v in bars[row["sym"]].items() if
                    at.date()==d and time(9,30)<=at.time()<=time(15,55)]
            row["rth_low_outcome_only"]=min((v[2] for v in points),default=None)
            row["rth_high_outcome_only"]=max((v[1] for v in points),default=None)
            row["filtered_buy_signals"]=buy_index.get((row["day"],row["sym"]))
            row["five_minute_sell_confirmations"]=sell_index.get((row["day"],row["sym"]),{})
        Path(z.audit_output).write_text(json.dumps(rows,indent=1,sort_keys=True))
    print(json.dumps(r,indent=2,sort_keys=True))

if __name__=="__main__":
    main()