#!/usr/bin/env python3
"""Same-event matched trailing stop sensitivity and TRAIN-only parameter pick.
Every six-stop comparison uses exactly the same historical event & minute path.
READ ONLY, NO BROKER ACTIONS, NOT REAL FILLS.
"""
from pathlib import Path
import csv,gzip,json,math,collections,importlib.util
R=Path("/var/lib/securityprepper-two-year-intraday-research")
p=Path("/tmp/srm_2yr_trailing_sim_20261121.py")
spec=importlib.util.spec_from_file_location("stopbase",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TRAILS=(.5,.75,1.0,1.5,2.0,2.5)
aggregate=collections.defaultdict(m.stats0)
per_symbol=collections.defaultdict(m.stats0)
per_rule=collections.defaultdict(m.stats0)
seen=collections.Counter()
matched=0;matched_cases=0
unmatched=0;duplicate=0;control_mismatch=0
key0=None;rows=[]
def finalize():
 global matched,unmatched,matched_cases,duplicate,control_mismatch
 if not rows:return
 bytrail={}
 for r in rows:
  t=float(r["trailing_stop_pct"])
  if t in bytrail:duplicate+=1;return
  bytrail[t]=r
 if len(bytrail)!=len(TRAILS) or set(bytrail)!=set(TRAILS):
  unmatched+=1;return
 refs=[r["control_hold"] for r in bytrail.values()]
 if max(refs)-min(refs)>.000001: control_mismatch+=1;return
 matched+=1
 for t in TRAILS:
  r=bytrail[t]
  side=r["side"];period=r["split"];sym=r["symbol"];rule=r["rule"]
  mm={"net":r["net"],"control_hold":r["control_hold"],"exit_reason":r["exit_reason"],"duration_minutes":r["duration_minutes"]}
  m.observe(aggregate[(period,side,t)],mm)
  m.observe(per_symbol[(sym,rule,side,t,period)],mm)
  m.observe(per_rule[(rule,side,t,period)],mm)
  matched_cases+=1
with gzip.open(R/"trailing_stop_simulated_research_receipts.jsonl.gz","rt") as src:
 for i,line in enumerate(src,1):
  r=json.loads(line)
  k=(r["symbol"],r["date"],r["rule"],r["side"],r["signal_minute"])
  if key0 is None:key0=k
  if k!=key0:
   finalize();rows=[];key0=k
  rows.append(r)
  if i%250000==0:print("SCAN",i,"matched",matched,"unmatched",unmatched,flush=True)
 finalize()
rows=[]
out=[]
for (period,side,t),v in sorted(aggregate.items()):
 x=m.snapshot(v);out.append({"period":period,"side":side,"stop_pct":t,**x})
with (R/"MATCHED_STOP_SENSITIVITY_BY_PERIOD_AND_SIDE.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
rule_rows=[]
for (rule,side,t,period),v in sorted(per_rule.items()):
 x=m.snapshot(v);rule_rows.append({"rule":rule,"side":side,"stop_pct":t,"period":period,**x})
with (R/"MATCHED_STOP_EACH_RULE_OOS.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rule_rows[0]));w.writeheader();w.writerows(rule_rows)
picks=[]
symbols=sorted(set(k[0] for k in per_symbol))
for s in symbols:
 ranked=[]
 for (sym,rule,side,t,period),v in per_symbol.items():
  if sym!=s or period!="TRAIN" or v["n"]<25:continue
  x=m.snapshot(v)
  penalty=(x["std_pct"] or 100)/(v["n"]**.5)
  score=x["net_proxy_avg_pct"]-0.8*penalty-0.15*max(0,-x["worst_net_pct"])
  ranked.append((score,rule,side,t))
 if not ranked:
  picks.append({"symbol":s,"decision":"NO_COMMON_COHORT_TRAIN_SUPPORT","approved_order":False});continue
 score,rule,side,t=max(ranked)
 tr=m.snapshot(per_symbol[(s,rule,side,t,"TRAIN")])
 va=m.snapshot(per_symbol.get((s,rule,side,t,"VALIDATE"),m.stats0()))
 ho=m.snapshot(per_symbol.get((s,rule,side,t,"HOLDOUT"),m.stats0()))
 good=(va["n"]>=15 and ho["n"]>=20 and
       tr["net_proxy_avg_pct"]>0 and va["net_proxy_avg_pct"]>0 and ho["net_proxy_avg_pct"]>0 and
       va["win_pct"]>=55 and ho["win_pct"]>=55 and
       va["net_proxy_avg_pct"]>va["hold_without_stop_avg_pct"] and
       ho["net_proxy_avg_pct"]>ho["hold_without_stop_avg_pct"])
 picks.append({"symbol":s,"rule":rule,"side":side,"train_chosen_stop_pct":t,
               "train":tr,"validation":va,"holdout":ho,"three_period_positive_and_better_than_hold":good,
               "decision":"RESEARCH_ONLY_NEEDS_REAL_BROKER_SPREAD_AND_NEWS" if good else "NO_VALIDATED_FORWARD_EDGE","approved_order":False})
with (R/"MATCHED_STOP_PER_SYMBOL_TRAIN_SELECTED.csv").open("w",newline="") as f:
 cols=["symbol","chosen_rule","side","train_chosen_stop_pct","train_n","train_net_proxy","validate_n","validate_net_proxy","holdout_n","holdout_net_proxy","holdout_win_pct","holdout_vs_no_trail_net_proxy","validated_proxy","decision"]
 w=csv.writer(f);w.writerow(cols)
 for x in picks:
  if "train" not in x:w.writerow([x["symbol"],"","","","","","","","","","","","","NO_COMMON_COHORT_TRAIN_SUPPORT"]);continue
  tr,va,ho=x["train"],x["validation"],x["holdout"]
  w.writerow([x["symbol"],x["rule"],x["side"],x["train_chosen_stop_pct"],tr["n"],tr["net_proxy_avg_pct"],va["n"],va["net_proxy_avg_pct"],ho["n"],ho["net_proxy_avg_pct"],ho["win_pct"],ho["hold_without_stop_avg_pct"],x["three_period_positive_and_better_than_hold"],x["decision"]])
summary={"schema":1,"method":"Only 6-stop fully observed common event groups; strict same-day, same-symbol, same-rule, same-side and same-entry minute. No broker fills; assumed .10% per side modeled execution costs.","source_scenarios":1055129,"matched_event_paths":matched,"matched_stop_cases":matched_cases,"unmatched_event_paths":unmatched,"duplicate_groups":duplicate,"inconsistent_hold_baselines":control_mismatch,"matched_symbol_count":len(symbols),"training_selected_symbols":sum('train' in x for x in picks),"independent_positive_aftercost_proxy_and_vs_hold":sum(x.get("three_period_positive_and_better_than_hold",False) for x in picks),
  "aggregates":out,"selected_picks":picks}
(R/"MATCHED_STOP_VALIDATION_SUMMARY.json").write_text(json.dumps(summary,indent=2))
print("MATCHED_SUMMARY",json.dumps({k:v for k,v in summary.items() if k not in ("aggregates","selected_picks")},sort_keys=True),flush=True)
print("MATCHED_HOLDOUT",json.dumps([x for x in out if x["period"]=="HOLDOUT"],sort_keys=True),flush=True)
print("MATCHED_VALIDATED",[(x["symbol"],x["rule"],x["side"],x["train_chosen_stop_pct"],x["holdout"]) for x in picks if x.get("three_period_positive_and_better_than_hold")],flush=True)