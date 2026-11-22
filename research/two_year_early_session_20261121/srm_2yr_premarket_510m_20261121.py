#!/usr/bin/env python3
"""Research-only every-completed-minute 00:00-08:30 America/Chicago premarket
predictive study, split-adjusted Alpaca SIP + BOATS trade bars.
Never substitutes last week's price for missing minute; no real orders.
"""
from pathlib import Path
import csv,collections,datetime as dt,gzip,json,math,statistics,os
CT=dt.timezone(dt.timedelta(hours=-6)) # REPLACED BELOW by ZoneInfo
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago");UTC=dt.timezone.utc
ROOT=Path("/var/lib/securityprepper-two-year-early-session-research")
RESEARCH=Path("/var/lib/securityprepper-two-year-intraday-research")
CFG=json.loads((ROOT/"manifest_config.json").read_text())
GROUPS=json.loads(Path("/var/lib/securityprepper-two-year-sector-backtest/full_membership_frozen.json").read_text())["groups"]
PRIORITY=json.loads(Path("/opt/securityprepper/quality-opportunity-watch/priority_universe.json").read_text())["groups"]
SECTOR={}
for g in ("Semiconductors","Cybersecurity","Storage","AI infrastructure"):
 for s in PRIORITY.get(g,[]):SECTOR.setdefault(s,"Semiconductors" if g=="Storage" else g)
for g,v in GROUPS.items():
 for s in v["peers"]:SECTOR.setdefault(s,g)
for g,v in GROUPS.items():SECTOR.setdefault(v["etf"],g)
ETFS={g:v["etf"] for g,v in GROUPS.items()}
REF={"SPY"}|set(ETFS.values())
START=dt.date(2024,11,20);END=dt.date(2026,11,20)
def split(d):
 return "TRAIN" if d<="2025-11-19" else ("VALIDATE" if d<="2026-05-19" else "HOLDOUT")
def pct(x,y):
 return 100*(y/x-1) if x and y and x>0 else None
def iter_day(sym):
 """Each bar's t is minute START. Only visible after minute END."""
 maps=collections.defaultdict(dict)
 for feed,folder in (("BOATS","BOATS_NIGHT"),("SIP","SIP_PRE")):
  p=ROOT/folder/(sym+".csv.gz")
  if not p.is_file():continue
  with gzip.open(p,"rt",newline="") as f:
   for a in csv.reader(f):
    try:
     t=int(a[0]);bar=dt.datetime.fromtimestamp(t*60,UTC).astimezone(CT)
     if bar.date()<START or bar.date()>END:continue
     off=bar.hour*60+bar.minute
     if not 0<=off<510:continue
     v=float(a[5]);c=float(a[4])
     if v<=0 or c<=0 or not math.isfinite(c):continue
     prior=maps[str(bar.date())].get(off)
     if prior and prior[1]!=c:
      if feed!="SIP":continue # SIP dominates feed overlap, no synthetic averaging.
     maps[str(bar.date())][off]=(feed,c,v)
    except (ValueError,IndexError,TypeError):continue
 for d,items in sorted(maps.items()):
  yield d,items
def rth():
 result={}
 p=RESEARCH/"daily_classes_20241120_20261120.csv"
 with p.open(newline="") as f:
  for r in csv.DictReader(f):
   result[(r["symbol"],r["date"])]=r
 return result
def summary(o):
 n=o[0];return {"observed":n,"hit":o[1],"hit_pct":round(100*o[1]/n,2) if n else None,
 "mean_directional_rth_open_flat_pct":round(o[2]/n,4) if n else None}
def main():
 a=rth()
 required=set(CFG["symbols"]);allrefs={}
 for i,s in enumerate(REF):
  allrefs[s]={d:mp for d,mp in iter_day(s)}
 print("REFERENCES_LOADED",len(allrefs),"first",list(allrefs)[:8],flush=True)
 global_stats=collections.defaultdict(lambda:[0,0,0.0])
 ticker_stats=collections.defaultdict(lambda:[0,0,0.0])
 midnight_stats=collections.defaultdict(lambda:[0,0,0.0])
 midnight_by_ticker=collections.defaultdict(lambda:[0,0,0.0])
 midnight_cov=collections.Counter();preopen_cov=collections.Counter()
 by_sym_first=collections.defaultdict(list)
 first_signal=[]
 total=0
 for j,sym in enumerate(CFG["symbols"],1):
  if sym in REF:continue
  g=SECTOR.get(sym)
  if not g or g not in ETFS:continue
  ETF=ETFS[g]
  prior_symbol={}
  for d,mp in iter_day(sym):
   day=a.get((sym,d));spi=a.get(("SPY",d));etfi=a.get((ETF,d))
   if not day or not spi or not etfi:continue
   prev=float(day["previous_rth_close"]) if day.get("previous_rth_close") else None
   openp=float(day["split_adj_rth_open"])
   flat=float(day["hard_flat_price"]) if day.get("hard_flat_price") else None
   if not (prev and openp and flat):continue
   snap_spy=allrefs.get("SPY",{}).get(d)
   snap_etf=allrefs.get(ETF,{}).get(d)
   if snap_spy is None or snap_etf is None:continue
   midnight=(next(((t,x) for t,x in sorted(mp.items()) if t<=10),None))
   mid_mkt=next(((t,x) for t,x in sorted(snap_spy.items()) if t<=10),None)
   mid_etf=next(((t,x) for t,x in sorted(snap_etf.items()) if t<=10),None)
   if midnight and mid_mkt and mid_etf:midnight_cov["all_three_near_midnight"]+=1
   if midnight:midnight_cov["has_first_trade_before_0010"]+=1
   else:midnight_cov["missing_trade_around_midnight"]+=1
   if any(t>=500 for t in mp):preopen_cov["last10m_trade_present"]+=1
   total+=1
   # Record at each minute m, only completed bars <= m available and <=2min old.
   minute_signal_first={}
   st_times=sorted(mp);ref_market_times=sorted(snap_spy);ref_etf_times=sorted(snap_etf)
   last_s=None;last_m=None;last_e=None; history=collections.deque(maxlen=60)
   ii=jj=kk=0
   first_intraday_open=(openp/prev-1)*100
   for m in range(1,511):
    while ii<len(st_times) and st_times[ii]<m: last_s=(st_times[ii],mp[st_times[ii]][1]);ii+=1
    while jj<len(ref_market_times) and ref_market_times[jj]<m: last_m=(ref_market_times[jj],snap_spy[ref_market_times[jj]][1]);jj+=1
    while kk<len(ref_etf_times) and ref_etf_times[kk]<m: last_e=(ref_etf_times[kk],snap_etf[ref_etf_times[kk]][1]);kk+=1
    if not last_s or m-(last_s[0]+1)>2:continue
    p=last_s[1]
    if p<5:continue
    # Directional event price floor and causal prior close both verified per date.
    # Positive/negative labels are RTH open->13:40, not price change already made overnight.
    # No new broker entry is attempted.
    if not last_m or not last_e:continue
    if m-(last_m[0]+1)>2 or m-(last_e[0]+1)>2:continue
    mp0=last_m[1];ep0=last_e[1]
    if mp0<5 or ep0<5:continue
    spyprev=float(spi["previous_rth_close"]) if spi.get("previous_rth_close") else None
    etfprev=float(etfi["previous_rth_close"]) if etfi.get("previous_rth_close") else None
    if not spyprev or not etfprev:continue
    rg=pct(prev,p);mg=pct(spyprev,mp0);eg=pct(etfprev,ep0)
    # 1min every minute: causal prior-close AND independent midnight-anchor rule.
    # The midnight anchor is the actual first completed trade within 10min, not a synthetic 00:00 price.
    for sign in (+1,-1):
     if midnight and mid_mkt and mid_etf and m>=max(midnight[0],mid_mkt[0],mid_etf[0])+1:
      cmid=sign*pct(midnight[1][1],p)
      mmid=sign*pct(mid_mkt[1][1],mp0)
      emid=sign*pct(mid_etf[1][1],ep0)
      if cmid>=.75 and mmid>=.10 and emid>=.25:
       future=sign*pct(openp,flat)
       md=midnight_stats[(m,sign,split(d))]
       md[0]+=1;md[1]+=int(future>.25);md[2]+=future
       tick=midnight_by_ticker[(sym,m,sign,split(d))]
       tick[0]+=1;tick[1]+=int(future>.25);tick[2]+=future
     if not(sign*rg>=1 and sign*mg>=.2 and sign*eg>=.35):continue
     future=sign*pct(openp,flat)
     record=global_stats[(m,sign,split(d))]
     record[0]+=1;record[1]+=int(future>.25);record[2]+=future
     target=ticker_stats[(sym,m,sign,split(d))]
     target[0]+=1;target[1]+=int(future>.25);target[2]+=future
     # Keep earliest first signal only for this side/symbol/date.
     if sign not in minute_signal_first:minute_signal_first[sign]={"symbol":sym,"date":d,"direction":sign,"signal_minute":m,"signal_time_ct":f"{m//60:02d}:{m%60:02d}","asof_price":p,
       "prev_close_gap_pct":round(rg,4),"spy_prev_gap_pct":round(mg,4),"etf_prev_gap_pct":round(eg,4),
       "at_open_flat_direction_pct":round(future,4),"label":day["day_class"],
       "valid_midnight_baseline":midnight is not None,
       "midnight_baseline_minute":midnight[0] if midnight else None,"segment":split(d),
       "feed":mp[last_s[0]][0]}
   first_signal.extend(minute_signal_first.values())
  if j%35==0:print("PROGRESS",j,"/",len(CFG["symbols"]),"eligible_symbol_days",total,flush=True)
 report={"schema":1,"model":"Earliest every-minute (m=1..510) premarket same-sign stock>=1%, SPY>=0.2%, sector ETF>=0.35% since prev split-adjusted RTH close, with 2m source freshness, hypothetical RTH open entry and pre-13:40 flat","source":"Alpaca SIP/BOATS split-adjusted one-minute trade bars","time_zone":"America/Chicago","coverage":{"eligible_symbol_days":total,**dict(midnight_cov),**dict(preopen_cov)},"train":"2024-11-20 through 2025-11-19","validation":"2025-11-20 through 2026-05-19","holdout":"2026-05-20 through 2026-11-20","bars_not_quotes":True,"actual_fills":0,
 "minute_aggregate":{f"{m}:{side}:{part}":summary(v) for (m,side,part),v in global_stats.items()},
 "true_near_midnight_anchor_rule":{f"{m}:{side}:{part}":summary(v) for (m,side,part),v in midnight_stats.items()},
 "first_signals":first_signal}
 (RESEARCH/"premarket_510minute_priorclose_market_sector_holdout.json").write_text(json.dumps(report,indent=2))
 # A compact, per-minute cross-universe holdout summary for every minute.
 with (RESEARCH/"premarket_every_minute_oos_20241120_20261120.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["minute_since_midnight_CT","time_CT","side","train_n","train_win_pct","validate_n","validate_win_pct","holdout_n","holdout_win_pct","holdout_mean_open_to_flat_pct"])
  for m in range(1,511):
   for sign in (+1,-1):
    u=[summary(global_stats.get((m,sign,t),[0,0,0])) for t in ("TRAIN","VALIDATE","HOLDOUT")]
    w.writerow([m,f"{m//60:02d}:{m%60:02d}","UP" if sign==1 else "DOWN",
               u[0]["observed"],u[0]["hit_pct"],u[1]["observed"],u[1]["hit_pct"],u[2]["observed"],u[2]["hit_pct"],u[2]["mean_directional_rth_open_flat_pct"]])
 with (RESEARCH/"premarket_midnight_anchor_minute_oos.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["minute_since_midnight_CT","side","train_n","train_hit_pct","validation_n","validation_hit_pct","holdout_n","holdout_hit_pct","holdout_mean_open_to_flat_pct"])
  for m in range(1,511):
   for sign in (+1,-1):
    a0,b0,c0=[summary(midnight_stats.get((m,sign,seg),[0,0,0.0])) for seg in ("TRAIN","VALIDATE","HOLDOUT")]
    w.writerow([m,"UP" if sign==1 else "DOWN",a0["observed"],a0["hit_pct"],b0["observed"],b0["hit_pct"],c0["observed"],c0["hit_pct"],c0["mean_directional_rth_open_flat_pct"]])
 with (RESEARCH/"premarket_first_signals_per_symbol_day.csv").open("w",newline="") as f:
  if first_signal:
   w=csv.DictWriter(f,fieldnames=list(first_signal[0]));w.writeheader();w.writerows(first_signal)
 # Choose each ticker's best 1-minute premarket signal time on TRAIN ONLY;
 # later periods are untouched with respect to selection, no broker order.
 choices=[]
 keys={s for (s,m,sign,period) in ticker_stats.keys()}
 for sym in sorted(keys):
  ranked=[]
  for sign in (+1,-1):
   for m in range(1,511):
    tr=ticker_stats.get((sym,m,sign,"TRAIN"),[0,0,0.0])
    if tr[0]<25:continue
    ss=summary(tr)
    score=ss["mean_directional_rth_open_flat_pct"]-0.25-1.5/(tr[0]**.5)
    ranked.append((score,m,sign))
  if not ranked:
   choices.append({"symbol":sym,"choice":"NO_TRAINING_SUPPORT"});continue
  score,m,sign=max(ranked)
  snapshots=[summary(ticker_stats.get((sym,m,sign,part),[0,0,0.0])) for part in ("TRAIN","VALIDATE","HOLDOUT")]
  tr,va,ho=snapshots
  nonnegative=(va["observed"]>=20 and ho["observed"]>=20 and
     tr["mean_directional_rth_open_flat_pct"]>0.25 and
     va["mean_directional_rth_open_flat_pct"]>0.25 and
     ho["mean_directional_rth_open_flat_pct"]>0.25 and
     va["hit_pct"]>=55 and ho["hit_pct"]>=55)
  choices.append({"symbol":sym,"minute_chosen_train_only":m,"minute_local_CT":f"{m//60:02d}:{m%60:02d}",
    "signal_side":"UP" if sign==1 else "DOWN_RESEARCH_ONLY","train":tr,"validate":va,"holdout":ho,
    "positive_proxy_on_all_three_periods":nonnegative,"actual_broker_fill":False})
 report["per_symbol_training_time_choice"]=choices
 (RESEARCH/"premarket_510minute_priorclose_market_sector_holdout.json").write_text(json.dumps(report,indent=2))
 with (RESEARCH/"premarket_symbol_training_selected_minute.csv").open("w",newline="") as f:
  w=csv.writer(f);w.writerow(["symbol","side","train_chosen_minute_CT","train_n","train_mean_gross_pct","val_n","val_mean_gross_pct","holdout_n","holdout_mean_gross_pct","holdout_hit_pct","research_only_proxy_positive"])
  for x in choices:
   if "train" not in x:w.writerow([x["symbol"],"NO_VALIDATED_SIGNAL"]);continue
   tr,va,ho=x["train"],x["validate"],x["holdout"]
   w.writerow([x["symbol"],x["signal_side"],x["minute_local_CT"],tr["observed"],tr["mean_directional_rth_open_flat_pct"],va["observed"],va["mean_directional_rth_open_flat_pct"],ho["observed"],ho["mean_directional_rth_open_flat_pct"],ho["hit_pct"],x["positive_proxy_on_all_three_periods"]])
 print("DONE",json.dumps({"symbol_days":total,"first_signals":len(first_signal),"minute_census":len(global_stats),"midnight_trade":midnight_cov["has_first_trade_before_0010"],"missing_midnight":midnight_cov["missing_trade_around_midnight"],"last10m_data":preopen_cov["last10m_trade_present"]}),flush=True)
 for m in (60,120,180,240,300,360,420,480,500):
  for side in (1,-1):
   stat=summary(global_stats.get((m,side,"HOLDOUT"),[0,0,0]))
   print("HOLDOUT_MINUTE",m,"DIR",side,stat,flush=True)
if __name__=="__main__":main()