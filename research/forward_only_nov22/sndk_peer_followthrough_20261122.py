#!/usr/bin/env python3
"""SNDK historical-only, peer-breadth first-signal short-horizon follow-through.
Reproduce the source rule before inspecting futures; no broker actions.
"""
from pathlib import Path
import csv,gzip,json,math,collections,statistics,datetime as dt,importlib.util
ROOT=Path("/var/lib/securityprepper-two-year-intraday-research")
DIRECTION=Path("/tmp/srm_2yr_early_direction_20261121.py")
p=importlib.util.spec_from_file_location("sourc",DIRECTION);q=importlib.util.module_from_spec(p);p.loader.exec_module(q)
STOCK="SNDK"
def seg(d):return q.segment(d)
def pct(a,b):return 100*(b/a-1) if a and b and a>0 else None
def main():
 refs,breadth=q.load()
 market={}
 src=Path("/var/lib/securityprepper-two-year-sector-backtest/sip1m")/(STOCK+".csv.gz")
 extra=Path("/var/lib/securityprepper-two-year-early-session-research/SIP_RTH_NOV20")/(STOCK+".csv.gz")
 for file in (src,extra):
  if not file.exists():continue
  with gzip.open(file,"rt",newline="") as f:
   for data in csv.reader(f):
    minute=int(data[0]);ts=dt.datetime.fromtimestamp(minute*60,dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=-6)))
    # UTC epoch minute adjusted to Chicago via zoneinfo, not constant offset.
    from zoneinfo import ZoneInfo
    local=dt.datetime.fromtimestamp(minute*60,dt.timezone.utc).astimezone(ZoneInfo("America/Chicago"))
    d=str(local.date());idx=(local.hour*60+local.minute)-(8*60+30)
    if idx<0 or idx>=390:continue
    c=float(data[4]);v=float(data[5])
    if c>0 and v>0:market.setdefault(d,{})[idx]=(c,v)
 rows=[];byseg=collections.defaultdict(list)
 with gzip.open(ROOT/"minute_early_features_20241120_20261120.jsonl.gz","rt") as f:
  for line in f:
   row=json.loads(line)
   if row.get("symbol")!=STOCK:continue
   date=row["date"];g=q.map_sector.get(STOCK);e=q.etf_for.get(g)
   spy=refs.get(("SPY",date));sector=refs.get((e,date));peer=breadth.get((g,date))
   if not spy or not sector or not peer:continue
   mp=row["minute_close"];op=row["rth_open"]
   for m in range(8,121):
    k=m-1
    p0=mp[k]
    if p0 is None or p0<5 or k<5 or mp[k-5] is None:continue
    a=spy["close"][k];b=sector["close"][k]
    if a is None or b is None:continue
    stock=pct(op,p0);last5=pct(mp[k-5],p0)
    sm=pct(spy["open"],a);se=pct(sector["open"],b)
    etf5=pct(sector["close"][k-5],b) if sector["close"][k-5] is not None else None
    if etf5 is None:continue
    included=(STOCK in q.member_of and g in q.member_of[STOCK])
    n=peer[2][k]-int(included);pnum=peer[0][k]-int(included and stock>=.10)
    if n<3:continue
    prev=row.get("prev_rth_close")
    if not prev:continue
    if any(x is None for x in mp[k-5:k+1]):continue
    if mp[k-3] is None or spy["close"][k-5] is None:continue
    if not(pnum/n>=.8 and sm>=.1 and se>=.2 and stock>=.2 and last5>=.05 and etf5>=.1):continue
    futures={}
    for hz in (5,10,30,60,120):
     future=market.get(date,{}).get(m+hz-1)
     futures[f"+{hz}m_pct"]=round(pct(p0,future[0]),4) if future else None
    pct_end=pct(p0,row["hard_flat_price"])
    line={"symbol":STOCK,"date":date,"segment":seg(date),"first_signal_minute":m,
          "alert_CT":f"{8+(30+m)//60:02d}:{(30+m)%60:02d}",
          "signal_price_trade_close":p0,"sector":g,"peer_fraction":round(pnum/n,4),
          "forward_to_hard_flat_pct":round(pct_end,4),
          "forward_to_hard_flat_minus25bp_proxy_pct":round(pct_end-.25,4),
          **futures,"NO_BROKER_FILL":True}
    rows.append(line);byseg[seg(date)].append(line)
    break
 out=ROOT/"SNDK_EARLY_PEER_BREADTH_FORWARD_HORIZONS_HISTORICAL.csv"
 with out.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 for segm,subset in byseg.items():
  print("COHORT",segm,"n",len(subset))
  for name in ["+5m_pct","+10m_pct","+30m_pct","+60m_pct","+120m_pct","forward_to_hard_flat_pct","forward_to_hard_flat_minus25bp_proxy_pct"]:
   vals=[r[name] for r in subset if r[name] is not None]
   print("HORIZON",name,"observed",len(vals),"mean",round(statistics.mean(vals),4) if vals else None,"positive",sum(v>0 for v in vals),"negative",sum(v<0 for v in vals))
 print("SAVED",out,"total_events",len(rows))
if __name__=="__main__":main()