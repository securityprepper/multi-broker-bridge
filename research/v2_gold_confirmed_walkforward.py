"""V2 research: one position per GOLD-MINER sector session, as-of walk-forward.
Bar timestamps represent START of 5m interval, never a completed bar early.
Outputs are hypothetical price marks, NOT broker execution estimates.
"""
from __future__ import annotations
import argparse, json
from datetime import datetime, time, timedelta
from pathlib import Path
from collections import defaultdict
from statistics import mean
from research import v2_gold_miner_preopen_lead as old

# These fixed candidate hypotheses are audited even when they never fire.
CLOCKS={"09:25":time(9,35),"10:00":time(10,10)}
RULES=("unconditional","gold_only","miners","gold_miners","gold_miner_relative",
       "gold_miner_prior5","gold_miner_rth","gold_miner_15m")
ASSETS=("GDX","GDXJ","best_producer")
TRAIN_END="2026-09-01"
FRICTIONS=(0.15,0.30,0.60)

def completed_change(bars,decision,minutes):
    here=old.at(bars,decision)
    before=old.at(bars,decision-timedelta(minutes=minutes))
    if not here or not before or before[0]<=0:return None
    return 100*(here[0]/before[0]-1)

def miner_signal(f,rule,clock,sessions,day):
    g=f.get("GLD"); m=f.get("GDX")
    if rule=="unconditional":return True
    gold=bool(g and g["pct"]>=.25)
    miners=bool(m and m["pct"]>=.40 and
                sum(bool(f.get(s) and f[s]["pct"]>=.40) for s in ("NEM","AEM","KGC"))>=2)
    if rule=="gold_only":return gold
    if rule=="miners":return miners
    if rule=="gold_miners":return gold and miners
    if not (gold and miners):return False
    if rule=="gold_miner_relative":return m["pct"]-g["pct"]>=.2
    if rule=="gold_miner_prior5":return g["prior5"]>=0 and m["prior5"]>=0
    if clock=="09:25":return False # DO NOT use regular-open data before the open.
    decision=datetime.fromisoformat(day).replace(tzinfo=old.ET,hour=10,minute=0)
    if rule=="gold_miner_rth":
        op=old.open_mark(sessions.get(("GDX",day),{}),time(9,30))
        return bool(op and m["price"]/op-1>=.0015)
    if rule=="gold_miner_15m":
        gl=completed_change(sessions.get(("GLD",day),{}),decision,15)
        gd=completed_change(sessions.get(("GDX",day),{}),decision,15)
        return gl is not None and gd is not None and gl>=0 and gd>=.20
    raise ValueError(rule)

def choose_asset(f,name):
    if name!="best_producer":return name
    cand=[s for s in ("NEM","AEM","KGC") if s in f]
    return max(cand,key=lambda s:(f[s]["pct"],s)) if cand else None

def net_returns(row):
    return {str(int(cost*100))+"bp":round(row["gross_to14"]-cost,5) for cost in FRICTIONS}

def report(rows):
    days=len({x["day"] for x in rows})
    if not rows:return {"trades":0,"days":0}
    wins=sum(x["net30"]>0 for x in rows)
    eq=1;peak=1;worst=0
    for x in sorted(rows,key=lambda r:(r["day"],r["symbol"])):
        eq *= max(0,1+x["net30"]/100)
        peak=max(peak,eq)
        worst=max(worst,1-eq/peak)
    return {"trades":len(rows),"days":days,"winners30":wins,
      "win_frac30":round(wins/len(rows),4),
      "wilson95_lower":round(old.wilson(wins,len(rows)),4),
      "mean_net15":round(mean(x["gross_to14"]-.15 for x in rows),4),
      "mean_net30":round(mean(x["net30"] for x in rows),4),
      "mean_net60":round(mean(x["gross_to14"]-.60 for x in rows),4),
      "mean_to_next_open30":round(mean(x["gross_next_open"]-.30 for x in rows if x["gross_next_open"] is not None),4) if any(x["gross_next_open"] is not None for x in rows) else None,
      "max_compounded_drawdown_pct":round(worst*100,3),
      "gdx_major_up_hits":sum(x["gdx_major_up"] for x in rows),
      "gdx_nonmajor_signals":sum(not x["gdx_major_up"] for x in rows),
      "earliest_qualifying_major_up":min((x["decision_ts"] for x in rows if x["gdx_major_up"]),default=None)}

def build():
    sessions,source=old.load_data()
    complete=old.complete_sessions(sessions)
    prev,prior5,next_open=old.historical_context(complete)
    days=sorted({d for sym,d in complete if sym=="GDX" and ("GDX",d) in prior5 and ("GLD",d) in prior5})
    events={}
    audits=[]
    for day in days:
        gdx=complete[("GDX",day)]
        p=prev[("GDX",day)]
        om=old.outcome(p,gdx["open"],gdx["close"])
        audits.append({"day":day,"gdx_major_up":om["major_up"],"gdx_major_down":om["major_down"],
                       "gdx_close_pct":round(om["close_pct"],4)})
        for clock,enter_clock in CLOCKS.items():
            f=old.features(day,clock,sessions,prev,prior5)
            for rule in RULES:
                if not miner_signal(f,rule,clock,sessions,day):continue
                for asset in ASSETS:
                    sym=choose_asset(f,asset)
                    if sym is None or (sym,day) not in complete or (sym,day) not in prior5:continue
                    decision=datetime.fromisoformat(day).replace(tzinfo=old.ET,
                         hour=int(clock[:2]),minute=int(clock[-2:]))
                    entry=old.open_mark(sessions.get((sym,day),{}),enter_clock)
                    exit14=old.open_mark(sessions.get((sym,day),{}),time(14,0))
                    if not entry or not exit14:continue
                    # All observations at or before decision; outcomes not part of candidate selection.
                    history=f.get(sym)
                    if history is None:continue
                    k=f"{clock}_{rule}_{asset}"
                    nextp=next_open.get((sym,day))
                    result={"day":day,"symbol":sym,"policy":k,"decision_ts":day+"T"+clock+":00-05:00", # display local ET only using day/clock; ISO DST offset corrected below
                      "entry_ts":day+"T"+enter_clock.isoformat(),"entry":round(entry,4),
                      "gross_to14":(exit14/entry-1)*100,
                      "net30":(exit14/entry-1)*100-.30,
                      "gross_next_open":(nextp/entry-1)*100 if nextp else None,
                      "gdx_major_up":om["major_up"],"gdx_major_down":om["major_down"],
                      "gdx_close_pct":om["close_pct"],"gold_asof_pct":f.get("GLD",{}).get("pct"),
                      "gdx_asof_pct":f.get("GDX",{}).get("pct"),"asset_asof_pct":history["pct"]}
                    result["decision_ts"]=decision.isoformat()
                    events.setdefault(k,[]).append(result)
    return events,audits,source

def evaluate(events,audits):
    totals={}
    for k,rows in events.items():
        totals[k]={"earlier":report([r for r in rows if r["day"]<TRAIN_END]),
                   "later":report([r for r in rows if r["day"]>=TRAIN_END]),
                   "all":report(rows)}
    # Select according to ONLY earlier data and adequate earlier independent sessions.
    qualifying=[(k,v["earlier"]["mean_net30"],v["earlier"]["win_frac30"])
                for k,v in totals.items()
                if v["earlier"]["days"]>=30]
    best=sorted(qualifying,key=lambda x:(-x[1],-x[2],x[0]))[:1]
    shadow=best[0][0] if best else None
    # Cash/no-trade is a genuine candidate. A profitable earlier mean is NECESSARY,
    # but not sufficient: demand the owner's >=80% TRAIN after-cost hit-rate goal.
    picked=(shadow if shadow and totals[shadow]["earlier"]["mean_net30"]>0
            and totals[shadow]["earlier"]["win_frac30"]>=.8
            and totals[shadow]["earlier"]["wilson95_lower"]>=.60 else None)
    # Train-only gate: fixed selection, no adaptation after looking at later outcomes.
    earlier_days=[d for d in audits if d["day"]<TRAIN_END]
    later_days=[d for d in audits if d["day"]>=TRAIN_END]
    later_winners=[d["day"] for d in later_days if d["gdx_major_up"]]
    later_hits=set(r["day"] for r in events.get(picked,[]) if r["day"]>=TRAIN_END and r["gdx_major_up"]) if picked else set()
    return {"policy_metrics":totals,"selection_by_earlier_only":picked,
      "earlier_best_rejected_shadow":shadow if picked is None else None,
      "earlier_best_shadow_metrics":totals[shadow] if shadow else None,
      "selected_later_metrics":totals[picked]["later"] if picked else None,
      "selected_later_gdx_major_up_hit_days":len(later_hits),
      "later_gdx_major_up_days":len(later_winners),
      "later_gdx_major_up_miss_days":sorted(set(later_winners)-later_hits),
      "earlier_gdx_major_up_days":sum(x["gdx_major_up"] for x in earlier_days),
      "earlier_gdx_major_down_days":sum(x["gdx_major_down"] for x in earlier_days),
      "later_gdx_major_down_days":sum(x["gdx_major_down"] for x in later_days),
      "trade_day_independence":"each policy at most ONE asset per eligible trading day",
      "asof_safety":"5-minute bars start timestamps; all price features only from bars completed <= decision",
      "warning":"This is price-mark research, NOT NBBO executable quotes or PAPER fills; 80% precision goal not demonstrated."}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True);arg=ap.parse_args()
    events,audits,source=build()
    result=evaluate(events,audits)
    result["sources"]=source
    result["audit_days"]=len(audits)
    result["candidates_configured"]=len(CLOCKS)*len(RULES)*len(ASSETS)
    result["candidates_with_trades"]=len(events)
    Path(arg.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    Path(arg.output+".events.json").write_text(json.dumps(events,indent=0))
    Path(arg.output+".audit.json").write_text(json.dumps(audits,indent=0))
    print(json.dumps({"selected":result["selection_by_earlier_only"],"later":result["selected_later_metrics"],
          "major_up_hits":result["selected_later_gdx_major_up_hit_days"],
          "major_up_total":result["later_gdx_major_up_days"],
          "tested":result["candidates_with_trades"]},indent=2))
if __name__=="__main__":main()
