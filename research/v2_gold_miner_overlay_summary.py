"""Additional V2 gold/miner: full-day classification and next-open loss avoidance.
Reads SIP 5m inputs & research result; NO broker/order functions.
"""
import argparse,json
from collections import Counter,defaultdict
from datetime import time
from pathlib import Path
from statistics import mean
from research.v2_gold_miner_preopen_lead import *

def compile_report(results_path):
    summary=json.loads(Path(results_path).read_text())
    ev=json.loads(Path(results_path+".events.json").read_text())
    sess,_=load_data()
    full=complete_sessions(sess)
    prev,prior5,nxt=historical_context(full)
    days=sorted({day for _,day in full})
    sector_counts=Counter()
    complete_dates=[]
    baseline=defaultdict(list)
    for day in days:
        if not all((sym,day) in prev and (sym,day) in full for sym in MINERS):
            continue
        moves={s:(full[(s,day)]["close"]/prev[(s,day)]-1)*100 for s in MINERS}
        positive=sum(v>0 for v in moves.values())
        negative=sum(v<0 for v in moves.values())
        sector_counts["positive" if moves["GDX"]>0 and positive>=3 else
                      "negative" if moves["GDX"]<0 and negative>=3 else "mixed"]+=1
        complete_dates.append(day)
        for sym in MINERS:
            if (sym,day) not in prior5:continue
            b=sess[(sym,day)]
            entry=open_mark(b,time(9,35)); exit14=open_mark(b,time(14,0))
            if entry and exit14:
                baseline["earlier" if day<SPLIT else "later"].append(
                    {"day":day,"symbol":sym,"net_pct":(exit14/entry-1)*100-.30})
    bs={}
    for period,items in baseline.items():
        bs[period]={"entries":len(items),"independent_days":len({r["day"] for r in items}),
              "profitable_frac":round(sum(r["net_pct"]>0 for r in items)/len(items),4),
              "mean_net30_pct":round(mean(r["net_pct"] for r in items),4)}
    # For exactly one predeclared rule, report downstream rebound/continued loss into next RTH open.
    detail={}
    signals={(r["symbol"],r["day"]):r for r in ev if r["signal_at"].endswith("09:25:00")
             and r["symbol"] in MINERS}
    for rule in ("gold_only","gold_breadth"):
      for side in ("down","up"):
        for period in ("earlier","later"):
          label=summary["summary"][f"09:25_{rule}_{side}"][period]
          # Events may be duplicated across rules (they have no rule property).
          # Only use canonical side via positive/negative sign of GLD/GDX as-of 09:25.
          entries=[]
          seen=set()
          for day in days:
            if (day<SPLIT)!=(period=="earlier"):continue
            feat=features(day,"09:25",sess,prev,prior5)
            if not qualifies(feat,rule,side):continue
            for sym in MINERS:
              key=(sym,day)
              if key in seen or key not in full or key not in prior5 or key not in nxt:continue
              entry=open_mark(sess[key],time(9,35))
              if not entry:continue
              seen.add(key)
              if side=="down":
                pp=(entry-nxt[key])/prev[key]*100-.30
              else:
                pp=(nxt[key]/entry-1)*100-.30
              mark=outcome(prev[key],full[key]["open"],full[key]["close"])
              entries.append({"day":day,"symbol":sym,"next_open_net":pp,
                              "major":mark["major_down"] if side=="down" else mark["major_up"],
                              "alert_before_minus3":feat.get(sym,{}).get("pct",99)>-3 if side=="down" else None,
                              "already_gap_down":mark["gap_down"]})
          detail[f"{rule}_{side}_{period}"]={
             "n":len(entries),"independent_days":len({e["day"] for e in entries}),
             "next_open_win_frac":round(sum(e["next_open_net"]>0 for e in entries)/len(entries),4) if entries else None,
             "mean_net_next_open_pct":round(mean(e["next_open_net"] for e in entries),4) if entries else None,
             "on_major_days":sum(e["major"] for e in entries),
             "major_warned_before_minus3":sum(e["major"] and e["alert_before_minus3"] for e in entries) if side=="down" else None,
             "major_already_gap_down":sum(e["major"] and e["already_gap_down"] for e in entries) if side=="down" else None,
          }
    # Near misses: no original 09:25 gold+breadth signal on big move days.
    exceptions={}
    for side in ("down","up"):
      failures=[]
      for (sym,day),s in sorted(full.items()):
        if sym not in MINERS or (sym,day) not in prior5 or (sym,day) not in prev:continue
        out=outcome(prev[(sym,day)],s["open"],s["close"])
        major=out["major_down"] if side=="down" else out["major_up"]
        if not major:continue
        f=features(day,"09:25",sess,prev,prior5)
        if qualifies(f,"gold_breadth",side):continue
        sign=1 if side=="up" else -1
        gold_ok="GLD" in f and sign*f["GLD"]["pct"]>=.25
        gdx_ok="GDX" in f and sign*f["GDX"]["pct"]>=.40
        eligible_miners=[x for x in ("NEM","AEM","KGC") if x in f and sign*f[x]["pct"]>=.40]
        failures.append({"day":day,"symbol":sym,"close_pct":round(out["close_pct"],3),
                         "rth_pct":round(out["rth_pct"],3),"gold_met":gold_ok,
                         "gdx_met":gdx_ok,"miner_breadth_met":len(eligible_miners)>=2,
                         "gold_at_0925":round(f["GLD"]["pct"],3) if "GLD" in f else None})
      exceptions[side]={"miss_count":len(failures),
                        "largest_misses":sorted(failures,key=lambda v:(v["close_pct"] if side=="down" else -v["close_pct"]))[:6]}
    return {"sector_def":"GDX sign and majority sign among GDX/GDXJ/NEM/AEM/KGC at RTH close; mixed otherwise",
            "gold_miner_sector":dict(sector_counts),"eligible_sector_sessions":len(complete_dates),
            "unconditional_0935_long_to14":bs,"next_open":detail,"misses":exceptions}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--result",required=True)
    q=p.parse_args()
    output=compile_report(q.result)
    print(json.dumps(output,indent=2))

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]