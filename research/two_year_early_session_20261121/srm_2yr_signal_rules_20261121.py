#!/usr/bin/env python3
"""Research-only causal early-session signal builder. Every minute 1..120,
but one earliest event/rule/day/side, with SPY/sector/peer confirmation.
No broker activity, no quotes falsely inferred from SIP trade closes.
"""
from pathlib import Path
import csv,collections,datetime as dt,gzip,importlib.util,json,math
TOP=Path("/var/lib/securityprepper-two-year-intraday-research")
feat=Path("/tmp/srm_2yr_early_direction_20261121.py")
spec=importlib.util.spec_from_file_location("direction",feat)
direction=importlib.util.module_from_spec(spec);spec.loader.exec_module(direction)
def readpremarket():
 p=TOP/"premarket_first_signals_per_symbol_day.csv";r={}
 if not p.exists():return r
 with p.open(newline="") as f:
  for x in csv.DictReader(f):
   try:
    if int(x["signal_minute"])<450:continue
    key=(x["symbol"],x["date"],int(x["direction"]))
    if key not in r or int(x["signal_minute"])<int(r[key]["signal_minute"]):r[key]=x
   except (KeyError,ValueError):continue
 return r
def ratio(p0,p1):return 100*(p1/p0-1) if p0 and p1 and p0>0 else None
def signal_one(m,dirn,row,stock_market,peer_count,overnight):
 cp=row["minute_close"]
 if m>len(cp):return None
 idx=m-1
 if cp[idx] is None:return None
 p=cp[idx];op=row["rth_open"];prev=row.get("prev_rth_close")
 if p<5 or not prev or prev<0:return None
 mark,etf=stock_market
 if m>len(mark["close"]) or m>len(etf["close"]):return None
 a=mark["close"][idx];b=etf["close"][idx]
 if a is None or b is None:return None
 sx=dirn*ratio(op,p)
 mx=dirn*ratio(mark["open"],a)
 ex=dirn*ratio(etf["open"],b)
 if sx is None or mx is None or ex is None:return None
 n=peer_count[2][idx];was_self=peer_count[3]
 n-=int(was_self)
 if n<3:return None
 pcount=(peer_count[0][idx] if dirn==1 else peer_count[1][idx])
 pcount-=int(was_self and sx>=.10)
 breadth=pcount/n
 recent5=None
 if idx>=5 and cp[idx-5] is not None:recent5=dirn*ratio(cp[idx-5],p)
 recent10=None
 if idx>=10 and cp[idx-10] is not None:recent10=dirn*ratio(cp[idx-10],p)
 recent15=None
 if idx>=15 and cp[idx-15] is not None:recent15=dirn*ratio(cp[idx-15],p)
 gap=dirn*ratio(prev,op)
 ext=dirn*ratio(prev,p)
 if ext is None or abs(ext)>6:return None
 recent_valid=sum(1 for j in range(max(0,idx-5),idx+1) if cp[j] is not None)
 if recent_valid<5:return None
 passed=[]
 if m>=5 and sx>=.40 and mx>=.10 and ex>=.15 and breadth>=.65 and (recent5 is None or recent5>=.25):
  passed.append("ALIGN_5M")
 if m>=15 and sx>=.75 and mx>=.20 and ex>=.35 and breadth>=.70 and recent5 is not None and recent5>=.10:
  passed.append("ALIGN_15M")
 if m>=30 and sx>=1.0 and mx>=.30 and ex>=.50 and breadth>=.70 and recent10 is not None and recent10>=.15:
  passed.append("ALIGN_30M")
 if m>=60 and sx>=1.5 and mx>=.5 and ex>=.75 and breadth>=.75 and recent15 is not None and recent15>=.20:
  passed.append("ALIGN_60M")
 if m>=5 and mark.get("prev") and etf.get("prev") and recent5 is not None:
  market_from_prev=dirn*ratio(mark["prev"],a)
  sector_from_prev=dirn*ratio(etf["prev"],b)
  if market_from_prev>=1.0 and sector_from_prev>=1.0 and breadth>=.75 and sx>=.30 and recent5>=.10:
   passed.append("MARKET_SECTOR_1PCT_BREADTH75")
 if m>=10 and gap<=-1.5 and sx>=.40 and recent5 is not None and recent5>=.30 and mx>=0 and ex>=0 and breadth>=.55:
  passed.append("GAP_REBOUND")
 if m>=11 and mx>=.1 and ex>=.15 and breadth>=.60 and sx>=.50 and recent5 is not None and recent5>=.15:
  h0=row["minute_high"][:10];l0=row["minute_low"][:10]
  if all(v is not None for v in h0+l0):
   breakout=(p/max(h0)-1)*100 if dirn==1 else (min(l0)/p-1)*100
   if breakout>=.10:passed.append("OPENING_10M_RANGE_BREAK")
 if m>=10 and breadth>=.80 and mx>=.15 and ex>=.20 and sx>=.15 and recent5 is not None and recent5>=.05:
  passed.append("PEER_BREADTH_80")
 if m>=5 and overnight and sx>=.30 and mx>=.10 and ex>=.15 and breadth>=.65 and recent5 is not None and recent5>=.15:
  passed.append("OVERNIGHT_LATE_ALIGNMENT")
 return {"passed":passed,"strength_stock_open_pct":round(sx,4),
         "stock_from_prev_close_pct":round(ratio(prev,p),4),
         "strength_market_open_pct":round(mx,4),
         "strength_sector_open_pct":round(ex,4),
         "breadth_fraction":round(breadth,4),
         "recent5_signed_pct":round(recent5,4) if recent5 is not None else None,
         "recent10_signed_pct":round(recent10,4) if recent10 is not None else None,
         "gap_from_prev_signed_pct":round(gap,4)}
def main():
 bench,breadth=direction.load()
 overnight=readpremarket()
 out=TOP/"first_120_minute_rule_events.jsonl.gz"
 byrule=collections.Counter();byyear=collections.Counter();rows=0;skipped=collections.Counter()
 with gzip.open(direction.SRC,"rt") as src,gzip.open(out,"wt",compresslevel=3) as f:
  for i,line in enumerate(src,1):
   row=json.loads(line);sym=row["symbol"];d=row["date"];g=direction.map_sector.get(sym)
   if not g or sym in direction.sector_references:continue
   etf=direction.etf_for.get(g)
   spy=bench.get(("SPY",d));sec=bench.get((etf,d))
   peers=breadth.get((g,d))
   if not spy or not sec or not peers or not row.get("prev_rth_close") or not row.get("hard_flat_price"):
    skipped["NO_REFERENCES"]+=1;continue
   keys=set()
   for m in range(1,121):
    for sign in (+1,-1):
     isovernight=(sym,d,sign) in overnight
     info=signal_one(m,sign,row,(spy,sec),(peers[0],peers[1],peers[2],sym in direction.member_of and g in direction.member_of[sym]),isovernight)
     if not info:continue
     for rule in info["passed"]:
      key=(rule,sign)
      if key in keys:continue
      keys.add(key)
      ev={"symbol":sym,"date":d,"sector":g,"etf":etf,"rule":rule,
         "side":"LONG" if sign==1 else "SHORT_PAPER_RESEARCH_ONLY",
         "dir":sign,"signal_minute":m,"signal_start_offset":m-1,
         "entry_offset":m,
         "signal_price_completed_1m_close":row["minute_close"][m-1],
         "first_regular_open":row["rth_open"],
         "session_end":row["session_minutes"],"flat_offset":row["hard_flat_minute_offset"],
         "flat_price":row["hard_flat_price"],"day_class":row["label"],
         "source_bar_is_quote":False,
         "pre_market_alignment_evidence":overnight.get((sym,d,sign)) if rule=="OVERNIGHT_LATE_ALIGNMENT" else None,
         "fields_asof_signal":{k:v for k,v in info.items() if k!="passed"},
         "split":direction.segment(d),
         "eligibility":"RESEARCH_ONLY_AFTER_10AM" if m>90 else "RESEARCH_ONLY_ASOF_LT_10AM",
         "broker_eligibility":"NOT_CLEARED_NEWS_SPREAD_ACCOUNT_NO_ORDER"}
      f.write(json.dumps(ev,separators=(",",":"))+"\n")
      byrule[(rule,ev["side"])]+=1;byyear[ev["split"]]+=1;rows+=1
   if i%25000==0:print("PROGRESS",i,"events",rows,flush=True)
 summary={"events_total":rows,"rule_counts":{f"{k[0]}:{k[1]}":v for k,v in byrule.items()},
 "split_counts":dict(byyear),"research_only":True,"no_paper_or_live_broker_calls":True,
 "rule_granularity":"Each completed 1-minute RTH bar from +1 to +120m; earliest trigger per rule/side/day"}
 (TOP/"first_120_minute_rule_events_summary.json").write_text(json.dumps(summary,indent=2))
 print("DONE",json.dumps(summary,sort_keys=True),flush=True)
if __name__=="__main__":main()