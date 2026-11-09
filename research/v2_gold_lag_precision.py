"""V2-only, causal GLD -> gold miner 15/30 minute lead/lag study.

Independent sessions; completed SIP 5-minute trade bars. NO BROKER actions.
Signals are computed before any same-day outcome is consulted.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from datetime import datetime,timedelta,time
from statistics import mean
from pathlib import Path
from research import v2_gold_miner_preopen_lead as g

DATA=g.BARS_DIR
TRAIN_END="2026-09-01"
CLOCKS=((9,45),(10,0),(10,15),(10,30),(11,0))
LAGS=(0,15,30)
GOLD_MOVES=(.15,.25)
RULES=("gold_only","gold_plus_miner","miner_only")
COST_BPS=(15,30,60)
MINERS=("NEM","AEM","KGC")

def decision(day,hh,mm):
    return datetime.fromisoformat(day).replace(tzinfo=g.ET,hour=hh,minute=mm)

def price_asof(bars,when):
    # Exactly one completed five-minute bar; no stale quote substitutions.
    row=g.at(bars,when,max_age_min=0)
    return row[0] if row else None

def move(bars,start,end):
    if start>=end:return None
    p0=price_asof(bars,start);p1=price_asof(bars,end)
    return 100*(p1/p0-1) if p0 and p1 else None

def sample_features(day,t,lag,sessions,prior):
    # Gold lead ends lag minutes before miner decision; miner lookback ends now.
    keys=("GLD","GDX",*MINERS)
    if not all((s,day) in prior for s in keys):return None
    end=t-timedelta(minutes=lag)
    gold=move(sessions.get(("GLD",day),{}),end-timedelta(minutes=15),end)
    changes={s:move(sessions.get((s,day),{}),t-timedelta(minutes=15),t)
             for s in ("GDX",*MINERS)}
    if gold is None or any(x is None for x in changes.values()):return None
    return gold,changes

def qualify(feat,side,rule,threshold):
    gold,miners=feat
    sg=1 if side=="up" else -1
    go=sg*gold>=threshold
    miner=sg*miners["GDX"]>=.10 and sum(sg*miners[s]>=.10 for s in MINERS)>=2
    return {"gold_only":go,"gold_plus_miner":go and miner,"miner_only":miner}[rule]

def asof_choice(feat,side):
    # Previous completed 15-minute miner strength only; never future price.
    sign=1 if side=="up" else -1
    return sorted(MINERS,key=lambda s:(-sign*feat[1][s],s))[0]

def sector_outcome(complete,prev,day,side):
    key=("GDX",day)
    p=prev.get(key);a=complete.get(key)
    if not p or not a:return None
    ch=100*(a["close"]/p-1);oc=100*(a["close"]/a["open"]-1)
    if side=="up":return max(ch,oc)>=3
    return min(ch,oc)<=-3

def build(data_dir=DATA):
    sessions,source=g.load_data(data_dir)
    complete=g.complete_sessions(sessions)
    prev,prior,nxt=g.historical_context(complete)
    days=sorted({d for s,d in complete if s=="GLD" and
                 all((x,d) in complete and (x,d) in prior for x in ("GDX",*MINERS))})
    events=defaultdict(list);audit=[]
    for day in days:
        label={}
        for side in ("up","down"):label[side]=sector_outcome(complete,prev,day,side)
        audit.append({"day":day,"major_gdx_up":label["up"],"major_gdx_down":label["down"],
             "gdx_rth_close":complete[("GDX",day)]["close"],
             "gdx_prior_rth_close":prev[("GDX",day)]})
        for lag in LAGS:
            for threshold in GOLD_MOVES:
                for rule in RULES:
                    for side in ("up","down"):
                        key=f"{rule}_lag{lag}_gold{threshold:.2f}_{side}"
                        for hh,mm in CLOCKS:
                            t=decision(day,hh,mm)
                            feat=sample_features(day,t,lag,sessions,prior)
                            if feat is None or not qualify(feat,side,rule,threshold):continue
                            sym=asof_choice(feat,side)
                            entry_t=t+timedelta(minutes=5)
                            price=g.open_mark(sessions.get((sym,day),{}),entry_t.time())
                            exit_price=g.open_mark(sessions.get((sym,day),{}),time(14,0))
                            if not price or not exit_price:continue
                            sign=1 if side=="up" else -1
                            gross=sign*100*(exit_price/price-1)
                            next_open=nxt.get((sym,day))
                            if next_open:
                                next_adv=sign*100*(next_open/price-1)-.30
                            else:next_adv=None
                            events[key].append({"day":day,"observed_at":t.isoformat(),
                               "gold_impulse_end":(t-timedelta(minutes=lag)).isoformat(),
                               "lag_min":lag,"symbol":sym,"direction":side,
                               "rule":rule,"gold_15m_pct":round(feat[0],4),
                               "miner_gdx_15m_pct":round(feat[1]["GDX"],4),
                               "entry_at":entry_t.isoformat(),"entry_mark":price,
                               "exit14_mark":exit_price,"next_open_mark":next_open,
                               "gross_pct":round(gross,6),"net15":round(gross-.15,6),
                               "net30":round(gross-.30,6),"net60":round(gross-.60,6),
                               "next_open_net30":round(next_adv,6) if next_adv is not None else None,
                               "major_sector_outcome":label[side]})
                            break # ONE candidate per sector-date, earliest as-of signal
    return events,audit,source

def stats(rows):
    n=len(rows);win=sum(x["net30"]>0 for x in rows)
    if not n:return {"signals":0,"independent_days":0}
    return {"signals":n,"independent_days":len({x["day"] for x in rows}),
       "profitable":win,"win_pct":round(win/n*100,2),
       "wilson95_lower_pct":round(g.wilson(win,n)*100,2),
       "mean_net15":round(mean(x["net15"] for x in rows),4),
       "mean_net30":round(mean(x["net30"] for x in rows),4),
       "mean_net60":round(mean(x["net60"] for x in rows),4),
       "mean_next_open_net30":round(mean(x["next_open_net30"] for x in rows
                   if x["next_open_net30"] is not None),4) if any(x["next_open_net30"] is not None for x in rows) else None,
       "major_hits":sum(x["major_sector_outcome"] for x in rows),
       "nonmajor_warnings":sum(not x["major_sector_outcome"] for x in rows),
       "earliest_major_warning":min((x["observed_at"] for x in rows
                      if x["major_sector_outcome"]),default=None)}

def evaluate(events,audit,source):
    periods={"earlier":lambda d:d<TRAIN_END,"later":lambda d:d>=TRAIN_END}
    report={"sources":source,"eligible_sector_days":len(audit),
      "status":{},"policies":{},
      "constraints":["PREMARKET data and existing split-adjusted historical SIP trade bars; not executable quotes.",
        "Gold signal 15m impulse ending lag=0/15/30m before miner decision; 15/30 are actual lead studies.",
        "Gold GLD ETF proxy, not spot gold/futures; no contemporaneous earnings/news inputs.",
        "First eligible signal from 09:45/10:00/10:15/10:30/11:00; delayed entry at next completed bar +5 minutes.",
        "Prior FIVE completed RTH days; no same-day close in signals; OOS selected only on pre-September train.",
        "Cash/no trade when earlier sample fails 80% after-cost wins / sample size / mean; NO broker orders."]}
    for name,test in periods.items():
        rows=[x for x in audit if test(x["day"])]
        report["status"][name]={"total_days":len(rows),
             "major_up_days":sum(x["major_gdx_up"] for x in rows),
             "major_down_days":sum(x["major_gdx_down"] for x in rows)}
    for key,rows in events.items():
        report["policies"][key]={p:stats([r for r in rows if fn(r["day"])])
                                for p,fn in periods.items()}
    # Freeze selected policy on training statistics exclusively, never search the holdout.
    winners=[(k,v["earlier"]["mean_net30"],v["earlier"]["win_pct"])
             for k,v in report["policies"].items()
             if v["earlier"]["independent_days"]>=30 and
                v["earlier"]["win_pct"]>=80 and
                v["earlier"]["wilson95_lower_pct"]>=60 and
                v["earlier"]["mean_net30"]>0]
    report["qualified_earlier_only"]=sorted(winners,key=lambda v:-v[1])
    report["selected_for_deploy"]="NO_TRADE" if not winners else winners[0][0]
    # The shadow policy is exploratory and NOT chosen by looking at later outcomes.
    shadows=[(k,v["earlier"]["mean_net30"]) for k,v in report["policies"].items()
              if v["earlier"]["independent_days"]>=30]
    best=max(shadows,key=lambda x:x[1])[0] if shadows else None
    report["best_train_shadow"]=best
    report["best_train_shadow_holdout"]=report["policies"][best]["later"] if best else None
    report["largest_train_win_pct"]=max((v["earlier"]["win_pct"] for v in report["policies"].values()
                               if v["earlier"]["independent_days"]>=30),default=None)
    return report

def main():
    a=argparse.ArgumentParser();a.add_argument("--input-dir",default=str(DATA))
    a.add_argument("--output",required=True);p=a.parse_args()
    e,d,s=build(Path(p.input_dir));r=evaluate(e,d,s)
    Path(p.output).write_text(json.dumps(r,indent=2))
    Path(p.output+".events.json").write_text(json.dumps(e))
    Path(p.output+".daily_audit.json").write_text(json.dumps(d))
    print(json.dumps({"status":r["status"],"eligible_sector_days":r["eligible_sector_days"],
       "candidates":len(r["policies"]),"selected":r["selected_for_deploy"],
       "best_train_shadow":r["best_train_shadow"],
       "shadow_holdout":r["best_train_shadow_holdout"],
       "qualified":r["qualified_earlier_only"][:3]},indent=2))
if __name__=="__main__":main()
