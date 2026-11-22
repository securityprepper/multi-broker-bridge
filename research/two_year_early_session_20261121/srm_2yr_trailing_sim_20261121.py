#!/usr/bin/env python3
"""RESEARCH ONLY: next-completed-minute-entry, completed-bar-confirmed
trailing-stop sensitivity vs same-event hard-flat control.
Do not use simulated trade prices as actual Alpaca executable fills.
No broker POST/GET or production changes.
"""
from pathlib import Path
import csv,gzip,json,math,collections,statistics,datetime as dt
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago");UTC=dt.timezone.utc;EPOCH=dt.date(1970,1,1)
OLD=Path("/var/lib/securityprepper-two-year-sector-backtest/sip1m")
NEW=Path("/var/lib/securityprepper-two-year-early-session-research")
ROOT=Path("/var/lib/securityprepper-two-year-intraday-research")
CAND=ROOT/"first_120_minute_rule_events.jsonl.gz"
TRAILS=(0.005,0.0075,0.01,0.015,0.02,0.025)
COST_PER_SIDE=0.001 # proxy: 10bp EACH side, not independently verified quote spread.
def date_for(minute):
 return EPOCH+dt.timedelta(days=minute//1440)
def byday(sym):
 original=OLD/f"{sym}.csv.gz"
 if not original.is_file():original=NEW/"SIP_RTH_NEW"/f"{sym}.csv.gz"
 current=NEW/"SIP_RTH_NOV20"/f"{sym}.csv.gz"
 for p in (original,current):
  if not p.is_file():continue
  d=None;bars={}
  with gzip.open(p,"rt",newline="") as f:
   for x in csv.reader(f):
    try:
     minute=int(x[0]);stamp=date_for(minute)
     if d!=stamp:
      if d is not None:yield str(d),bars
      bars={};d=stamp
     marketopen=int(dt.datetime.combine(stamp,dt.time(8,30),CT).timestamp()//60)
     m=minute-marketopen
     if 0<=m<390:
      b=tuple(float(v) for v in x[1:6])
      if all(math.isfinite(v) for v in b) and min(b[:4])>=5 and b[4]>0:
       bars[m]=b
    except (ValueError,IndexError):continue
  if d is not None:yield str(d),bars
def simulate(event,bars,trail):
 sign=event["dir"];entry_index=event["entry_offset"];end=event["flat_offset"]
 if entry_index>=end or end<100 or entry_index not in bars:return None
 o0=bars[entry_index][0]
 if not (5<=o0<=2000):return None
 if int(2000/o0)<1:return None
 # Use latest real bar at or before declared hard flat, not after it.
 last=next((i for i in range(end-1,end-4,-1) if i in bars),None)
 if last is None or last<=entry_index:return None
 entry=o0
 anchor=entry
 stop=anchor*(1-trail) if sign==1 else anchor*(1+trail) if trail else None
 exit_price=bars[last][3];exit_index=last;reason="FORCED_FLAT"
 highest=entry;lowest=entry
 for i in range(entry_index,last+1):
  if i not in bars: # No executable bar => exit data uncertain.
   return None
  o,h,l,c,v=bars[i]
  if trail:
   if sign==1 and l<=stop:
    exit_price=min(o,stop);exit_index=i;reason="TRAIL_STOP_CONSERVATIVE";break
   if sign==-1 and h>=stop:
    exit_price=max(o,stop);exit_index=i;reason="TRAIL_STOP_CONSERVATIVE";break
  highest=max(highest,h);lowest=min(lowest,l)
  if trail:
   if sign==1:stop=max(stop,highest*(1-trail))
   else:stop=min(stop,lowest*(1+trail))
 if sign==1:
  entry_proxy=entry*(1+COST_PER_SIDE)
  exit_proxy=exit_price*(1-COST_PER_SIDE)
  net=(exit_proxy/entry_proxy-1)*100
  hold_control=(bars[last][3]*(1-COST_PER_SIDE)/entry_proxy-1)*100
 else:
  entry_proxy=entry*(1-COST_PER_SIDE)
  exit_proxy=exit_price*(1+COST_PER_SIDE)
  net=(entry_proxy-exit_proxy)/entry_proxy*100
  hold_control=(entry_proxy-bars[last][3]*(1+COST_PER_SIDE))/entry_proxy*100
 gross=sign*(exit_price/entry-1)*100
 return {"net":net,"gross":gross,"control_hold":hold_control,
         "exit_offset":exit_index,"exit_reason":reason,
         "duration_minutes":exit_index-entry_index,
         "entry_raw":entry,"exit_raw":exit_price,"proxy_cost_pct":200*COST_PER_SIDE}
def stats0():
 return {"n":0,"win":0,"net_sum":0.0,"net_sum2":0.0,"hold_sum":0.0,"stop_exits":0,"duration_sum":0,"negative_tail":0,"loss_2pct":0,"worst_net":float("inf")}
def observe(s,r):
 v=r["net"];s["n"]+=1;s["win"]+=int(v>0);s["net_sum"]+=v;s["net_sum2"]+=v*v;s["hold_sum"]+=r["control_hold"]
 s["stop_exits"]+=int(r["exit_reason"]!="FORCED_FLAT");s["duration_sum"]+=r["duration_minutes"]
 s["loss_2pct"]+=int(v<=-2.0);s["worst_net"]=min(s["worst_net"],v)
def snapshot(s):
 n=s["n"]; avg=s["net_sum"]/n if n else None
 std=math.sqrt(max(0,(s["net_sum2"]-s["net_sum"]**2/n)/(n-1))) if n>1 else None
 return {"n":n,"net_proxy_avg_pct":round(avg,4) if avg is not None else None,
 "win_pct":round(s["win"]/n*100,2) if n else None,
 "std_pct":round(std,4) if std is not None else None,
 "hold_without_stop_avg_pct":round(s["hold_sum"]/n,4) if n else None,
 "stop_exit_pct":round(s["stop_exits"]/n*100,2) if n else None,
 "mean_duration_min":round(s["duration_sum"]/n,2) if n else None,
 "loss_gt2_pct":round(s["loss_2pct"]/n*100,2) if n else None,
 "worst_net_pct":round(s["worst_net"],4) if n else None}
def main():
 candidates=collections.defaultdict(lambda:collections.defaultdict(list))
 events=0
 with gzip.open(CAND,"rt") as f:
  for line in f:
   ev=json.loads(line);candidates[ev["symbol"]][ev["date"]].append(ev);events+=1
 print("SIGNAL_EVENTS_LOADED",events,"SYMBOLS",len(candidates),flush=True)
 stats=collections.defaultdict(stats0)
 out=ROOT/"trailing_stop_simulated_research_receipts.jsonl.gz"
 total=0;skipped=collections.Counter()
 with gzip.open(out,"wt",compresslevel=3) as f:
  for k,sym in enumerate(sorted(candidates),1):
   found=set()
   for d,bars in byday(sym):
    es=candidates[sym].get(d)
    if not es:continue
    found.add(d)
    for ev in es:
     for t in TRAILS:
      result=simulate(ev,bars,t)
      if result is None:
       skipped["INVALID_ENTRY_OR_BAR_GAP"]+=1;continue
      key=(sym,ev["rule"],ev["side"],t,ev["split"])
      observe(stats[key],result)
      if result["net"]<-50:raise RuntimeError("UNREALISTIC_NET_FILL")
      record={"date":d,"symbol":sym,"rule":ev["rule"],"side":ev["side"],
        "trailing_stop_pct":round(t*100,3),"split":ev["split"],
        "signal_minute":ev["signal_minute"],"first_entry_minute":ev["entry_offset"],
        "day_class":ev["day_class"],"broker_filled":False,"source":"SIP split-adjusted 1m OHLC completed bars",
        **{k:round(v,4) if isinstance(v,float) else v for k,v in result.items()}}
      f.write(json.dumps(record,separators=(",",":"))+"\n")
      total+=1
   if k%30==0:print("PROGRESS",k,"/",len(candidates),"hypothetical_stop_cases",total,flush=True)
   for d in set(candidates[sym])-found:
    skipped["NO_RTH_BARS:"+sym]+=1
 # Freeze best rule+side+trailing based only on the earliest chronological training sessions.
 keys=collections.defaultdict(list)
 for (sym,rule,side,t,part),s in stats.items():
  if part=="TRAIN":keys[sym].append((rule,side,t,s))
 picks=[];eligible=0
 for sym,choices in sorted(keys.items()):
  ranked=[]
  for rule,side,t,ss in choices:
   tr=snapshot(ss)
   if tr["n"]<25:continue
   # Small-sample penalized train metric, cost proxy assumed.
   score=tr["net_proxy_avg_pct"]-.8*tr["std_pct"]/max(1,tr["n"]**.5)-.15*max(0,-tr["worst_net_pct"])
   ranked.append((score,rule,side,t))
  if not ranked:
   picks.append({"symbol":sym,"candidate_status":"INSUFFICIENT_TRAINING_SIGNALS","accepted_order":False})
   continue
  eligible+=1
  _,rule,side,t=max(ranked)
  train=snapshot(stats[(sym,rule,side,t,"TRAIN")])
  val=snapshot(stats.get((sym,rule,side,t,"VALIDATE"),stats0()))
  hold=snapshot(stats.get((sym,rule,side,t,"HOLDOUT"),stats0()))
  valid_edge=(val["n"]>=15 and hold["n"]>=20 and val["net_proxy_avg_pct"]>0 and hold["net_proxy_avg_pct"]>0
        and val["win_pct"]>=55 and hold["win_pct"]>=55 and
        val["hold_without_stop_avg_pct"]<val["net_proxy_avg_pct"] and
        hold["hold_without_stop_avg_pct"]<hold["net_proxy_avg_pct"])
  picks.append({"symbol":sym,"side":side,"rule":rule,"training_selected_trailing_stop_pct":round(t*100,3),
       "train":train,"validation":val,"holdout":hold,
       "independent_proxy_positive_both":valid_edge,
       "candidate_status":"SIMULATED_PAPER_RESEARCH_NEEDS_REAL_QUOTE_FEES_AND_NEWS" if valid_edge else "NO_VALIDATED_AFTERCOST_EDGE",
       "accepted_order":False,"experimental_approval":False})
 report={"schema":1,"data":"Alpaca historical SIP 1m split-adjusted OHLC; source-time causal signals, nontraded",
 "model":"Next minute open as entry proxy, two-sided 10bp each-side total 20bp trading-cost proxy, trailing stop from prior COMPLETED one-minute price high/low, stop-first before trail update, gap adverse open, 13:40 CT hard flat (11:40 on exchange early-close), max notional $2000 whole shares","not_real_fills":True,"spread_not_verified":True,"news_not_cleared":True,"borrowability_unverified":True,
 "stop_grid_pct":[round(x*100,3) for x in TRAILS],
 "train":"2024-11-20 through 2025-11-19","validation":"2025-11-20 through 2026-05-19","holdout":"2026-05-20 through 2026-11-20",
 "simulated_cases":total,"signal_events":events,"candidate_symbols":len(candidates),
 "selected_with_train_n25":eligible,"selected_picks":picks,"exclusions":dict(skipped),"all_results":{}}
 # The full rule/side/stop grid keeps the denominators; nothing is selected on the holdout.
 for (sym,rule,side,t,part),v in stats.items():
  key=f"{sym}|{rule}|{side}|{t*100:.3f}|{part}"
  report["all_results"][key]=snapshot(v)
 (ROOT/"trailing_stops_train_validate_untouched_holdout.json").write_text(json.dumps(report,indent=2,sort_keys=True))
 with (ROOT/"trailing_stops_per_symbol_training_selected.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["symbol","side","rule","training_stop_pct","train_n","train_mean_net_proxy_pct","val_n","val_mean_net_proxy_pct","holdout_n","holdout_mean_net_proxy_pct","holdout_win_pct","holdout_vs_hold_to_flat_mean_pct","status"])
  for e in picks:
   if "train" not in e:
    w.writerow([e["symbol"],"","","","","","","","","","","",e["candidate_status"]]);continue
   tr,va,ho=e["train"],e["validation"],e["holdout"]
   w.writerow([e["symbol"],e["side"],e["rule"],e["training_selected_trailing_stop_pct"],tr["n"],tr["net_proxy_avg_pct"],va["n"],va["net_proxy_avg_pct"],ho["n"],ho["net_proxy_avg_pct"],ho["win_pct"],ho["hold_without_stop_avg_pct"],e["candidate_status"]])
 print("FINISHED",json.dumps({"simulated_cases":total,"events":events,"eligible_training_symbols":eligible,"independent_proxy_positive_both":sum(x.get("independent_proxy_positive_both",False) for x in picks),"exclusion_reasons_top":collections.Counter({k:v for k,v in skipped.items() if not k.startswith("NO_RTH_BARS:")}).most_common(6)}),flush=True)
 print("PICKS_INDEPENDENT",[(e["symbol"],e["side"],e["rule"],e["training_selected_trailing_stop_pct"],e["holdout"]) for e in picks if e.get("independent_proxy_positive_both")][:18],flush=True)
if __name__=="__main__":main()