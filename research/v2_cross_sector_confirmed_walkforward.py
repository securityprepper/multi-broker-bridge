"""Research-only cross-sector five-minute, prior-five, precision-first comparison.
No account, quote-routing, or broker order operations.
Candidate signals use only completed SIP bars with start timestamps.
"""
from __future__ import annotations
from datetime import datetime,time,timedelta
from pathlib import Path
from statistics import mean
from collections import defaultdict
from math import sqrt
import argparse,json
from research import v2_gold_miner_preopen_lead as g

SIP=Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
SECTORS={"energy":("XLE","XOM","CVX"),
 "financials":("XLF","JPM","BAC"),
 "industrials":("XLI","CAT","GE"),
 "healthcare":("XLV","UNH","LLY"),
 "software":("IGV","MSFT","CRM")}
RULES=("sector_only","breadth","strong_breadth","prior5_scaled",
       "opening_followthrough","15m_acceleration","prior5_trend")
CLOCKS={"09:25":time(9,35),"10:00":time(10,10)}
TRAIN_CUTOFF="2026-09-01"

def load(path=SIP):
    sessions=defaultdict(dict);src={}
    for sym in sorted({s for ss in SECTORS.values() for s in ss}):
        j=json.loads((path/(sym+"_sip.json")).read_text())
        if j.get("feed")!="sip" or j.get("adjustment")!="split" or j.get("timeframe")!="5Min":
            raise ValueError(f"unknown/corrupt feed: {sym}")
        src[sym]={"bars":len(j["bars"]),"first":j["bars"][0][0] if j["bars"] else None,
                  "last":j["bars"][-1][0] if j["bars"] else None}
        for raw in j["bars"]:
            t=g.parse(raw[0])
            if raw[1]>0 and raw[4]>0:sessions[(sym,t.date().isoformat())][t]=tuple(raw[1:])
    return sessions,src

def abs_prev5_hist(series):
    # Five prior COMPLETED closes yield four completed close-to-close observations.
    return mean(abs(100*(series[i]/series[i-1]-1)) for i in range(1,len(series))) if len(series)>=5 else None

def feature(day,clock,symbol,sessions,prev,prior):
    p=prev.get((symbol,day))
    history=prior.get((symbol,day))
    if p is None or not history:return None
    h,m=map(int,clock.split(":"))
    d=datetime.fromisoformat(day).replace(tzinfo=g.ET,hour=h,minute=m)
    q=g.at(sessions.get((symbol,day),{}),d)
    if not q:return None
    bars=sessions.get((symbol,day),{})
    recent=g.at(bars,d-timedelta(minutes=15))
    rth_open=g.open_mark(bars,time(9,30)) if clock=="10:00" else None
    return {"pct":100*(q[0]/p-1),"last":q[0],
      "mean_abs_prior4":abs_prev5_hist(history),"prior5_trend":100*(p/history[0]-1),
      "recent15":100*(q[0]/recent[0]-1) if recent else None,
      "rth_from_open":100*(q[0]/rth_open-1) if rth_open else None,
      "price_bar_start":q[1]}

def signal(feat,symbols,rule,clock,sign):
    etf,p1,p2=symbols
    if any(x not in feat for x in symbols):return False
    f=[feat[x] for x in symbols]
    if rule=="sector_only":return sign*f[0]["pct"]>=.25
    if rule=="breadth":return sign*f[0]["pct"]>=.25 and all(sign*x["pct"]>=.35 for x in f[1:])
    if rule=="strong_breadth":return sign*f[0]["pct"]>=.50 and all(sign*x["pct"]>=.50 for x in f[1:])
    scaled=(sign*f[0]["pct"]>=max(.20,.80*f[0]["mean_abs_prior4"]) and
            all(sign*x["pct"]>=max(.30,.8*x["mean_abs_prior4"]) for x in f[1:]))
    if rule=="prior5_scaled":return scaled
    if rule=="prior5_trend":return scaled and sign*f[0]["prior5_trend"]>=0
    if clock!="10:00":return False
    if rule=="opening_followthrough":
        return scaled and all(x["rth_from_open"] is not None and sign*x["rth_from_open"]>=.1 for x in f)
    if rule=="15m_acceleration":
        return scaled and f[0]["recent15"] is not None and sign*f[0]["recent15"]>=.1 and all(
             x["recent15"] is not None and sign*x["recent15"]>=.05 for x in f[1:])
    raise ValueError(rule)

def summary_rows(rows):
    if not rows:return {"count":0,"independent_days":0}
    n=len(rows);w=sum(x["net30"]>0 for x in rows)
    return {"count":n,"independent_days":len({x["day"] for x in rows}),
       "win_pct_after30":round(100*w/n,2),"wilson_lower95":round(g.wilson(w,n),4),
       "mean_net15":round(mean(x["gross"]-.15 for x in rows),4),
       "mean_net30":round(mean(x["net30"] for x in rows),4),
       "mean_net60":round(mean(x["gross"]-.60 for x in rows),4),
       "major_sector_hits":sum(x["major"] for x in rows),
       "nonmajor_sector_signals":sum(not x["major"] for x in rows),
       "earliest_major_warning":min((x["signal_at"] for x in rows if x["major"]),default=None),
       "hypothetical_better_than_next_open_pct":round(100*sum(x["exit_adv_next_open_30"]>0
        for x in rows if x["exit_adv_next_open_30"] is not None)/
        max(1,sum(x["exit_adv_next_open_30"] is not None for x in rows)),2)}

def build(path=SIP):
    sessions,src=load(path)
    complete=g.complete_sessions(sessions)
    prev,prior,nxt=g.historical_context(complete)
    daily=[];events=defaultdict(list);counts=defaultdict(lambda:{"positive":0,"negative":0,"mixed":0})
    for sector,syms in SECTORS.items():
        etf,p1,p2=syms
        for day in sorted({d for s,d in complete if s==etf}):
            keys=[(s,day) for s in syms]
            if not all(k in prior and k in prev for k in keys):continue
            if not all(k in complete for k in keys):continue
            changes=[100*(complete[k]["close"]/prev[k]-1) for k in keys]
            rthchanges=[100*(complete[k]["close"]/complete[k]["open"]-1) for k in keys]
            category="positive" if all(x>0 for x in changes) else "negative" if all(x<0 for x in changes) else "mixed"
            counts[sector][category]+=1
            # Label is outcome-only and its volatility threshold uses ONLY prior completed bars.
            basis=max(1,1.5*abs_prev5_hist(prior[(etf,day)]))
            major_up=max(changes[0],rthchanges[0])>=basis
            major_down=min(changes[0],rthchanges[0])<=-basis
            daily.append({"sector":sector,"day":day,"status":category,
                  "etf_close_pct":round(changes[0],4),"etf_rth_pct":round(rthchanges[0],4),
                  "major_up":major_up,"major_down":major_down,
                  "major_threshold_pct":round(basis,4)})
            for clock,enter_time in CLOCKS.items():
                ff={s:feature(day,clock,s,sessions,prev,prior) for s in syms}
                ff={s:val for s,val in ff.items() if val is not None}
                for rule in RULES:
                    for sign in (1,-1):
                        if not signal(ff,syms,rule,clock,sign):continue
                        label="UP" if sign==1 else "DOWN"
                        for asset in ("etf","strongest_peer"):
                            sym=etf if asset=="etf" else max((p1,p2),key=lambda s:(sign*ff[s]["pct"],s))
                            entry=g.open_mark(sessions.get((sym,day),{}),enter_time)
                            end14=g.open_mark(sessions.get((sym,day),{}),time(14,0))
                            if not entry or not end14:continue
                            future=nxt.get((sym,day))
                            gross=sign*100*(end14/entry-1)
                            exitadv=(100*(entry-future)/entry-.30 if sign==-1 and future else
                                     None)
                            k=f"{sector}_{clock}_{rule}_{label}_{asset}"
                            h,mi=map(int,clock.split(":"))
                            obs=datetime.fromisoformat(day).replace(tzinfo=g.ET,hour=h,minute=mi)
                            events[k].append({"sector":sector,"day":day,"symbol":sym,
                               "signal_at":obs.isoformat(),"entry":entry,"exit14":end14,
                               "gross":gross,"net30":gross-.30,
                               "exit_adv_next_open_30":exitadv,"major":major_up if sign==1 else major_down,
                               "etf_close_pct":changes[0],"threshold_pct":basis,
                               "direction":label,"gdx_not_applicable":True})
    return events,daily,counts,src

def evaluate(events,daily,counts,src):
    res={"source":src,"sectors":{}, "sector_counts":dict(counts),
         "market_regimes":"major threshold per ETF date max(1%,1.5 x prior-five four-day-interval mean abs return)",
         "notes":["This uses historical SIP TRADE bars, not NBBO executable quotes.",
           "BOATS not available for these extra sectors; no actual fills.",
           "One position per sector-date per candidate, not multiple correlated trades.",
           "15/30/60bp fees+slippage modeled, not executions.",
           "Prior FIVE completed RTH sessions only; later outcomes never used for signals.",
           "No confirmed 80% after-cost precision; no PAPER/LIVE GO."]}
    for sector,syms in SECTORS.items():
        universe=[d for d in daily if d["sector"]==sector]
        cands={k:v for k,v in events.items() if k.startswith(sector+"_")}
        sub={}
        for k,rows in cands.items():
            sub[k.removeprefix(sector+"_")]={"earlier":summary_rows([x for x in rows if x["day"]<TRAIN_CUTOFF]),
                  "later":summary_rows([x for x in rows if x["day"]>=TRAIN_CUTOFF])}
        # Select strictly on earlier sample; a no-trade policy is mandatory when all fail.
        eligible=[(k,v["earlier"]["mean_net30"],v["earlier"]["win_pct_after30"],
                   v["earlier"]["wilson_lower95"]) for k,v in sub.items()
                 if v["earlier"]["independent_days"]>=30]
        shadow=sorted(eligible,key=lambda x:(-x[1],-x[2],x[0]))[0] if eligible else None
        winner=shadow[0] if shadow and shadow[1]>0 and shadow[2]>=80 and shadow[3]>=.60 else None
        res["sectors"][sector]={"input_3_symbols":syms,
          "complete_days":len(universe),
          "earlier_major_up":sum(x["major_up"] for x in universe if x["day"]<TRAIN_CUTOFF),
          "earlier_major_down":sum(x["major_down"] for x in universe if x["day"]<TRAIN_CUTOFF),
          "later_major_up":sum(x["major_up"] for x in universe if x["day"]>=TRAIN_CUTOFF),
          "later_major_down":sum(x["major_down"] for x in universe if x["day"]>=TRAIN_CUTOFF),
          "earlier_best_shadow":shadow[0] if shadow else None,
          "earlier_best_shadow_stats":sub[shadow[0]] if shadow else None,
          "locked_qualifying_policy":winner,"later_selected":sub.get(winner,{}).get("later") if winner else None,
          "candidates":sub}
    return res

def stock_outcome_audit(path=SIP):
    """ALL individual stocks and ETFs, including untriggered gains and declines."""
    sessions,_=load(path)
    complete=g.complete_sessions(sessions)
    prev,prior,nxt=g.historical_context(complete)
    audit=[]
    for sector,syms in SECTORS.items():
        for sym in syms:
            for day in sorted(d for s,d in complete if s==sym):
                k=(sym,day)
                if k not in prev or k not in prior:continue
                p=prev[k];s=complete[k]
                c=100*(s["close"]/p-1)
                oc=100*(s["close"]/s["open"]-1)
                level=max(1,1.5*abs_prev5_hist(prior[k]))
                n=nxt.get(k)
                audit.append({"sector":sector,"symbol":sym,"day":day,
                    "previous_regular_close":round(p,4),
                    "regular_open":round(s["open"],4),"regular_low":round(s["low"],4),
                    "regular_high":round(s["high"],4),"regular_close":round(s["close"],4),
                    "close_from_previous_pct":round(c,4),
                    "regular_open_to_close_pct":round(oc,4),
                    "major_up":max(c,oc)>=level,"major_down":min(c,oc)<=-level,
                    "dynamic_major_threshold_pct":round(level,4),
                    "next_regular_open":round(n,4) if n else None})
    return audit

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);p.add_argument("--input-dir",default=str(SIP));args=p.parse_args()
    events,daily,counts,src=build(Path(args.input_dir))
    result=evaluate(events,daily,counts,src)
    stock_audit=stock_outcome_audit(Path(args.input_dir))
    result["stock_daily_audit_rows"]=len(stock_audit)
    result["stock_major_up"]=sum(x["major_up"] for x in stock_audit)
    result["stock_major_down"]=sum(x["major_down"] for x in stock_audit)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    Path(args.output+".audit.json").write_text(json.dumps(daily,indent=0))
    Path(args.output+".stock_audit.json").write_text(json.dumps(stock_audit,indent=0))
    # Extensive event audit may be large but remains on isolated host only.
    Path(args.output+".events.json").write_text(json.dumps(events,indent=0))
    print(json.dumps({"sectors":{s:{"counts":result["sector_counts"][s],
               "locked":v["locked_qualifying_policy"],
               "best_shadow":v["earlier_best_shadow"],
               "shadow_earlier":v["earlier_best_shadow_stats"]["earlier"] if v["earlier_best_shadow_stats"] else None,
               "shadow_later":v["earlier_best_shadow_stats"]["later"] if v["earlier_best_shadow_stats"] else None,
               "later_up":v["later_major_up"],"later_down":v["later_major_down"]} for s,v in result["sectors"].items()}},indent=2))
if __name__=="__main__":main()
