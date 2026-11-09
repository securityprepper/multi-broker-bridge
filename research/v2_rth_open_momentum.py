"""V2 research-only rising-sector open-to-current momentum replay.

Independent from the preopen reversal strategy; measures what could have
been observed at completed five-minute SIP bars, without broker operations.
The next-bar and 14:00/next-session prices are scoring outcomes only.
"""
from __future__ import annotations
import argparse, json
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
from research.v2_early_flip_sensitivity import ETF, PEERS, LATER, prior5_return

T5=timedelta(minutes=5)
T15=timedelta(minutes=15)
OPEN=time(9,30)
VARIANTS={
    "early_1030": {"last": time(10,30), "recent15": False},
    "through_1300": {"last": time(13,0), "recent15": False},
    "recent15_1300": {"last": time(13,0), "recent15": True},
}


def asof_open_momentum(bars, day, cutoff, symbol, recent15=False):
    """Use only regular opening quotes and completed intraday candles."""
    if symbol not in (*PEERS,ETF):
        raise ValueError("unknown symbol")
    if cutoff.tzinfo is None:
        raise ValueError("naive as-of timestamp")
    local=cutoff.astimezone(ET)
    if local.date()!=day or local.time()<time(9,35) or local.time()>time(13,0):
        return None
    if local.minute % 5 or local.second or local.microsecond:
        return None
    completed=local-T5
    if completed.date()!=day:
        return None
    moves={}
    recent={}
    for sym in (*PEERS,ETF):
        opening=bars.get(sym,{}).get(datetime.combine(day,OPEN,ET))
        current=bars.get(sym,{}).get(completed)
        if opening is None or current is None:
            return None
        price_open=opening[0]
        price_now=current[3]
        if not all(isfinite(v) and v>0 for v in (price_open,price_now)):
            return None
        moves[sym]=100*(price_now/price_open-1)
        if recent15:
            # The 15m comparison bar must be COMPLETED by cutoff.
            if cutoff.time()<time(9,50):
                return None
            past=bars.get(sym,{}).get(completed-T15)
            if past is None or not isfinite(past[3]) or past[3]<=0:
                return None
            recent[sym]=100*(price_now/past[3]-1)
    peers=[p for p in PEERS if p!=symbol]
    aligned=sum(moves[p]>=.25 for p in peers)
    if moves[ETF]<.50 or moves[symbol]<1.00 or aligned<ceil(len(peers)/2):
        return None
    if recent15 and (recent[ETF]<.20 or recent[symbol]<.40):
        return None
    return {"soxx_open_pct":round(moves[ETF],4),
            "own_open_pct":round(moves[symbol],4),
            "peers":aligned,"peer_count":len(peers),
            "own_recent15_pct":round(recent[symbol],4) if recent15 else None,
            "soxx_recent15_pct":round(recent[ETF],4) if recent15 else None}


def first_signal(bars, day, symbol, variant):
    """Monitoring until a signal qualifies (not just first failed candidate)."""
    if variant not in VARIANTS:
        raise ValueError("unknown variant")
    setup=VARIANTS[variant]
    for m in range(9*60+35,setup["last"].hour*60+setup["last"].minute+1,5):
        at=datetime.combine(day,time(m//60,m%60),ET)
        ctx=asof_open_momentum(bars,day,at,symbol,setup["recent15"])
        if ctx is None:
            continue
        price=bars[symbol][at-T5][3]
        future=bars[symbol].get(at)
        return {"at":at.isoformat(), "price":price,
                "next_bar_open": future[0] if future else None,
                "side":"up",**ctx}
    return None


def bounded_entry_to14(event, mark14, friction_bp=15, limit_bp=30):
    """A next-bar print is NOT proof of bid/ask executable liquidity."""
    if friction_bp<0 or limit_bp<=0:
        raise ValueError("unreasonable costs")
    nxt=event["next_bar_open"]
    if nxt is None or mark14 is None or min(nxt,mark14,event["price"])<=0:
        return None
    f=friction_bp/10000
    buy=nxt*(1+f)
    eligible=buy<=event["price"]*(1+limit_bp/10000)
    return {"price_eligible":eligible,
            "modeled_return_pct":round(100*(mark14*(1-f)/buy-1),4) if eligible else 0.0}


def summarize(rows,variant,period):
    subset=[r for r in rows if r["variant"]==variant and
            (period=="all" or r["later"]==(period=="later"))]
    entered=[r for r in subset if r["event"]]
    hit=[r for r in entered if r["major_up"]]
    outcomes=[r["score15"]["modeled_return_pct"] for r in entered
              if r["score15"] is not None]
    nextopen=[r["nextscore"]["bounded_advantage_nextopen_pp"] for r in entered
              if r["nextscore"] is not None]
    days=defaultdict(list)
    for r in entered:
        if r["score15"] is not None:
            days[r["day"]].append(r["score15"]["modeled_return_pct"])
    missed=sorted([r for r in subset if r["major_up"] and not r["event"]],
                  key=lambda r: r["change_pct"],reverse=True)
    return {"stockdays":len(subset),
            "major_gain_days":sum(r["major_up"] for r in subset),
            "major_loss_days":sum(r["major_down"] for r in subset),
            "rth_openclose_3pct_days":sum(r["rth_openclose_3pct"] for r in subset),
            "signals":len(entered),
            "major_gainers_caught":len(hit),
            "major_gainers_missed":sum(r["major_up"] for r in subset)-len(hit),
            "nonmajor_up_signals":len(entered)-len(hit),
            "major_down_signals":sum(r["major_down"] for r in entered),
            "rth_openclose_3pct_hits":sum(r["rth_openclose_3pct"] for r in entered),
            "early_before_5pct_close_return":sum(
                r["event"]["prevclose_pct_at_signal"]<5 for r in hit),
            "signals_after_1030":sum(r["event"]["at"][11:16]>"10:30" for r in entered),
            "earliest_major_signal":min((r["event"]["at"] for r in hit),default=None),
            "15bp_price_eligible":sum(r["score15"]["price_eligible"] for r in entered
                                      if r["score15"] is not None),
            "15bp_scorable":len(outcomes),
            "15bp_mean_to14_pct":round(mean(outcomes),4) if outcomes else None,
            "15bp_median_to14_pct":round(median(outcomes),4) if outcomes else None,
            "15bp_day_equal_mean_to14_pct":round(mean(map(mean,days.values())),4)
                        if days else None,
            "30bp_mean_to14_pct":round(mean(
                r["score30"]["modeled_return_pct"] for r in entered
                if r["score30"] is not None),4) if any(
                r["score30"] is not None for r in entered) else None,
            "30bp_price_eligible":sum(r["score30"]["price_eligible"] for r in entered
                                      if r["score30"] is not None),
            "nextopen_mean_15bp_pct":round(mean(nextopen),4) if nextopen else None,
            "profitable_14_count":sum(v>0 for v in outcomes),
            "unprofitable_14_count":sum(v<0 for v in outcomes),
            "missed_largest_gain_examples":[{"symbol":r["sym"],"date":r["day"],
                    "close_pct":r["change_pct"]} for r in missed[:5]]}


def analyze(bars,daily):
    universe,days=all_days(bars,daily)
    dates=[date.fromisoformat(s) for s in days]
    dateindex={d:i for i,d in enumerate(dates)}
    following={dates[i]:dates[i+1] for i in range(len(dates)-1)}
    closes=prior_regular_closes(bars)
    out=[]
    for row in universe:
        sym=row["sym"]
        day=date.fromisoformat(row["day"])
        rth=bars[sym].get(datetime.combine(day,OPEN,ET))
        if rth is None or rth[0]<=0:
            continue
        rth_close=closes.get(sym,{}).get(day)
        if rth_close is None:
            continue
        openclose=100*(rth_close/rth[0]-1)
        nextday=following.get(day)
        nxt=bars[sym].get(datetime.combine(nextday,OPEN,ET)) if nextday else None
        futureopen=nxt[0] if nxt else None
        for variant in VARIANTS:
            event=first_signal(bars,day,sym,variant)
            if event:
                event["prevclose_pct_at_signal"]=round(
                    100*(event["price"]/row["previous_close"]-1),4)
            out.append({"variant":variant,"sym":sym,"day":row["day"],
                        "later":day>=LATER,"change_pct":row["change_pct"],
                        "major_up":row["big_up"],"major_down":row["big_down"],
                        "rth_openclose_3pct":openclose>=3,
                        "prior5_soxx_pct":prior5_return(closes,dates,dateindex[day]),
                        "event":event,
                        "score15":bounded_entry_to14(event,row["mark14"],15)
                                    if event else None,
                        "score30":bounded_entry_to14(event,row["mark14"],30)
                                    if event else None,
                        "nextscore":price_scenario(event,futureopen,
                            row["previous_close"],"up") if event else None})
    result={"stockdays":len(universe),"tested_dayrows":len(out)//len(VARIANTS),
            "major_up_close":sum(r["big_up"] for r in universe),
            "major_down_close":sum(r["big_down"] for r in universe),
            "period":f"{dates[0]} through {dates[-1]}",
            "definition":"Regular opening 09:30 print to completed 5m bars; SOXX +0.5%, target +1%, half other peers +0.25%; optional 15m momentum +0.2% SOXX/+0.4% target; 09:35..10:30 or 13:00",
            "segments":{},"later_days_examples":{},"prior5_weak_5pct":{}}
    for segment in ("all","earlier","later"):
        result["segments"][segment]={variant:summarize(out,variant,segment)
                                     for variant in VARIANTS}
    for variant in VARIANTS:
        ev=[r for r in out if r["variant"]==variant and r["event"] and
            r["prior5_soxx_pct"] is not None]
        weak=[r for r in ev if r["prior5_soxx_pct"]<=-5]
        others=[r for r in ev if r["prior5_soxx_pct"]>-5]
        result["prior5_weak_5pct"][variant]={
            "weak_signals":len(weak),"other_signals":len(others),
            "weak_mean_to14_pct":round(mean(r["score15"]["modeled_return_pct"]
                          for r in weak if r["score15"] is not None),4)
                          if weak else None,
            "other_mean_to14_pct":round(mean(r["score15"]["modeled_return_pct"]
                          for r in others if r["score15"] is not None),4)
                          if others else None}
        result["later_days_examples"][variant]=[
            {"symbol":r["sym"],"day":r["day"],"at":r["event"]["at"],
             "close_pct":r["change_pct"]}
            for r in out if r["variant"]==variant and r["later"] and
            r["event"] and r["major_up"]][:12]
    result["limitations"]="SIP five-minute price-mark eligibility, not NBBO/BOATS fills; no synchronized news/futures or V1 orders"
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    ap.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    ap.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    ap.add_argument("--output")
    o=ap.parse_args()
    result=analyze(ingest([o.primary,o.peers]),
                   json.loads(Path(o.daily).read_text())["split"])
    if o.output:
        Path(o.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()