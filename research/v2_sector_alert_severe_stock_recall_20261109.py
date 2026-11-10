"""V2 retrospective: how high sector-shock screens overlap genuine stock drawdowns.

Research-only, no broker writes, no production imports. Uses 52wk adjusted SIP
five-minute bars from prior independent sector ETF and constituent collectors.
A forecast outcome is NEVER consulted when issuing a candidate signal.
"""
from __future__ import annotations

from collections import defaultdict
from bisect import bisect_left
from datetime import date, datetime, time, timedelta
from pathlib import Path
import json
import sys

# Same-directory published research input reader; no production/trader imports.
import v2_sector_alert_precision_grid_20261109 as source

ET_TIME_OPEN = time(9, 30)
ET_TIME_LAST = time(15, 55)
THRESHOLDS_NEW = {
 "semiconductors":5.0, "gold_miners":5.0, "energy":3.0,
 "financials":3.0,"industrials":3.0,"healthcare":3.0,"software":4.0}
THRESHOLDS_OLD = {
 "semiconductors":2.0, "gold_miners":2.0, "energy":3.0,
 "financials":3.0,"industrials":3.0,"healthcare":3.0,"software":3.0}

_rth_memo={}
_complete_memo={}
_source_refs={}  # strong references avoid id(cache) recycling across tiny synthetic tests
def rth(cache,sym,day):
 _source_refs[id(cache)]=cache
 key=(id(cache),sym,day)
 if key not in _rth_memo:
  _rth_memo[key]={dt:v for dt,v in cache.get(sym,{}).get(day,{}).items()
                  if ET_TIME_OPEN<=dt.time()<=ET_TIME_LAST}
 return _rth_memo[key]

def is_complete(bars):
 times={z.strftime("%H:%M") for z in bars}
 return len(bars)>=76 and "09:30" in times and "15:55" in times

def complete_session_dates(cache,sym):
 key=(id(cache),sym)
 if key not in _complete_memo:
  _complete_memo[key]=sorted(d for d in cache[sym] if is_complete(rth(cache,sym,d)))
 return _complete_memo[key]

def preexisting_complete_days(cache, sym, day):
 return bisect_left(complete_session_dates(cache,sym),day)

def eligible_day(cache,sector,day):
 etf,peers=source.SECTOR[sector]
 symbols=(etf,)+peers
 return all(preexisting_complete_days(cache,s,day)>=5
            and is_complete(rth(cache,s,day)) for s in symbols)

def sector_shock_day(cache,sector,day,threshold):
 etf,peers=source.SECTOR[sector]
 er=rth(cache,etf,day)
 prs={sym:rth(cache,sym,day) for sym in peers}
 if not er or not all(prs.values()):return {}
 opens={sym:next(v[0] for z,v in sorted(bars.items()) if z.time()==ET_TIME_OPEN)
        for sym,bars in [(etf,er)]+list(prs.items())}
 earliest={}
 previous=None
 for dt,ohlc in sorted(er.items()):
  close=ohlc[3]
  if previous is None or dt-previous[0]!=timedelta(minutes=5):
   previous=(dt,close)
   continue
  prev_dt,prev_close=previous
  for sign in (+1,-1):
   if sign in earliest:continue
   if not (sign*(close/opens[etf]-1)*100>=threshold and
           sign*(prev_close/opens[etf]-1)*100>=threshold):continue
   breadth=0
   for sym,ps in prs.items():
    if dt not in ps:continue
    breadth+=sign*(ps[dt][3]/opens[sym]-1)*100 >= threshold/4
   minimum=2
   if breadth<minimum:continue
   earliest[sign]={"time":(dt+timedelta(minutes=5)).isoformat(),
                   "bar_start":dt.isoformat(),"mark":close,
                   "etf_from_open_pct":round(100*(close/opens[etf]-1),5),
                   "qualified_peer_count":int(breadth)}
  previous=(dt,close)
 return earliest

def stock_weakness_day(bars,prev_close,threshold=2.5,delta15=1.0,sign=-1):
 ordered=sorted(bars.items())
 first_total=None
 first_both=None
 for i,(dt,v) in enumerate(ordered):
  c=v[3]; pct=sign*100*(c/prev_close-1)
  if pct>=threshold and first_total is None:
   first_total={"time":(dt+timedelta(minutes=5)).isoformat(),"mark":c}
  if i<3 or dt-ordered[i-3][0]!=timedelta(minutes=15):continue
  old=ordered[i-3][1][3]
  # Relative to previous close; -1pp in 15min is included in -2.5% total.
  d15=sign*100*(c-old)/prev_close
  if pct>=threshold and d15>=delta15 and first_both is None:
   first_both={"time":(dt+timedelta(minutes=5)).isoformat(),
               "mark":c,"total_from_previous_close_pct":round(sign*pct,5),
               "last15_change_pp":round(sign*d15,5)}
 return first_total,first_both

def next_prev_close(cache,sym,day):
 prior=complete_session_dates(cache,sym)
 index=bisect_left(prior,day)
 if index==0:return None
 last=rth(cache,sym,prior[index-1])
 return sorted(last.items())[-1][1][3]

def stock_day(cache,sym,day):
 bars=rth(cache,sym,day)
 prev=next_prev_close(cache,sym,day)
 if prev is None or not is_complete(bars):return None
 openpx=next(v[0] for z,v in sorted(bars.items()) if z.time()==ET_TIME_OPEN)
 closepx=sorted(bars.items())[-1][1][3]
 retcc=(closepx/prev-1)*100;retoc=(closepx/openpx-1)*100
 total_down,strict_down=stock_weakness_day(bars,prev,sign=-1)
 total_up,strict_up=stock_weakness_day(bars,prev,sign=+1)
 return {"prev_close":prev,"rth_open":openpx,"rth_close":closepx,
  "close_to_close_pct":round(retcc,5),"open_to_close_pct":round(retoc,5),
  "major_down":retcc<=-5 or retoc<=-5,
  "major_up":retcc>=5 or retoc>=5,
  "stock_down_total_2p5":total_down,"stock_down_overlap_2p5_and_1pp_15m":strict_down,
  "stock_up_total_2p5":total_up,"stock_up_overlap_2p5_and_1pp_15m":strict_up}

def analyze(cache):
 out={"model":"V2 research-only","completed_data_through":"2026-11-06",
 "stock_severe_threshold_pct":5,
 "stock_emergency":"total -2.5% from previous completed RTH close AND >=1pp last 15m (overlapping)",
 "threshold_new_day":THRESHOLDS_NEW,"threshold_old_day":THRESHOLDS_OLD,
 "rows":[],"summary":{}}
 for sector,(etf,peers) in source.SECTOR.items():
  dates=sorted(cache[etf]);count_days=0
  for day in dates:
   if not eligible_day(cache,sector,day):continue
   count_days+=1
   new=sector_shock_day(cache,sector,day,THRESHOLDS_NEW[sector])
   old=sector_shock_day(cache,sector,day,THRESHOLDS_OLD[sector])
   for sym in peers:
    sd=stock_day(cache,sym,day)
    if not sd:continue
    def info(signal,sign):
     if not signal:return None
     barstart=datetime.fromisoformat(signal["bar_start"])
     px=rth(cache,sym,day).get(barstart,(None,None,None,None))[3]
     if px is None:return {"time":signal["time"],"missing_stock_mark":True}
     # For an existing long, selling at alert would avoid future decline.
     remaining=(px-sd["rth_close"])/sd["prev_close"]*100
     return {"time":signal["time"],"etf_price":signal["mark"],
       "stock_price_at_alert":px,
       "stock_change_from_previous_close_at_alert_pct":round((px/sd["prev_close"]-1)*100,5),
       "gross_sell_at_alert_vs_hold_to_close_pp":round(remaining,5),
       "already_down_at_least_5pct":px<=sd["prev_close"]*0.95}
    row={"sector":sector,"symbol":sym,"date":day,
      "new_down":info(new.get(-1),-1),"old_down":info(old.get(-1),-1),
      "new_up":info(new.get(+1),+1),"old_up":info(old.get(+1),+1),**sd}
    out["rows"].append(row)
  sectorrows=[v for v in out["rows"] if v["sector"]==sector]
  ser={}
  for suffix,polarity in (("down","major_down"),("up","major_up")):
   major=[r for r in sectorrows if r[polarity]]
   ser[suffix]={"major_stockdays":len(major),"all_stockdays":len(sectorrows)}
   for label in ("new","old"):
    key=f"{label}_{suffix}"
    signals=[r for r in sectorrows if r[key]]
    detected=[r for r in major if r[key]]
    ser[suffix][label]={
      "alerted_stockdays":len(signals),
      "detected_major":len(detected),"missed_major":len(major)-len(detected),
      "nonmajor_warned":len(signals)-len(detected)}
    if suffix=="down":
     ser[suffix][label].update({
        "major_warned_before_minus_5":sum(not r[key]["already_down_at_least_5pct"] for r in detected if r[key]),
        "major_warned_when_already_minus_5":sum(r[key]["already_down_at_least_5pct"] for r in detected if r[key]),
        "alert_selling_would_avoid_0p3pp_to_close":sum(r[key]["gross_sell_at_alert_vs_hold_to_close_pp"]>0.3 for r in signals if r[key])})
   if suffix=="down":
    for label,key in (("standalone_2p5","stock_down_total_2p5"),
                      ("strict_overlap","stock_down_overlap_2p5_and_1pp_15m")):
     flagged=[r for r in sectorrows if r[key]]
     caught=[r for r in major if r[key]]
     ser[suffix][label]={"alerted_stockdays":len(flagged),"detected_major":len(caught),
        "missed_major":len(major)-len(caught),
        "nonmajor_warned":len(flagged)-len(caught)}
  out["summary"][sector]={"complete_days":count_days,"peer_symbols":list(peers),**ser}
 return out

def main():
 cache=source.load()
 output=analyze(cache)
 p=Path("/tmp/v2_sector_alert_severe_stock_recall_20261109.json")
 p.write_text(json.dumps(output,indent=2)+"\n")
 for s,z in output["summary"].items():
  d=z["down"];up=z["up"]
  print(s,"days",z["complete_days"],"stockdays",d["all_stockdays"],
  "majorDOWN",d["major_stockdays"],"new",d["new"]["detected_major"],"old",d["old"]["detected_major"],
  "strict-stock",d["strict_overlap"]["detected_major"],"majorUP",up["major_stockdays"],
  "new",up["new"]["detected_major"],"old",up["old"]["detected_major"])
 print("TOTAL_AUDIT_STOCKDAYS",len(output["rows"]),p.stat().st_size)
if __name__=="__main__":main()
