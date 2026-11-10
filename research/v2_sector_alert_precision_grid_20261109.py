"""Research-only threshold grid: few events vs after-signal false positives.

A trigger is the first pair of consecutive COMPLETED 5m ETF closes >= threshold
in the same sign, with contemporaneous ETF+peer breadth confirmation.
The eventual +60 minute ETF return is an OUTCOME, never used in triggering.
For nocturnal sessions, use only observed SIP 16:00-20:00/04:00-09:30, no BOATS.
"""
import json,math,statistics
from collections import defaultdict
from datetime import datetime,timedelta,time,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ET=ZoneInfo("America/New_York")
BASE=Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
GOLD=Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
SECTOR={
 "semiconductors":("SOXX",("AMD","MU","NVDA")),
 "gold_miners":("GDX",("NEM","AEM","KGC")),
 "energy":("XLE",("XOM","CVX")),
 "financials":("XLF",("JPM","BAC")),
 "industrials":("XLI",("CAT","GE")),
 "healthcare":("XLV",("UNH","LLY")),
 "software":("IGV",("MSFT","CRM")),
}
def file_for(symbol):
 if symbol in {"SOXX","AMD","MU"}:return "/tmp/semis_52wk_5min_sip_adjusted.json"
 if symbol=="NVDA":return "/tmp/semis_peers_52wk_5min_adjusted.json"
 if symbol in {"GDX","NEM","AEM","KGC"}:return str(GOLD/(symbol+"_sip.json"))
 return str(BASE/(symbol+"_sip.json"))
def load():
 cache={}; out=defaultdict(lambda:defaultdict(dict))
 for sector,(etf,peers) in SECTOR.items():
  for sym in (etf,)+peers:
   path=file_for(sym)
   if path not in cache:cache[path]=json.loads(Path(path).read_text())
   j=cache[path]
   raw=j[sym].items() if isinstance(j.get(sym),dict) else ((r[0],r[1:]) for r in j["bars"])
   for isodt,ohlcv in raw:
    z=datetime.fromisoformat(isodt.replace("Z","+00:00")).astimezone(ET)
    if z.weekday()>=5:continue
    o,h,l,c=[float(v) for v in ohlcv[:4]]
    if min(o,h,l,c)<=0:continue
    out[sym][z.date().isoformat()][z]=(o,h,l,c)
 return out

def compute_day_snapshot(cache,syms,day):
 # exact 09:30 open as reference, all bars in RTH
 series={}
 for sym in syms:
  d=cache[sym].get(day,{})
  r={z.strftime("%H:%M"):v for z,v in d.items() if time(9,30)<=z.time()<=time(15,55)}
  if "09:30" not in r:return None
  series[sym]=r
 return series

def day_signals(sector,cache,threshold,peer_frac=.25):
 etf,peers=SECTOR[sector]
 days=sorted(cache[etf])
 # Five preceding completed RTH sessions, determined entirely BEFORE day.
 historical_days={}
 for sym in (etf,)+peers:
  completed=[]
  for d,bars in cache[sym].items():
   q={z.strftime("%H:%M"):v for z,v in bars.items() if time(9,30)<=z.time()<=time(15,55)}
   if "09:30" in q and "15:55" in q and len(q)>=65:completed.append(d)
  historical_days[sym]=sorted(completed)
 rows=[]
 for day in days:
  if any(sum(old<day for old in historical_days[sym])<5 for sym in (etf,)+peers):
   continue
  # Today only needs a completed opening candle to begin evaluation.
  data=compute_day_snapshot(cache,(etf,)+peers,day)
  if not data:continue
  ref={sym:v["09:30"][0] for sym,v in data.items()}
  records=[(day,k) for k in sorted(data[etf]) if "09:35"<=k<="13:30"]
  first=None
  for _,k in records:
   hm=datetime.strptime(k,"%H:%M")
   previous=(hm-timedelta(minutes=5)).strftime("%H:%M")
   ahead=(hm+timedelta(minutes=60)).strftime("%H:%M")
   if previous not in data[etf]:continue
   cur=data[etf][k][3];prev=data[etf][previous][3]
   for sign in (1,-1):
    if not(sign*(cur/ref[etf]-1)*100>=threshold and
           sign*(prev/ref[etf]-1)*100>=threshold):continue
    current_peers=[]
    for sym in peers:
     if k not in data[sym]:continue
     current_peers.append(sign*100*(data[sym][k][3]/ref[sym]-1)>=threshold*peer_frac)
    if len(current_peers)<len(peers) or sum(current_peers)<(2 if len(peers)==3 else 2):continue
    # Signal is available when candle starting 'k' CLOSES, i.e. k+5m.
    # Future +60m is exact 5m completed bar starting k+60m.
    future=data[etf][ahead][3] if ahead in data[etf] else None
    pnl=sign*100*(future/cur-1) if future is not None else None
    first={"day":day,"sign":sign,"bar_start_ET":k,"signal_at_ET":(hm+timedelta(minutes=5)).strftime("%H:%M"),
           "signal_price":cur,"forward_60m_price":future,"signed_forward_60m_pct":round(pnl,6) if pnl is not None else None,
           "realized_delta_from_open_pct":round(sign*(cur/ref[etf]-1)*100,4)}
    break
   if first:break
  rows.append({"day":day,"event":first})
 return rows

def summary(rows,threshold):
 events=[x["event"] for x in rows if x["event"]]
 n=len(events)
 if not n:return {"events":0,"up":0,"down":0,"forward_positive":0,"forward_plus_50bp":0,"false_for_halfpct":0,
                  "mean_future_signed_pct":None,"event_days":0}
 returns=[x["signed_forward_60m_pct"] for x in events if x["signed_forward_60m_pct"] is not None]
 if not returns:
  return {"events":n,"up":sum(x["sign"]==1 for x in events),"down":sum(x["sign"]==-1 for x in events),
          "forward_positive":0,"forward_plus_50bp":0,"false_for_halfpct":0,
          "unscored_future_data":n,"mean_future_signed_pct":None,
          "earliest_signal":min((x["day"],x["signal_at_ET"]) for x in events),"event_days":n}
 return {"events":n,"up":sum(x["sign"]==1 for x in events),"down":sum(x["sign"]==-1 for x in events),
         "forward_positive":sum(x>0 for x in returns),"forward_plus_50bp":sum(x>=.5 for x in returns),
         "false_for_halfpct":sum(x<.5 for x in returns),
         "unscored_future_data":n-len(returns),
         "mean_future_signed_pct":round(statistics.mean(returns),4),
         "median_future_signed_pct":round(statistics.median(returns),4),
         "worst_future_signed_pct":round(min(returns),4),
         "earliest_signal":min((x["day"],x["signal_at_ET"]) for x in events),
         "event_days":len(set(x["day"] for x in events))}

grid={
 "semiconductors":[2,2.5,3,3.5,4,4.5,5,5.5,6],
 "gold_miners":[2,2.5,3,3.5,4,4.5,5,5.5,6,7],
 "energy":[2.5,3,3.5,4,4.5,5],
 "financials":[2,2.5,3,3.5,4,5],
 "industrials":[2,2.5,3,3.5,4,5],
 "healthcare":[2,2.5,3,3.5,4,5],
 "software":[2.5,3,3.5,4,4.5,5,6]}
def main():
 cache=load();r={}
 for sector in SECTOR:
  samples=[]
  for th in grid[sector]:
   rows=day_signals(sector,cache,th)
   first=int(len(rows)*.7)
   samples.append({"threshold":th,"earlier":summary(rows[:first],th),
                   "later":summary(rows[first:],th),"all":summary(rows,th),
                   "eligible_days":len(rows),"later_days":len(rows)-first})
  r[sector]=samples
 Path("/tmp/v2_sector_alert_precision_grid_20261109.json").write_text(json.dumps(r,indent=2)+"\n")
 for sector,variants in r.items():
  print(sector,"cohort",variants[0]["eligible_days"])
  for x in variants:
   s=x["all"];later=x["later"]
   print(" %4.1f %%  count %3d (late %2d),  fwd>=+.5%% %2d (late %2d)  fwd+ %2d  mean %+0.3f"%(
       x["threshold"],s["events"],later["events"],s["forward_plus_50bp"],
       later["forward_plus_50bp"],s["forward_positive"],s["mean_future_signed_pct"] if s["mean_future_signed_pct"] is not None else 0))
if __name__=="__main__":main()
