#!/usr/bin/env python3
"""Research-only historical overnight predictive patterns, with a fixed
8:25 am Chicago as-of price snapshot and actual RTH open-to-13:40 future.
Data Alpaca SIP/BOATS split-adjusted 1m TRADE CLOSES, NOT executable fills.
Hypothesis exploration already saw later-period historical summaries:
do not characterize test dates as a pristine prospective holdout.
"""
from pathlib import Path
import bisect,csv,collections,datetime as dt,gzip,importlib.util,json,math
ROOT=Path("/var/lib/securityprepper-two-year-intraday-research")
REFERENCE=Path("/tmp/srm_2yr_premarket_510m_20261121.py")
spec=importlib.util.spec_from_file_location("premarket",REFERENCE)
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
GATE=Path("/var/cache/securityprepper-holiday/task-gate.json")
def stamp(x):return dt.datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(dt.timezone.utc)
def gate():
 j=json.loads(GATE.read_text());n=dt.datetime.now(dt.timezone.utc)
 if not(j.get("schema_version")==1 and j.get("status_valid") is True and j.get("calendar_coverage_ok") is True and j.get("timezone")=="America/Chicago" and j.get("paused") is False and stamp(j["published_at"])<=n<stamp(j["valid_until"]) and n<stamp(j["next_check_at"])):
  raise RuntimeError("HOLIDAY_GATE_INVALID_OR_PAUSED")
 return j.get("calendar_revision")
def ratio(a,b):return (b/a-1)*100 if a and b and a>0 else None
def snap(mp,target,max_delay=3):
 if not mp:return None
 times=sorted(mp)
 i=bisect.bisect_left(times,target)-1
 if i<0:return None
 t=times[i]
 if target-(t+1)>max_delay:return None
 return {"minute_start":t,"price":mp[t][1],"volume":mp[t][2],"source":mp[t][0]}
def stats():
 return {"n":0,"days":set(),"win_aftercost":0,"positive":0,"sum_signed":0.,"ssq":0.,"out_up":0,"out_down":0,"out_mixed":0,"spy_beat":0,"spy_n":0,"sector_beat":0,"sector_n":0}
def add(o,r):
 z=r["signed_RTH_open_to_flat_pct"];o["n"]+=1;o["days"].add(r["date"]);o["sum_signed"]+=z;o["ssq"]+=z*z
 o["win_aftercost"]+=int(z>.25);o["positive"]+=int(z>0)
 o["out_up"]+=int(z>=.75);o["out_down"]+=int(z<=-.75);o["out_mixed"]+=int(-.75<z<.75)
 if r["SPY_signed_open_to_flat_pct"] is not None:
  o["spy_n"]+=1;o["spy_beat"]+=int(z>r["SPY_signed_open_to_flat_pct"])
 if r["ETF_signed_open_to_flat_pct"] is not None:
  o["sector_n"]+=1;o["sector_beat"]+=int(z>r["ETF_signed_open_to_flat_pct"])
def summ(o):
 n=o["n"]
 if not n:return {"n":0}
 mu=o["sum_signed"]/n
 sd=math.sqrt(max(0,(o["ssq"]-o["sum_signed"]**2/n)/(n-1))) if n>1 else None
 return {"n":n,"distinct_days":len(o["days"]),"future_mean_gross_pct":round(mu,4),"future_mean_minus25bp_proxy_pct":round(mu-.25,4),
  "future_positive_after25bp_pct":round(100*o["win_aftercost"]/n,2),
  "forward_up_over075_pct":round(100*o["out_up"]/n,2),"forward_down_below075_pct":round(100*o["out_down"]/n,2),"forward_mixed_pct":round(100*o["out_mixed"]/n,2),
  "beats_SPY_future_pct":round(100*o["spy_beat"]/o["spy_n"],2) if o["spy_n"] else None,
  "beats_sector_future_pct":round(100*o["sector_beat"]/o["sector_n"],2) if o["sector_n"] else None,
  "naive_sd_pct":round(sd,4) if sd is not None else None}
def main():
 gate();rth=p.rth();etfs=p.ETFS
 all_etf={}
 for i,s in enumerate(p.REF):
  all_etf[s]={d:mp for d,mp in p.iter_day(s)}
 print("NIGHT_REFERENCE_LOADED",len(all_etf),"RTH_ROWS",len(rth),flush=True)
 gate()
 byrule=collections.defaultdict(stats);bysector=collections.defaultdict(stats);bysymbol=collections.defaultdict(stats);time_stats=collections.defaultdict(stats)
 names=["OVERNIGHT_STOCK_SECTOR_SPY_CONTINUE","EXTREME_GAP_FADES_IN_LAST30",
        "PREOPEN_SECTOR_LEADS_LAGGING_STOCK","OVERNIGHT_DIVERGENCE_FROM_SECTOR",
        "LATE_PREOPEN_ACCELERATION","MIDNIGHT_OPENING_DRIFT_PERSISTS"]
 allrows=[];eligible=collections.Counter();timestamp_points=(360,420,480,500,505)
 for i,sym in enumerate(p.CFG["symbols"],1):
  if sym in p.REF:continue
  g=p.SECTOR.get(sym);sector=etfs.get(g)
  if not g or not sector:continue
  for d,mp in p.iter_day(sym):
   me=rth.get((sym,d));sp=rth.get(("SPY",d));et=rth.get((sector,d))
   spy=all_etf.get("SPY",{}).get(d);sec=all_etf.get(sector,{}).get(d)
   if not(me and sp and et and spy and sec):continue
   prev=me.get("previous_rth_close");s_prev=sp.get("previous_rth_close");e_prev=et.get("previous_rth_close")
   if not(prev and s_prev and e_prev):continue
   prev=float(prev);s_prev=float(s_prev);e_prev=float(e_prev)
   start=float(me["split_adj_rth_open"]);end=float(me["hard_flat_price"]) if me.get("hard_flat_price") else None
   if not end or start<5 or end<5:continue
   mstart=float(sp["split_adj_rth_open"]);mend=float(sp["hard_flat_price"]) if sp.get("hard_flat_price") else None
   estart=float(et["split_adj_rth_open"]);eend=float(et["hard_flat_price"]) if et.get("hard_flat_price") else None
   if not (mend and eend):continue
   eligible["valid_symbol_days"]+=1
   first=snap(mp,11,10);s_first=snap(spy,11,10);e_first=snap(sec,11,10)
   chosen=set()
   for minute in timestamp_points:
    z=snap(mp,minute);sz=snap(spy,minute);ez=snap(sec,minute)
    if not(z and sz and ez):continue
    if min(z["price"],sz["price"],ez["price"])<5:continue
    z30=snap(mp,minute-30,4);z15=snap(mp,minute-15,4);e30=snap(sec,minute-30,4)
    gap=ratio(prev,z["price"]);market=ratio(s_prev,sz["price"]);etf=ratio(e_prev,ez["price"])
    recent30=ratio(z30["price"],z["price"]) if z30 else None
    recent15=ratio(z15["price"],z["price"]) if z15 else None
    sector30=ratio(e30["price"],ez["price"]) if e30 else None
    if None in (gap,market,etf):continue
    for direction in (1,-1):
     g0=direction*gap;m0=direction*market;e0=direction*etf
     recent30_dir=direction*recent30 if recent30 is not None else None
     recent15_dir=direction*recent15 if recent15 is not None else None
     etf30_dir=direction*sector30 if sector30 is not None else None
     good=[]
     if g0>=1. and m0>=.2 and e0>=.35 and recent30_dir is not None and recent30_dir>=.3 and e0<6:
      good.append("OVERNIGHT_STOCK_SECTOR_SPY_CONTINUE")
     if -g0>=2. and recent30_dir is not None and recent30_dir>=.5 and etf30_dir is not None and etf30_dir>=.15:
      good.append("EXTREME_GAP_FADES_IN_LAST30")
     if -g0>=.5 and m0>=.35 and e0>=.6 and recent15_dir is not None and recent15_dir>=.2:
      good.append("PREOPEN_SECTOR_LEADS_LAGGING_STOCK")
     if -g0>=1.5 and m0>=.25 and e0>=.5:
      good.append("OVERNIGHT_DIVERGENCE_FROM_SECTOR")
     if recent15_dir is not None and recent15_dir>=.5 and m0>=.1 and e0>=.2 and abs(gap)<4:
      good.append("LATE_PREOPEN_ACCELERATION")
     if first and s_first and e_first and all(v["price"]>=5 for v in [first,s_first,e_first]):
      ov=ratio(first["price"],z["price"]); om=ratio(s_first["price"],sz["price"]);oe=ratio(e_first["price"],ez["price"])
      if ov is not None and om is not None and oe is not None and direction*ov>=1. and direction*om>=.25 and direction*oe>=.35:
       good.append("MIDNIGHT_OPENING_DRIFT_PERSISTS")
     for name in good:
      key=(name,direction)
      if key in chosen:continue
      chosen.add(key)
      future=direction*ratio(start,end)
      if future is None:continue
      mr=direction*ratio(mstart,mend);er=direction*ratio(estart,eend)
      x={"symbol":sym,"date":d,"sector":g,"rule":name,"side":"UP" if direction==1 else "DOWN",
         "minute_asof_CT":minute,"asof_CT":f"{minute//60:02d}:{minute%60:02d}",
         "asof_trade_close":z["price"],"asof_trade_minute_start":z["minute_start"],"split":p.split(d),
         "signed_RTH_open_to_flat_pct":future,"SPY_signed_open_to_flat_pct":mr,"ETF_signed_open_to_flat_pct":er,
         "initial_gap_pct":gap,"SPY_prior_close_gap_pct":market,"ETF_prior_close_gap_pct":etf,
         "recent30_pct":recent30,"recent15_pct":recent15,
         "actual_fills":False}
      add(byrule[(name,direction,p.split(d))],x)
      add(bysector[(name,direction,p.split(d),g)],x)
      add(bysymbol[(name,direction,p.split(d),sym)],x)
      add(time_stats[(name,direction,p.split(d),minute)],x)
      allrows.append(x)
   if i%45==0 and minute==505:
    pass
  if i%45==0:
   gate()
   print("PROGRESS_SYMBOL",i,"events",len(allrows),flush=True)
 results=[{"rule":n,"side":"UP" if direction==1 else "DOWN","period":period,**summ(v)}
           for (n,direction,period),v in sorted(byrule.items())]
 sectors=[{"rule":n,"side":"UP" if direction==1 else "DOWN","period":period,"sector":g,**summ(v)}
          for (n,direction,period,g),v in sorted(bysector.items())]
 select=[]
 for sym in sorted(set(k[3] for k in bysymbol)):
  ranked=[]
  for (name,direction,period,s),o in bysymbol.items():
   if s!=sym or period!="TRAIN" or o["n"]<25:continue
   st=summ(o);score=st["future_mean_minus25bp_proxy_pct"]-(st["naive_sd_pct"] or 100)/o["n"]**.5
   ranked.append((score,name,direction))
  if not ranked:continue
  _,name,direction=max(ranked)
  t=summ(bysymbol[(name,direction,"TRAIN",sym)])
  v=summ(bysymbol.get((name,direction,"VALIDATE",sym),stats()))
  h=summ(bysymbol.get((name,direction,"HOLDOUT",sym),stats()))
  passed=(v["n"]>=15 and h["n"]>=20 and
      t["future_mean_minus25bp_proxy_pct"]>0 and v["future_mean_minus25bp_proxy_pct"]>0 and h["future_mean_minus25bp_proxy_pct"]>0 and
      v["future_positive_after25bp_pct"]>=55 and h["future_positive_after25bp_pct"]>=55)
  select.append({"symbol":sym,"rule":name,"side":"UP" if direction==1 else "DOWN","train":t,"validation":v,"holdout":h,"exploratory_date_separated_support":passed,"broker_authorized":False})
 summary={
  "schema":1,"definition":"five predeclared timestamps (06:00,07:00,08:00,08:20,08:25 CT), retrospective actual SIP/BOATS 1m splits; first rule per symbol-day; future open->13:40 flat, NOT overnight gains","caveat":"Hypothesis families developed with knowledge of earlier backtest findings, so later validation is exploratory rather than pristine forward; no real bid-ask fills",
  "eligible_symbol_days":eligible["valid_symbol_days"],"signal_event_count":len(allrows),
  "rule_names":names,"aggregate":results,"sector":sectors,"per_symbol_selected":select,
  "no_broker_orders":True,"cost_proxy_roundtrip_pct":.25}
 (ROOT/"OVERNIGHT_PREOPEN_SUBSEQUENT_DIRECTION_PATTERN_TEST_20261122.json").write_text(json.dumps(summary,indent=2))
 for filename,items in [("OVERNIGHT_PATTERN_AGGREGATE_BY_PERIOD.csv",results),("OVERNIGHT_PATTERN_BY_SECTOR.csv",sectors)]:
  with (ROOT/filename).open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
 print("DONE",json.dumps({"symbol_days":eligible["valid_symbol_days"],"event_count":len(allrows),"pattern_periods":len(results),"symbols_tested":len(select),"exploratory_supported":sum(x["exploratory_date_separated_support"] for x in select)}),flush=True)
 for a in results:
  if a["period"]=="HOLDOUT":
   print("HOLDOUT",a["rule"],a["side"],a["n"],a.get("distinct_days"),a.get("future_mean_minus25bp_proxy_pct"),a.get("future_positive_after25bp_pct"),flush=True)
if __name__=="__main__":main()