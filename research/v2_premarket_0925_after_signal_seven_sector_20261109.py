"""Research-only, 09:25 ET completed-bar, seven-sector forward edge.

Signal uses previous FIVE complete RTH sessions of ETF/peers and ONLY SIP
bars completed by 09:25 ET on the test day; no current-day close is eligible.
Trade comparison enters at 09:30 ET RTH opening mark (not a verified ask),
exits at 14:40 ET = 13:40 CT flat using a completed 14:35 ETF five-min bar.
NO BROKER ORDERS. Historical research reused, NOT untouched test performance.
"""
import json
import csv
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime,time,timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
import v2_sector_alert_precision_grid_20261109 as data

TIMEZONE=ZoneInfo("America/New_York")
SIGNAL_CUTOFF=time(9,20) # last included bar starts at 09:20, closes 09:25
SNAPSHOT=time(9,25)
EXIT_BAR=time(14,35) # last included exit bar closes 14:40 ET
THRESHOLDS=(.25,.5,.75,1.0)
PEER_FRACTION=.5
BREADTH_STALENESS_MIN=10
FRICTION_PP=.30
METRICS={"forward_eod_direction_hit_min_pp":.05,"gross_cost_break_even_pp":FRICTION_PP}

def full_rth_close(bars):
    by_clock={z.strftime("%H:%M"):v for z,v in bars.items()
              if time(9,30)<=z.time()<=time(15,55)}
    if "09:30" not in by_clock or "15:55" not in by_clock or len(by_clock)<65:
        return None
    return by_clock["15:55"][3]

def prior_sessions(cache,sym,day):
    q=[(d,full_rth_close(b)) for d,b in cache[sym].items() if d<day]
    return [(d,p) for d,p in sorted(q) if p is not None]

def asof_bars(bars):
    return {z:v for z,v in bars.items() if time(4,0)<=z.time()<=SIGNAL_CUTOFF}

def latest_asof_price(bars):
    q=asof_bars(bars)
    if not q:return None
    z=max(q)
    anchor=datetime.combine(z.date(),SNAPSHOT,TIMEZONE)
    if z+timedelta(minutes=5)>anchor:raise AssertionError("future bar")
    if (anchor-(z+timedelta(minutes=5))).total_seconds()>BREADTH_STALENESS_MIN*60:return None
    return (z,q[z][3])

def bar_at(bars,clock):
    found=[(z,v) for z,v in bars.items() if z.time()==clock]
    return found[0][1] if len(found)==1 else None

def analyze_sector(cache,sector,threshold):
    etf,peers=data.SECTOR[sector]
    rows=[]
    syms=(etf,)+peers
    full_index={sym:sorted((d,v) for d,bars in cache[sym].items()
                        if (v:=full_rth_close(bars)) is not None) for sym in syms}
    full_dates={sym:[d for d,v in full_index[sym]] for sym in syms}
    for day in sorted(cache[etf]):
        prior={sym:full_index[sym][:bisect_left(full_dates[sym],day)] for sym in syms}
        if any(len(prior[sym])<5 for sym in syms):continue
        # Skip incomplete preceding-date join: bars must have last complete RTH
        # on same market session for ETF and each peer.
        refdate=prior[etf][-1][0]
        if any(prior[sym][-1][0]!=refdate for sym in syms):continue
        ref={sym:prior[sym][-1][1] for sym in syms}
        b={sym:cache[sym].get(day,{}) for sym in syms}
        latest={sym:latest_asof_price(b[sym]) for sym in syms}
        event=None
        if all(latest.values()):
            etf_stamp,etf_price=latest[etf]
            if etf_stamp.time()!=SIGNAL_CUTOFF:
                rows.append({"day":day,"event":None})
                continue  # no exact 09:20 bar -> ABSTAIN, not dropped sample
            for sign in (1,-1):
                move=sign*(etf_price/ref[etf]-1)*100
                if move<threshold:continue
                confirmed=sum(sign*(latest[sym][1]/ref[sym]-1)*100 >= threshold*PEER_FRACTION for sym in peers)
                required=2
                if confirmed<required:continue
                opening=bar_at(b[etf],time(9,30))
                exitbar=bar_at(b[etf],EXIT_BAR)
                mark=exitbar[3] if exitbar else None
                open_px=opening[0] if opening else None
                forecast=sign*(mark/etf_price-1)*100 if mark else None
                traded=sign*(mark/open_px-1)*100-FRICTION_PP if mark and open_px else None
                event={"signal_et":"09:25","signal_price":round(etf_price,6),"source_bar_start_et":"09:20",
                       "source_refday":refdate,"ref_price":round(ref[etf],6),
                       "sign":sign,"ref_to_signal_pct":round(move,6),
                       "peers_confirmed":confirmed,
                       "exit_et":"14:40","exit_mark":round(mark,6) if mark else None,
                       "future_sign_pct":round(forecast,6) if forecast is not None else None,
                       "model_0930_open":round(open_px,6) if open_px else None,
                       "modeled_0930_1440_after_30bp_pct":round(traded,6) if traded is not None else None}
                break
        rows.append({"day":day,"event":event})
    return rows

def summarize(rows):
    es=[r["event"] for r in rows if r["event"]]
    scored=[e for e in es if e["future_sign_pct"] is not None]
    tr=[e for e in es if e["modeled_0930_1440_after_30bp_pct"] is not None]
    scored_early=[e for e in es if e["sign"]==1]
    outcome={"days":len(rows),"alerts":len(es),"abstained":len(rows)-len(es),
       "up":len(scored_early),"down":len(es)-len(scored_early),
       "future_scored":len(scored),"future_hit":sum(e["future_sign_pct"]>=.05 for e in scored),
       "future_wrong":sum(e["future_sign_pct"]<=-.05 for e in scored),
       "future_tiny":sum(-.05<e["future_sign_pct"]<.05 for e in scored),
       "avg_forward_pct":round(mean(e["future_sign_pct"] for e in scored),4) if scored else None,
       "model_scored":len(tr),"after30bp_positive":sum(e["modeled_0930_1440_after_30bp_pct"]>0 for e in tr),
       "model_avg_after30bp_pct":round(mean(e["modeled_0930_1440_after_30bp_pct"] for e in tr),4) if tr else None,
       "worst_model_pct":round(min(e["modeled_0930_1440_after_30bp_pct"] for e in tr),4) if tr else None,
       "best_model_pct":round(max(e["modeled_0930_1440_after_30bp_pct"] for e in tr),4) if tr else None}
    outcome["by_direction"]={}
    for d,label in ((1,"up"),(-1,"down")):
        x=[e for e in scored if e["sign"]==d]
        y=[e for e in tr if e["sign"]==d]
        outcome["by_direction"][label]={"scored":len(x),"correct":sum(e["future_sign_pct"]>=.05 for e in x),
            "after_cost_wins":sum(e["modeled_0930_1440_after_30bp_pct"]>0 for e in y),
            "after_cost_trades":len(y)}
    return outcome

def run(cache):
    out={"method":"09:20-09:25 ET completed SIP bar signal, prior five completed RTH sessions, <=10m breadth freshness, unobserved BOATS may change overnight conclusions, 09:30 ET open-mark entrance and 14:40 ET completed mark exit; NO actual fills",
    "percent_thresholds":THRESHOLDS,"peer_frac":PEER_FRACTION,"illustrative_roundtrip_cost_bp":30,
    "known_reuse_exploration_not_blind":True,"sectors":{}}
    for sector in data.SECTOR:
        a={}
        for t in THRESHOLDS:
            rows=analyze_sector(cache,sector,t)
            partition=int(len(rows)*.7)
            a[str(t)]={"all":summarize(rows),"early":summarize(rows[:partition]),
                       "later_reused":summarize(rows[partition:]),
                       "sample_events":next(({"date":r["day"],**r["event"]} for r in rows if r["event"]),None)}
        out["sectors"][sector]=a
    return out

def main():
    cache=data.load()
    result=run(cache)
    result["data_availability"]={}
    daily=[]
    # Cache prior ETF closes once; do not rescan 250 historical sessions for
    # every new daily audit line (also reduces host CPU contention).
    prev_index={}
    prev_dates={}
    for sector,(etf,peers) in data.SECTOR.items():
        prev_index[etf]=sorted((d,v) for d,bars in cache[etf].items()
                   if (v:=full_rth_close(bars)) is not None)
        prev_dates[etf]=[d for d,v in prev_index[etf]]
    cols=["sector","day","signal_et","source_bar_start_et","source_refday",
          "ref_price","signal_price","sign","ref_to_signal_pct","peers_confirmed",
          "exit_et","exit_mark","future_sign_pct","model_0930_open",
          "modeled_0930_1440_after_30bp_pct","outcome_etf_close_1555",
          "outcome_prevclose_to_final_pct","outcome_open_to_final_pct",
          "outcome_close_move_atleast_3pct"]
    for sector,(etf,peers) in data.SECTOR.items():
        events=analyze_sector(cache,sector,.5)
        n_etf=n_peers=n_exit=0
        for row in events:
            day=row["day"]
            etfbars=cache[etf].get(day,{})
            n_etf+=(bar_at(etfbars,SIGNAL_CUTOFF) is not None)
            n_peers+=(all(latest_asof_price(cache[sym].get(day,{})) for sym in peers))
            n_exit+=(bar_at(etfbars,EXIT_BAR) is not None)
            pi=bisect_left(prev_dates[etf],day)
            prevclose=prev_index[etf][pi-1][1] if pi>0 else None
            closebar=bar_at(etfbars,time(15,55))
            openbar=bar_at(etfbars,time(9,30))
            close=closebar[3] if closebar else None
            open_px=openbar[0] if openbar else None
            # HINDSIGHT audit targets ONLY: never feed these back to signal.
            eod=100*(close/prevclose-1) if close and prevclose else None
            open_to_close=100*(close/open_px-1) if close and open_px else None
            daily.append({"sector":sector,"day":day,**(row["event"] or {}),
               "outcome_etf_close_1555":round(close,6) if close else None,
               "outcome_prevclose_to_final_pct":round(eod,6) if eod is not None else None,
               "outcome_open_to_final_pct":round(open_to_close,6) if open_to_close is not None else None,
               "outcome_close_move_atleast_3pct":abs(eod)>=3 if eod is not None else None})
        result["data_availability"][sector]={"eligible_sessions":len(events),
            "etf_exact_0920_start_bar_available":n_etf,
            "all_peers_fresh_within_10min_by_0925":n_peers,
            "exit_1435_bar_available":n_exit}
    audit=Path("/tmp/v2_premarket_0925_after_signal_seven_sector_20261109_daily.csv")
    with audit.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore")
        w.writeheader();w.writerows(daily)
    out=Path("/tmp/v2_premarket_0925_after_signal_seven_sector_20261109.json")
    out.write_text(json.dumps(result,indent=2)+"\n")
    for sector,r in result["sectors"].items():
        print("\n"+sector)
        for t,z in r.items():
            s=z["later_reused"]
            print(" threshold",t,"days",s["days"],"events",s["alerts"],
                  "forward_hit",s["future_hit"],"/",s["future_scored"],
                  "after30bp",s["after30bp_positive"],"/",s["model_scored"],
                  "mean_net",s["model_avg_after30bp_pct"])
if __name__=="__main__": main()
