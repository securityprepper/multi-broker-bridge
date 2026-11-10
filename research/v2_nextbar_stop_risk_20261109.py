"""V2 research-only next-bar hard-stop/anti-churn risk sensitivity.

Uses an already TRAIN-selected sector policy without changing selection.
Signals come from the as-of completed 5m bar; next-bar entry from a later OPEN.
Stop decision only on a subsequent completed 5m CLOSE, fills modeled at NEXT 5m OPEN.
True bid/ask, spread, partial fills, short borrow and stop slippage NOT available.
No broker orders.
"""
from __future__ import annotations
import json
from datetime import datetime,timedelta
from pathlib import Path
from statistics import mean
from research import v2_next_move_first_7sector_walkforward_20261109 as base
from research.v2_next_move_first_7sector_walkforward_20261109 import FILES,TIMES
def plus_mins(clock,n):
 return (datetime(2000,1,1,*[int(i) for i in clock.split(":")])+timedelta(minutes=n)).strftime("%H:%M")
def replay_one(cache,sector,trade,stop_pct=2.5,round_trip_cost=.30):
 """Fixed holding ends at 14:40 ET; stop can't execute before next completed bar."""
 etf,peers=FILES[sector]
 day=trade["day"]
 bars=cache[etf].get(day,{})
 signal=trade["clock"]
 side=1 if trade["side"]=="UP" else -1
 entry_clock=plus_mins(signal,5)
 entry=bars.get(entry_clock,(None,))[0]
 if entry is None:return {"data_available":False,"reason":"entry bar missing"}
 ticks=[(clock,bars[clock]) for clock in sorted(bars)
        if entry_clock<=clock<="14:35"]
 if not ticks or "14:35" not in bars:
  return {"data_available":False,"reason":"required hard-flat bar missing"}
 worst_excursion=0.0
 best_excursion=0.0
 for k,bar in ticks:
  o,h,l,c=bar
  worst_price=l if side==1 else h
  best_price=h if side==1 else l
  adverse=side*100*(worst_price/entry-1)
  favorable=side*100*(best_price/entry-1)
  worst_excursion=min(worst_excursion,adverse)
  best_excursion=max(best_excursion,favorable)
 close_at_flat=bars["14:35"][3]
 base_net=side*100*(close_at_flat/entry-1)-round_trip_cost
 triggered=None
 # The candle's LOW/HIGH is outcome-only, not used to trigger synthetic close stops.
 for i,(t,candle) in enumerate(ticks):
  if t>="14:35":break
  signed_close=side*100*(candle[3]/entry-1)
  if signed_close>-stop_pct:continue
  next_t=plus_mins(t,5)
  next_bar=bars.get(next_t)
  if next_bar is None or next_t>"14:35":
   return {"data_available":False,"reason":"missing next-open after stop decision"}
  px=next_bar[0]
  triggered={"decision_bar_start":t,"execute_next_bar_start":next_t,"executed_proxy":px}
  break
 px=triggered["executed_proxy"] if triggered else close_at_flat
 stopped_net=side*100*(px/entry-1)-round_trip_cost
 return {"data_available":True,"entry_proxy":entry,"stop_touched":triggered is not None,
         "stop_event":triggered,"flat_1340_CT_net_pct":round(base_net,5),
         "nextbar_stop_net_pct":round(stopped_net,5),
         "max_adverse_pct":round(worst_excursion,5),
         "max_favorable_pct":round(best_excursion,5),
         "exit_proxy":px}
def evaluate_all(cache,selected,sector):
 trades=[]
 for x in selected:
  for stop in (1.5,2.5,4.0):
   record=replay_one(cache,sector,x,stop)
   if record["data_available"]:trades.append({"day":x["day"],"stop":stop,**record})
 by={}
 for stop in (1.5,2.5,4.0):
  rows=[x for x in trades if x["stop"]==stop]
  if not rows:
   by[str(stop)]={"complete_replays":0};continue
  p=[x["nextbar_stop_net_pct"] for x in rows]
  q=[x["flat_1340_CT_net_pct"] for x in rows]
  by[str(stop)]={
   "complete_replays":len(rows),"stops_triggered":sum(x["stop_touched"] for x in rows),
   "mean_net_pct":round(mean(p),4),"win_count":sum(z>0 for z in p),
   "hold_mean_net_pct":round(mean(q),4),"hold_win_count":sum(z>0 for z in q),
   "paired_mean_stop_minus_hold_pp":round(mean(x-y for x,y in zip(p,q)),4),
   "worst_stop_net_pct":round(min(p),4),
   "worst_hold_net_pct":round(min(q),4),
   "max_intrahold_adverse_pct":round(min(x["max_adverse_pct"] for x in rows),4),
   "max_intrahold_favorable_pct":round(max(x["max_favorable_pct"] for x in rows),4),
   "stopped_but_hold_would_profit":sum(x["stop_touched"] and x["flat_1340_CT_net_pct"]>0 for x in rows),
   "stopped_and_avoided_worse_flat":sum(x["stop_touched"] and
                                       x["nextbar_stop_net_pct"]>x["flat_1340_CT_net_pct"] for x in rows)
   }
 return by
def main():
 cache=base.load()
 src=json.loads(Path("/tmp/v2_next_move_first_7sector_walkforward_20261109.json").read_text())
 out={}
 for sector in FILES:
  plan=src[sector].get("best_training_shadow")
  if not plan:continue
  # Later dates only! Also calculate risk on SAME frozen candidate for earlier period.
  earlier_rows=base.make_rows(cache,sector)
  split=int(.7*len(earlier_rows))
  policy=tuple(plan["policy"])
  a,_,_=base.evaluate(earlier_rows[:split],sector,policy)
  b,_,_=base.evaluate(earlier_rows[split:],sector,policy)
  # annotate direction for replay without looking at any outcome
  sign="UP" if policy[-1]==1 else "DOWN"
  for x in a+b:x["side"]=sign
  out[sector]={"policy":policy,"earlier":evaluate_all(cache,a,sector),
               "later":evaluate_all(cache,b,sector)}
  z=out[sector]["later"]["2.5"]
  print(sector,"later",z)
 path=Path("/tmp/v2_nextbar_stop_risk_20261109.json")
 path.write_text(json.dumps(out,indent=2)+"\n")
 print("RESULTS",path)
if __name__=="__main__":main()
