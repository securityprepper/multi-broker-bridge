#!/usr/bin/env python3
"""Research-only RTH two-year daily classifier and minute-predictability dataset.
All data come from completed split-adjusted SIP 1Min historical files.
No broker orders and no changes to production monitors.
"""
from pathlib import Path
from datetime import datetime,date,time,timezone,timedelta
from zoneinfo import ZoneInfo
import csv,gzip,json,math,statistics,collections,os
CT=ZoneInfo("America/Chicago");UTC=timezone.utc
SRC=Path("/var/lib/securityprepper-two-year-sector-backtest")
MORE=Path("/var/lib/securityprepper-two-year-early-session-research")
DEST=Path("/var/lib/securityprepper-two-year-intraday-research")
DEST.mkdir(parents=True,exist_ok=True,mode=0o700)
START=date(2024,11,20);END=date(2026,11,20)
D0=date(1970,1,1)
SECTOR=json.loads((SRC/"full_membership_frozen.json").read_text())["groups"]
MISSING_META=[]
def rows(sym):
 p=SRC/"sip1m"/f"{sym}.csv.gz"
 if p.exists():
  if not (SRC/"sip1m"/f"{sym}.meta.json").exists() and not (SRC/"sip1m"/f"{sym}.csv.meta.json").exists():MISSING_META.append(sym)
 else:
  p=MORE/"SIP_RTH_NEW"/f"{sym}.csv.gz"
  if not p.exists():return
 today=MORE/"SIP_RTH_NOV20"/f"{sym}.csv.gz"
 for f in (p,today):
  if not f.exists():continue
  with gzip.open(f,"rt",newline="") as g:
   for x in csv.reader(g):
    if len(x)<6:continue
    try:
     minute=int(x[0]);o,h,l,c,v=[float(z) for z in x[1:6]]
     if min(o,h,l,c)<=0 or v<=0 or not all(map(math.isfinite,(o,h,l,c,v))):continue
     yield minute,(o,h,l,c,v)
    except (ValueError,IndexError):continue
def byday(sym):
 current=None;one={}
 cache_day=None;cache_date=None;cache_start=None
 for minute,ohlcv in rows(sym):
  dayidx=minute//1440
  if dayidx!=cache_day:
   cache_day=dayidx; cache_date=D0+timedelta(days=dayidx)
   cache_start=int(datetime.combine(cache_date,time(8,30),CT).timestamp()//60)
  local_day=cache_date
  if local_day<START or local_day>END:continue
  offset=minute-cache_start
  if not 0<=offset<390:continue
  if current is None:current=local_day
  if local_day!=current:
   yield current,one
   one={};current=local_day
  one[offset]=ohlcv
 if current is not None:yield current,one
def spy_sessions():
 result={}
 for d,points in byday("SPY"):
  if min(points,default=500)>2 or len(points)<175:continue
  last=max(points)
  if last<200:continue
  end=210 if last<300 else 390
  if end-last>3:continue
  result[d]=end
 return result
# Exchange-calendar GET-only readback, including authoritative early-close hours.
calendar_file=DEST/"nyse_broker_calendar_20241120_20261121.json"
CALENDAR={date.fromisoformat(x["date"]):x for x in json.loads(calendar_file.read_text())}
OBSERVED_SPY=spy_sessions()
SESSIONS={d:(210 if CALENDAR[d]["close"]=="13:00" else 390)
          for d in CALENDAR if START<=d<=END and d in OBSERVED_SPY}
assert all(CALENDAR[d].get("open")=="09:30" and CALENDAR[d].get("close") in ("13:00","16:00") for d in SESSIONS)
print("SPY_MARKET_DAYS",len(SESSIONS),"EARLY_CLOSES",sum(x==210 for x in SESSIONS.values()),flush=True)
config={"schema":1,"session_source":"split adjusted SIP 1m SPY as exchange-session proxy","label":"UP if O_to_C>=+0.75% and close location>=0.70 of day's range; DOWN if <=-0.75% and close location<=0.30; otherwise MIXED", "day_start":str(START),"day_end":str(END),"train_end":"2025-11-19","validation_end":"2026-05-19","holdout_end":"2026-11-20","confidence":"historical current-membership universe; not point-in-time index membership"}
(DEST/"frozen_method.json").write_text(json.dumps(config,indent=2))
from collections import defaultdict
UNIVERSE=json.loads((MORE/"manifest_config.json").read_text())["symbols"]
OUT=DEST/"daily_classes_20241120_20261120.csv"
PER_MINUTE=DEST/"minute_early_features_20241120_20261120.jsonl.gz"
n_rows=0;summary={};coverage_errors={}
with OUT.open("w",newline="") as out,gzip.open(PER_MINUTE,"wt",compresslevel=3) as mf:
 writer=csv.writer(out)
 writer.writerow(["symbol","date","split_adj_rth_open","split_adj_rth_close","day_change_pct","day_high","day_low","closing_range_location","day_class","session_minutes","actual_bars","quality_coverage_pct","open_to_1m_pct","open_to_5m_pct","open_to_10m_pct","open_to_20m_pct","open_to_30m_pct","open_to_60m_pct","open_to_90m_pct","open_to_120m_pct","previous_rth_close","gap_from_prev_pct","hard_flat_price","hard_flat_minute_offset"])
 for si,sym in enumerate(UNIVERSE,1):
  ct=collections.Counter();valid=0;tot=0;days_bad=0;prev_end_price=None
  for d,mp in byday(sym):
   end=SESSIONS.get(d)
   if not end:continue
   tot+=1
   avail=[i for i in mp if i<end]
   if not avail:days_bad+=1;continue
   first=next((i for i in range(0,3) if i in mp),None)
   last=next((i for i in range(end-1,end-4,-1) if i in mp),None)
   cov=len(avail)/end
   if first is None or last is None or cov<.80:
    days_bad+=1;prev_end_price=None;continue
   a=mp[first][0]; z=mp[last][3]
   hi=max(mp[i][1] for i in avail);lo=min(mp[i][2] for i in avail)
   rp=(z/a-1)*100
   pos=(z-lo)/(hi-lo) if hi>lo else .5
   label="UP" if rp>=.75 and pos>=.7 else ("DOWN" if rp<=-.75 and pos<=.3 else "MIXED")
   flatten_offset=min(310,end-20)
   flatten_end=next((i for i in range(flatten_offset-1,flatten_offset-4,-1) if i in mp),None)
   flatten_price=mp[flatten_end][3] if flatten_end is not None else None
   gap_percent=round((a/prev_end_price-1)*100,4) if prev_end_price and prev_end_price>0 else None
   ct[label]+=1;valid+=1;n_rows+=1
   closes=[mp[i][3] if i in mp else None for i in range(min(120,end))]
   opens=[mp[i][0] if i in mp else None for i in range(min(120,end))]
   highs=[mp[i][1] if i in mp else None for i in range(min(120,end))]
   lows=[mp[i][2] if i in mp else None for i in range(min(120,end))]
   volumes=[mp[i][4] if i in mp else None for i in range(min(120,end))]
   def at(x):
    return round((closes[x-1]/a-1)*100,4) if len(closes)>=x and closes[x-1] is not None else None
   writer.writerow([sym,str(d),round(a,6),round(z,6),round(rp,4),round(hi,6),round(lo,6),round(pos,4),label,end,len(avail),round(cov*100,2)]+[at(x) for x in (1,5,10,20,30,60,90,120)]+[prev_end_price,gap_percent,flatten_price,flatten_offset])
   m={"symbol":sym,"date":str(d),"label":label,"return_pct":round(rp,4),"rth_open":a,"rth_close":z,"rth_high":hi,"rth_low":lo,"close_position":round(pos,4),"session_minutes":end,"bar_coverage":round(cov,4),"prev_rth_close":prev_end_price,"gap_from_prev_pct":gap_percent,"hard_flat_price":flatten_price,"hard_flat_minute_offset":flatten_offset,"minute_open":opens,"minute_high":highs,"minute_low":lows,"minute_close":closes,"minute_volume":volumes}
   mf.write(json.dumps(m,separators=(",",":"))+"\n")
   prev_end_price=z
  summary[sym]={"eligible_days":valid,"covered_session_days":tot,"missing_or_bad_days":days_bad,"up":ct["UP"],"down":ct["DOWN"],"mixed":ct["MIXED"]}
  if si%30==0:print("PROGRESS",si,"/",len(UNIVERSE),"valid_symbol_days",n_rows,flush=True)
meta={"total_eligible_symbol_days":n_rows,"SPY_sessions":len(SESSIONS),"symbol_count":len(UNIVERSE),"symbols_with_over_100_sessions":sum(v["eligible_days"]>=100 for v in summary.values()),"symbols_with_over_400_sessions":sum(v["eligible_days"]>=400 for v in summary.values()),"class_total":{k:sum(v[k] for v in summary.values()) for k in ("up","down","mixed")},"each_symbol":summary,"source_has_coverage_gaps":True}
(DEST/"rth_daily_classifier_summary.json").write_text(json.dumps(meta,indent=2,sort_keys=True))
print("DONE",json.dumps({k:v for k,v in meta.items() if k!="each_symbol"},sort_keys=True),flush=True)
print("SOURCE_META_MISSING",len(MISSING_META),MISSING_META[:15])