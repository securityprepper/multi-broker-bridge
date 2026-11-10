"""V2 research-only. Train-selected 09:35/09:45/10:05 sector breadth signals,
with next-bar delayed entry, strictly prior-five-completed-day context and
chronological later-period evaluation. NO broker connections or order methods.
This is exploratory retrospective research, not a fresh independent holdout.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from collections import defaultdict
from datetime import datetime, time, timedelta
from statistics import mean
from zoneinfo import ZoneInfo
ET=ZoneInfo("America/New_York")
FILES={
 "semiconductors":("SOXX",("AMD","MU","NVDA")),
 "gold_miners":("GDX",("NEM","AEM","KGC")),
 "energy":("XLE",("XOM","CVX")),
 "financials":("XLF",("JPM","BAC")),
 "industrials":("XLI",("CAT","GE")),
 "healthcare":("XLV",("UNH","LLY")),
 "software":("IGV",("MSFT","CRM"))}
SIP="/tmp/v2-run17-cross-sector-precision/alpaca_sip"
GOLD="/tmp/v2-run15-sector-precision-work/alpaca_sip"
SEMI="/tmp/semis_52wk_5min_sip_adjusted.json"
PEERS="/tmp/semis_peers_52wk_5min_adjusted.json"
TIMES=("09:35","09:45","10:05")
# Candidate thresholds set BEFORE looking at test results in this pass.
MIN_SECTOR=(.15,.3,.5,.75,1.0)
MIN_PEER=(0.,.2,.4)
MIN_5M=(None,0.,.10)
MAX_SECTOR=(1.5,3.0)
MIN_BREADTH3=(2,3)
COST=.30
def source(symbol):
 if symbol in ("AMD","MU","SOXX"):return SEMI
 if symbol=="NVDA":return PEERS
 if symbol in ("GDX","NEM","AEM","KGC"):return GOLD+"/"+symbol+"_sip.json"
 return SIP+"/"+symbol+"_sip.json"
def load():
 store={};result=defaultdict(lambda:defaultdict(dict))
 for sector,(etf,peers) in FILES.items():
  for sym in (etf,)+peers:
   p=source(sym)
   if p not in store:store[p]=json.loads(Path(p).read_text())
   j=store[p]
   raw=j[sym].items() if isinstance(j.get(sym),dict) else ((r[0],r[1:]) for r in j["bars"])
   for ts,values in raw:
    dt=datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ET)
    if dt.weekday()>4:continue
    try:
     o,h,l,c=[float(v) for v in values[:4]]
    except (ValueError,TypeError):continue
    if min(o,h,l,c)<=0:continue
    result[sym][dt.date().isoformat()][dt.strftime("%H:%M")]=(o,h,l,c)
 return result
def previous_complete_dates(cache,sym):
 complete=set()
 for day,bars in cache[sym].items():
  if "09:30" in bars and "15:55" in bars and sum("09:30"<=k<="15:55" for k in bars)>=65:
   complete.add(day)
 return sorted(complete)
def make_rows(cache,sector):
 etf,peers=FILES[sector]
 prior={s:previous_complete_dates(cache,s) for s in (etf,)+peers}
 days=sorted(cache[etf])
 result=[]
 for day in days:
  # Presence/absence of today's later bars MUST NOT define signal eligibility.
  if any(sum(d<day for d in prior[s])<5 for s in prior):continue
  bars={s:cache[s].get(day,{}) for s in prior}
  if any("09:30" not in bars[s] for s in prior):continue
  opens={s:bars[s]["09:30"][0] for s in prior}
  clocks=[]
  for decision in TIMES:
   h,m=map(int,decision.split(":"))
   d=datetime(2026,1,1,h,m)
   last=(d-timedelta(minutes=5)).strftime("%H:%M")
   prev=(d-timedelta(minutes=10)).strftime("%H:%M")
   old=(d-timedelta(minutes=20)).strftime("%H:%M")
   enter=(d+timedelta(minutes=5)).strftime("%H:%M")
   next60=(d+timedelta(minutes=60)).strftime("%H:%M")
   exit_clock="14:35" # final 5m close at 14:40 ET (13:40 Chicago)
   observed={}
   for s,b in bars.items():
    if last not in b or prev not in b:break
    p=b[last][3];was=b[prev][3]
    observed[s]={"pct":100*(p/opens[s]-1),"m5":100*(p/was-1),"mark":p}
   else:
    # Outcomes only. They may be None; NEVER filter signal eligibility on them.
    entry_open=bars[etf].get(enter,(None,))[0]
    future60=bars[etf].get(next60,(None,None,None,None))[3]
    final=bars[etf].get(exit_clock,(None,None,None,None))[3]
    # Confirm 5-minute signal closes no later than decision time.
    clocks.append({"decision":decision,"past":observed,"entry_open":entry_open,
                   "p60":future60,"pend":final,
                   "sector_history_available":old in bars[etf]})
  if clocks:result.append({"day":day,"windows":clocks})
 return result
def qualify(win,side,sector_min,peer_min,breadth,minimum_momentum,maximum_pct,sector):
 etf,peers=FILES[sector]
 f=win["past"]
 if side*f[etf]["pct"]<sector_min or side*f[etf]["pct"]>maximum_pct:return False
 if minimum_momentum is not None and side*f[etf]["m5"]<minimum_momentum:return False
 if sum(side*f[p]["pct"]>=peer_min for p in peers)<breadth:return False
 return True
def evaluate(rows,sector,policy,cost=.30):
 minimum,peer_min,breadth,momentum,max_pct,side=policy
 triggered=[];no_signal=0
 for row in rows:
  matched=None
  for w in row["windows"]:
   if qualify(w,side,minimum,peer_min,breadth,momentum,max_pct,sector):
    matched=w;break
  if not matched:
   no_signal+=1;continue
  # Do NOT drop a signal from the denominator when future mark unavailable.
  entry=matched["entry_open"]
  nxt=matched["p60"]
  flat=matched["pend"]
  r60=side*100*(nxt/entry-1) if entry is not None and nxt is not None else None
  rflat=side*100*(flat/entry-1) if entry is not None and flat is not None else None
  triggered.append({"day":row["day"],"clock":matched["decision"],
                    "p_entry":entry,"p_60":nxt,"p_flat":flat,
                    "future60_raw_pct":r60,"flat_raw_pct":rflat,
                    "after30bp_60":r60-cost if r60 is not None else None,
                    "after30bp_flat":rflat-cost if rflat is not None else None})
 return triggered,len(rows),no_signal
def stats(trades,rows,none):
 scored=[x for x in trades if x["after30bp_60"] is not None]
 n=len(scored)
 net=[x["after30bp_60"] for x in scored]
 flat=[x["after30bp_flat"] for x in trades if x["after30bp_flat"] is not None]
 return {"eligible_days":rows,"signals":len(trades),"abstain":none,
   "signal_coverage":round(len(trades)/rows,3) if rows else 0,
   "future_60m_scored":n,"future_60m_unscored":len(trades)-n,
   "future_60m_direction_correct":sum(x["future60_raw_pct"]>0 for x in scored),
   "future_60m_gt_0_5pct_raw":sum(x["future60_raw_pct"]>=.5 for x in scored),
   "after30bp_60m_winners":sum(x>0 for x in net),
   "after30bp_60m_win_pct":round(100*sum(x>0 for x in net)/n,2) if n else None,
   "after30bp_60m_mean_pct":round(mean(net),4) if n else None,
   "after30bp_60m_worst_pct":round(min(net),4) if n else None,
   "after30bp_flat_win_pct":round(100*sum(x>0 for x in flat)/len(flat),2) if flat else None,
   "after30bp_flat_mean_pct":round(mean(flat),4) if flat else None,
   "by_signal_time":{t:sum(x["clock"]==t for x in trades) for t in TIMES}}
def policy_grid(sector):
 _,peers=FILES[sector];allowed=(2,3) if len(peers)==3 else (2,)
 for direction in (1,-1):
  for a in MIN_SECTOR:
   for b in MIN_PEER:
    for n in allowed:
     for m in MIN_5M:
      for maxpct in MAX_SECTOR:
       if a>maxpct:continue
       yield (a,b,n,m,maxpct,direction)
def rank(s):
 # Only earlier data used to rank candidates; prioritize precision with coverage
 if s["future_60m_scored"]<18 or s["signal_coverage"]<.08:return -1e6
 return (s["after30bp_60m_mean_pct"] or -999)+.10*(s["after30bp_60m_win_pct"] or 0)/100
def compare_sector(sector,cache):
 rows=make_rows(cache,sector)
 split=int(.70*len(rows))
 train,test=rows[:split],rows[split:]
 best=None
 eligible=0;passing=[]
 for policy in policy_grid(sector):
  tr,nt,na=evaluate(train,sector,policy)
  sm=stats(tr,nt,na)
  eligible+=1
  r=rank(sm)
  if r<=-1e5:continue
  if best is None or r>best[0]:best=(r,policy,sm)
  if (sm["after30bp_60m_win_pct"] or 0)>=65 and (sm["after30bp_60m_mean_pct"] or -1)>0:
   passing.append((r,policy,sm))
 if not best:
  return {"error":"No training candidate with >=18 observations and 8% coverage","eligible_days":len(rows),"tested_candidates":eligible}
 def audit(item):
  _,pol,ts=item
  sh,nn,ab=evaluate(test,sector,pol)
  return {"policy":list(pol),"earlier":ts,"later":stats(sh,nn,ab),
          "later_events":sh}
 return {"eligible_days":len(rows),"test_start":test[0]["day"],"test_days":len(test),
         "tested_candidates":eligible,"training_qualifiers":len(passing),
         "best_training_shadow":audit(best),
         "training_policy_pass_65pct":audit(max(passing,key=lambda x:x[0])) if passing else None}
def run():
 cache=load();result={}
 for sector in FILES:
  result[sector]=compare_sector(sector,cache)
  b=result[sector]
  if "best_training_shadow" in b:
   print(sector,"train candidates",b["tested_candidates"],"pass",b["training_qualifiers"],
         "best earlier",b["best_training_shadow"]["earlier"]["after30bp_60m_win_pct"],
         "later",b["best_training_shadow"]["later"]["after30bp_60m_win_pct"],
         "signals later",b["best_training_shadow"]["later"]["signals"])
  else:print(sector,"no eligible training candidate")
 out=Path("/tmp/v2_next_move_first_7sector_walkforward_20261109.json")
 out.write_text(json.dumps(result,indent=2)+"\n")
 print("RESULTS",str(out),out.stat().st_size)
if __name__=="__main__":run()
