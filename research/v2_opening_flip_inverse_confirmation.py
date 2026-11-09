"""V2 postopen sector flip plus SOXS/SOXL direction confirmation, offline only.

SOXS and SOXL are leveraged products, correlated to SOXX, not independent
proof of a causal move. All inputs at the instant of each completed 5m bar.
Price marks at the following bar and after 14:00 are outcomes, never inputs.
"""
from __future__ import annotations
import argparse,json
from datetime import date,datetime,time,timedelta
from math import ceil
from pathlib import Path
from statistics import mean
from research.v2_stock_risk_dayphase import ET,ingest
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_reversal_and_limit_stress import all_days
from research.v2_next_open_stop_stress import price_scenario
from research.v2_opening_sector_flip_stress import (
    ETF,PEERS,LATER,CUTOFFS,ANCHOR,T5,preopen_direction,completed_returns,
    first_open_flip,same_day_proxy)

EXTRA=("SOXS","SOXL")
EXTRA_MOVE_PP=2.0

def inverse_confirmation_at(extra, extra_closes, previous_day, target, asof,
                            first_direction, variant, threshold_pp=EXTRA_MOVE_PP):
    """True only on two actual completed BOUGHT/FALLING ETF candles.
    SOXS rising and SOXL falling confirm a down sector flip, vice versa.
    'soxs' requires only SOXS; 'both' requires both; no future bars.
    """
    if variant not in ("soxs","both") or threshold_pp<=0 or threshold_pp>50:
        raise ValueError("variant/threshold")
    sign=-first_direction
    vals={}
    for s in EXTRA if variant=="both" else ("SOXS",):
        base=extra_closes.get(s,{}).get(previous_day)
        anchor=extra.get(s,{}).get(datetime.combine(target,ANCHOR,ET))
        current=extra.get(s,{}).get(asof-T5)
        if not base or not anchor or not current or base<=0 or anchor[3]<=0 or current[3]<=0:
            return False
        vals[s]=100*(current[3]-anchor[3])/base
    # If preopen sector bullish, down flip expected SOXS +2pp and SOXL -2pp.
    # If preopen sector bearish, inverse signs apply.
    if (-sign)*vals["SOXS"] < threshold_pp:
        return False
    if variant=="both" and sign*vals["SOXL"] < threshold_pp:
        return False
    return True

def confirmed_flip(base,closes,extra,extra_closes,symbol,previous_day,target_day,variant,threshold_pp=EXTRA_MOVE_PP):
    if symbol not in (*PEERS,ETF):
        raise ValueError("symbol")
    pre=completed_returns(base,closes,previous_day,target_day,ANCHOR)
    direction=preopen_direction(pre)
    if not direction:
        return None
    contra=-direction
    others=[s for s in PEERS if s!=symbol]
    for checkpoint in CUTOFFS:
        asof=datetime.combine(target_day,checkpoint,ET)
        current=completed_returns(base,closes,previous_day,target_day,(asof-T5).time())
        if current is None:
            continue
        breadth=sum(contra*(current[p]-pre[p])>=.5 for p in others)
        if not (contra*(current[ETF]-pre[ETF])>=1 and
                contra*(current[symbol]-pre[symbol])>=1 and
                breadth>=ceil(len(others)/2)):
            continue
        if not inverse_confirmation_at(extra,extra_closes,previous_day,
                target_day,asof,direction,variant,threshold_pp):
            continue
        price=base[symbol][asof-T5][3]
        next_bar=base[symbol].get(asof)
        return {"asof":asof.isoformat(),"side":"down" if contra<0 else "up",
                "price":price,"next_bar_open":next_bar[0] if next_bar else None,
                "base_change_pct":round(current[symbol],4),
                "soxx_from_preopen_pp":round(current[ETF]-pre[ETF],4),
                "peer_breadth":breadth}
    return None

def summary(rows,side,variant):
    subset=[x for x in rows if x["side"]==side and x["variant"]==variant]
    chosen=[x for x in subset if x["event"]]
    hits=[x for x in chosen if x["major"]]
    scores=[x["score14"] for x in chosen if x["score14"] is not None]
    nxt=[x["next_score"]["bounded_advantage_nextopen_pp"] for x in chosen
         if x["next_score"] is not None]
    lag=[x["lag_min"] for x in chosen if x["lag_min"] is not None]
    outcomes=[v["bounded_advantage_14_pp"] for v in scores]
    return {"warnings":len(chosen),"major_hits":len(hits),
        "nonmajor_warnings":len(chosen)-len(hits),
        "major_early_before_5pct":sum(abs(x["event"]["base_change_pct"])<5 for x in hits),
        "limit_price_eligible_marks":sum(v["price_eligible"] for v in scores),
        "scorable_nextbar_marks":len(scores),
        "mean_bounded_to14_pp":round(mean(outcomes),4) if outcomes else None,
        "mean_bounded_to_nextopen_pp":round(mean(nxt),4) if nxt else None,
        "delay_vs_first_flip_mean_minutes":round(mean(lag),2) if lag else None,
        "delayed_vs_first_flip_count":sum(v>0 for v in lag),
        "favorable_to14_count":sum(v>0 for v in outcomes),
        "adverse_to14_count":sum(v<0 for v in outcomes)}

def analyze(base,daily,extra):
    rows,days=all_days(base,daily)
    calendar=[date.fromisoformat(x) for x in days]
    previous=dict(zip(calendar[1:],calendar[:-1]))
    nxt=dict(zip(calendar[:-1],calendar[1:]))
    closes=prior_regular_closes(base)
    extra_closes=prior_regular_closes(extra)
    ledger=[]
    nov2=[]
    for r in rows:
        d=date.fromisoformat(r["day"]);s=r["sym"]
        origin=first_open_flip(base,closes,s,previous[d],d)
        evs={"initial":origin}
        for name,kind,threshold in (
                ("soxs_2","soxs",2.0),("both_2","both",2.0),
                ("both_4","both",4.0),("both_6","both",6.0)):
            evs[name]=confirmed_flip(base,closes,extra,extra_closes,
                                     s,previous[d],d,kind,threshold)
        following=nxt.get(d)
        nextrow=(base[s].get(datetime.combine(following,time(9,30),ET))
                 if following else None)
        next_price=nextrow[0] if nextrow else None
        for variant,e in evs.items():
            for side in ("down","up"):
                event=e if e and e["side"]==side else None
                lag=((datetime.fromisoformat(event["asof"])-
                      datetime.fromisoformat(origin["asof"])).total_seconds()/60
                     if event and origin else None)
                ledger.append({"day":r["day"],"symbol":s,"variant":variant,
                    "side":side,"major":r["big_down"] if side=="down"
                        else r["big_up"],"event":event,"lag_min":lag,
                    "score14":same_day_proxy(event,r["mark14"],r["previous_close"])
                        if event else None,
                    "next_score":price_scenario(event,next_price,
                        r["previous_close"],side) if event else None})
                if d==date(2026,11,2) and event:
                    nov2.append({"symbol":s,"variant":variant,"side":side,
                        "at":event["asof"],"event_vs_close_pct":event["base_change_pct"],
                        "closing_day_pct":r["change_pct"]})
    out={"stock_days":len(rows),"major_up":sum(r["big_up"] for r in rows),
         "major_down":sum(r["big_down"] for r in rows),
         "definition":"Initial SOXX+peer postopen flip, optionally confirmed at each same completed bar by SOXS and optionally SOXL opposite moves of 2, 4, or 6 pp since 09:15 ET. Recheck all checkpoints, never only first unconfirmed alert.",
         "periods":{},"nov2_2026":nov2,
         "limitations":"Only SIP 5m OHLC, NOT actual NBBO, BOATS, fills or realized P&L. Leveraged ETFs are correlated, not independent causal evidence."}
    for span in ("all","earlier","later"):
        subset=[x for x in ledger if span=="all" or
                (date.fromisoformat(x["day"])>=LATER)==(span=="later")]
        out["periods"][span]={side:{
            v:summary(subset,side,v) for v in ("initial","soxs_2","both_2","both_4","both_6")}
            for side in ("up","down")}
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    parser.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    parser.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    parser.add_argument("--soxs",default="/tmp/soxs_52wk_5min_sip_adjusted.json")
    parser.add_argument("--soxl",default="/tmp/soxl_52wk_5min_sip_adjusted.json")
    parser.add_argument("--output")
    arg=parser.parse_args()
    result=analyze(ingest([arg.primary,arg.peers]),
                   json.loads(Path(arg.daily).read_text())["split"],
                   ingest([arg.soxs,arg.soxl]))
    if arg.output:
        Path(arg.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":
    main()
