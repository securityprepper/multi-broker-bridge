"""V2 fixed preopen sector breadth early-warning study; research only, no broker calls.

Strictly use completed five-minute SIP bars at 08:25 or 09:10 ET and
previous completed regular close. Outcome labels and future prices score
the signal AFTER it is generated. No live feed or order submission.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from math import ceil, isfinite
from statistics import mean
from pathlib import Path
import argparse, json
from research.v2_stock_risk_dayphase import ET, ingest, collect, phase
from research.v2_reversal_and_limit_stress import all_days
from research.v2_asof_sector_confirmation import prior_regular_closes

ETF = "SOXX"
PEERS = ("AMD","MU","SNDK","NVDA","AVGO","WDC","TSM","INTC")
SNAPSHOTS = (time(8,30), time(9,15))
SECTOR_PCT = 0.5
STOCK_PCT = 1.0
LIMIT_BP = 30
FRICTION_BP = 15
LATER = date(2026,9,1)

def fixed_snapshot(bars, closes, symbol, previous_day, target_day, cutoff, side):
    if side not in ("up","down"):
        raise ValueError("side")
    if symbol not in (*PEERS,ETF):
        raise ValueError("symbol")
    asof = datetime.combine(target_day, cutoff, ET)
    completed = asof - timedelta(minutes=5)
    if completed.date() != target_day:
        return None
    ret = {}
    for sym in (*PEERS, ETF):
        row = bars.get(sym,{}).get(completed)
        base = closes.get(sym,{}).get(previous_day)
        if row is None or base is None or not all(
                isfinite(x) and x > 0 for x in (base,row[3])):
            return None
        ret[sym] = (row[3]/base-1)*100
    sign = 1 if side=="up" else -1
    peer_names = [p for p in PEERS if p!=symbol]
    aligned = sum(sign*ret[s]>=SECTOR_PCT for s in peer_names)
    if (sign*ret[ETF] < SECTOR_PCT or
        aligned < ceil(len(peer_names)/2) or
        sign*ret[symbol] < STOCK_PCT):
        return None
    observed_price = bars[symbol][completed][3]
    # Next opening is a future price outcome, NOT a signal input or verified fill.
    next_row = bars[symbol].get(asof)
    return dict(asof=asof.isoformat(), observed_price=observed_price,
                own_move_pct=round(ret[symbol],4),
                soxx_move_pct=round(ret[ETF],4), aligned=aligned,
                peer_count=len(peer_names),
                next_bar_open=next_row[0] if next_row else None)

def earliest_signal(bars, closes, symbol, previous_day, target_day, side):
    for cutoff in SNAPSHOTS:
        event=fixed_snapshot(bars,closes,symbol,previous_day,target_day,cutoff,side)
        if event is not None:
            return event
    return None

def price_mark(event, previous_close, rth_open, side, close_mark=None):
    if event is None or event["next_bar_open"] is None or rth_open is None:
        return None
    ref=event["observed_price"]
    nxt=event["next_bar_open"]
    adverse=FRICTION_BP/10000
    limit=LIMIT_BP/10000
    if side=="down":
        proxy=nxt*(1-adverse)
        eligible=proxy>=ref*(1-limit)
        advantage=100*(proxy-rth_open*(1-adverse))/previous_close
    else:
        proxy=nxt*(1+adverse)
        eligible=proxy<=ref*(1+limit)
        advantage=100*(rth_open*(1+adverse)-proxy)/previous_close
    close_adv=None
    if close_mark is not None:
        if side=="down":
            close_adv=100*(proxy-close_mark*(1-adverse))/previous_close
        else:
            close_adv=100*(close_mark*(1-adverse)-proxy)/previous_close
    return {"eligible":eligible,
            "vs_0930_pp":round(advantage,5) if eligible else 0.0,
            "vs_close_pp":round(close_adv,5) if eligible and close_adv is not None else (
                0.0 if not eligible else None)}

def summary(rows,side):
    subset=[r for r in rows if r["side"]==side]
    major=[r for r in subset if r["major"]]
    signals=[r for r in subset if r["event"]]
    hits=[r for r in signals if r["major"]]
    nonmajor=[r for r in signals if not r["major"]]
    baseline=[r for r in subset if r["baseline"]]
    combined=[r for r in subset if r["baseline"] or r["event"]]
    incremental=[r for r in hits if not r["baseline"]]
    early=[r for r in hits if abs(r["event"]["own_move_pct"]) < 5]
    proxied=[r["scenario"] for r in signals if r["scenario"] is not None]
    eligible=[r["vs_0930_pp"] for r in proxied if r["eligible"]]
    close_values=[r["vs_close_pp"] for r in proxied if r["vs_close_pp"] is not None]
    close_eligible=[r["vs_close_pp"] for r in proxied if r["eligible"] and r["vs_close_pp"] is not None]
    return dict(stock_days=len(subset),major_days=len(major),
        warnings=len(signals),major_hits=len(hits),major_missed=len(major)-len(hits),
        original_preopen_warnings=len(baseline),
        original_preopen_major_hits=sum(r["major"] for r in baseline),
        original_preopen_nonmajor_warnings=sum(not r["major"] for r in baseline),
        union_warning_count=len(combined),
        union_major_hits=sum(r["major"] for r in combined),
        union_nonmajor_warnings=sum(not r["major"] for r in combined),
        nonmajor_warnings=len(nonmajor),major_hits_before_5pct=len(early),
        additional_major_hits_over_original_preopen=len(incremental),
        additional_nonmajor_warnings_over_original_preopen=sum(not r["baseline"] for r in nonmajor),
        major_hits_prior_to_original_signal=sum(bool(r["baseline"]) and
            r["event"]["asof"] < r["baseline"] for r in hits),
        future_price_scorable=len(proxied),future_price_limit_eligible=len(eligible),
        mean_eligible_vs_0930_pp=round(mean(eligible),4) if eligible else None,
        mean_bounded_all_signals_vs_close_pp=round(mean(close_values),4) if close_values else None,
        mean_eligible_vs_close_pp=round(mean(close_eligible),4) if close_eligible else None,
        close_improvement_count=sum(v>0 for v in close_values),
        close_adverse_count=sum(v<0 for v in close_values),
        improvement_count=sum(v>0 for v in eligible),
        adverse_count=sum(v<0 for v in eligible),
        missed_major_examples=[dict(symbol=r["symbol"],day=r["day"],close_pct=r["close_change_pct"],
                                  baseline=bool(r["baseline"])) for r in major if not r["event"]][:10])

def preopen_up_baseline(bars,day,prior,previous_close):
    for at in sorted(bars):
        if phase(at,day,prior) not in ('premarket','evening'):
            continue
        old=bars.get(at-timedelta(minutes=15))
        if old is None: continue
        now=bars[at][3]
        if previous_close>0 and old[3]>0 and now>0 and now/previous_close>=1.025 and now/old[3]>=1.01:
            return (at+timedelta(minutes=5)).isoformat()
    return None

def analyze(bars,daily):
    rows,dates=all_days(bars,daily)
    calendar=[date.fromisoformat(v) for v in dates]
    previous={calendar[i]:calendar[i-1] for i in range(1,len(calendar))}
    closes=prior_regular_closes(bars)
    baseline={(r["symbol"],r["day"]):r for r in collect(bars,dates)}
    # Restrict upside baseline scan to preceding evening and the current premarket.
    by_sym_day={}
    for sym,bar_map in bars.items():
        partitions=defaultdict(dict)
        for at,record in bar_map.items(): partitions[at.date()][at]=record
        by_sym_day[sym]=partitions
    results=[]
    for row in rows:
        s=row["sym"]; day=date.fromisoformat(row["day"]); prev=previous[day]
        base=row["previous_close"]
        rth=bars[s].get(datetime.combine(day,time(9,30),ET))
        for side in ("up","down"):
            event=earliest_signal(bars,closes,s,prev,day,side)
            prev_alert=(baseline.get((s,row["day"]),{}).get("pre_asof")
                if side=="down" else preopen_up_baseline(
                    {**by_sym_day[s][prev],**by_sym_day[s][day]},day,prev,base))
            results.append(dict(symbol=s,day=row["day"],side=side,event=event,
              major=row["big_up"] if side=="up" else row["big_down"],
              close_change_pct=row["change_pct"],baseline=prev_alert,
              scenario=price_mark(event,base,rth[0] if rth else None,side,
                    closes[s].get(day))))
    output=dict(coverage=dict(stock_days=len(rows),first=dates[1],last=dates[-1],
                major_up=sum(r["big_up"] for r in rows),
                major_down=sum(r["big_down"] for r in rows)),
        definition=dict(checkpoints_et=["08:30","09:15"],
             soxx_threshold_pct=SECTOR_PCT,peer_majority_threshold_pct=SECTOR_PCT,
             own_threshold_pct=STOCK_PCT,all_peers_contemporaneous_required=True),
        result={},
        note="SIP 5m OHLC price-mark scenarios, not NBBO/BOATS quotes or executable fills.")
    for segment in ("all","earlier","later"):
        a=[r for r in results if segment=="all" or
           (date.fromisoformat(r["day"])>=LATER)==(segment=="later")]
        output["result"][segment]={side:summary(a,side) for side in ("up","down")}
    return output

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    ap.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    ap.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    ap.add_argument("--output")
    args=ap.parse_args()
    result=analyze(ingest([args.primary,args.peers]),
                   json.loads(Path(args.daily).read_text())["split"])
    if args.output: Path(args.output).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()