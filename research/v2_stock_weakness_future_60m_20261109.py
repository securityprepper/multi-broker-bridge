"""Post-signal 60m and 13:40 CT follow-through for V2 factual stock weakness.

Research-only. Initial trigger is frozen in the previously timestamped signal
audit; scoring loads future bar only AFTER the signal, never for admission.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, time
import json
from pathlib import Path
import v2_sector_alert_severe_stock_recall_20261109 as core

def score_one(cache,row,trigger):
 if not trigger:return None
 dt=datetime.fromisoformat(trigger["time"])
 # Trigger was completed five-minute candle; available only at its CLOSE.
 start=dt-timedelta(minutes=5)
 chart=core.rth(cache,row["symbol"],row["date"])
 start_bar=chart.get(start)
 if start_bar is None:return {"status":"missing_actual_signal_bar"}
 signal_px=start_bar[3]
 assert abs(signal_px-trigger["mark"])<1e-6
 later=start+timedelta(minutes=60)
 future=chart.get(later) if later+timedelta(minutes=5)<=datetime.combine(
   dt.date(),time(16),tzinfo=dt.tzinfo) else None
 final_bar=None
 for k,v in chart.items():
  if k.time()==time(14,35):final_bar=v
 def outcome(px):
  if px is None:return None
  return round((signal_px-px)/signal_px*100,5)
 signed60=outcome(future[3] if future else None)
 signedflat=outcome(final_bar[3] if final_bar else None) if dt.time()<time(14,40) else None
 return {"trigger_at_ET":dt.isoformat(),"signal_price":signal_px,
         "future_60m_close_at_ET":(later+timedelta(minutes=5)).isoformat() if future else None,
         "future_60m_price":future[3] if future else None,
         "signed_sell_vs_hold_60m_pct":signed60,
         "signed_sell_vs_hold_to1340CT_pct":signedflat,
         "warning_before_entry_cutoff":dt.time()<=time(14,15),
         "outcome_60m_after_30bp_positive":signed60>0.3 if signed60 is not None else None,
         "forward_rebound_over_2pct":signed60<=-2 if signed60 is not None else None}

def aggregate(items):
 events=len(items);observed=[x for x in items if x["outcome_60m"] and
                           x["outcome_60m"]["signed_sell_vs_hold_60m_pct"] is not None]
 ret=[x["outcome_60m"]["signed_sell_vs_hold_60m_pct"] for x in observed]
 return {"alerts":events,"scorable_60m":len(ret),"forward_decline_at_least_0p3pct":sum(x>0.3 for x in ret),
         "forward_decline_any":sum(x>0 for x in ret),
         "forward_rebound_at_least_2pct":sum(x<=-2 for x in ret),
         "mean_signed_sell_vs_hold_60m_before_cost_pct":round(sum(ret)/len(ret),5) if ret else None,
         "after_30bp_mean_pct":round(sum(x-0.3 for x in ret)/len(ret),5) if ret else None}

def main():
 origin=json.loads(Path("/tmp/v2_sector_alert_severe_stock_recall_20261109.json").read_text())
 cache=core.source.load()
 rows=origin["rows"];summary={}
 for sector in core.THRESHOLDS_NEW:
  selected=[r for r in rows if r["sector"]==sector]
  unique_days=sorted(set(r["date"] for r in selected))
  split=unique_days[int(len(unique_days)*0.7)]
  for row in selected:
   row["outcome_60m"]=score_one(cache,row,row.get("stock_down_overlap_2p5_and_1pp_15m"))
  em=[r for r in selected if r["outcome_60m"]]
  summary[sector]={
   "split_first_later_day":split,
   "earlier":aggregate([r for r in em if r["date"]<split]),
   "later":aggregate([r for r in em if r["date"]>=split]),
   "all":aggregate(em),
   "major_down_missing_strict":[
      {"date":r["date"],"symbol":r["symbol"],
       "close_close_pct":r["close_to_close_pct"],
       "rth_open_close_pct":r["open_to_close_pct"],
       "opening_gap_pct":round((r["rth_open"]/r["prev_close"]-1)*100,4),
       "reached_total_2p5":bool(r["stock_down_total_2p5"]),
       "new_sector_shock_before_close":bool(r["new_down"])}
      for r in selected if r["major_down"] and not r["stock_down_overlap_2p5_and_1pp_15m"]]}
 output={"provenance":"52-week SIP adjusted five-minute MARKS, no executable NBBO or fills",
 "owner_sell_trigger":"RTH previous-close -2.5% including last15 -1pp, strict AND",
 "future_baseline":"first completed five-minute signal close (NOT previous close), outcome exactly 60 minutes later",
 "retired_5pct_sector_shock_safety_warning":False,
 "precision_summary":summary,
 "daily_audit":[{"date":r["date"],"sector":r["sector"],"symbol":r["symbol"],
                 "major_down":r["major_down"],"severe_up":r["major_up"],
                 "stock_trigger":r["stock_down_overlap_2p5_and_1pp_15m"],
                 "future60":r["outcome_60m"]}
                for r in rows if r["outcome_60m"]]}
 p=Path("/tmp/v2_stock_weakness_future_60m_20261109.json")
 p.write_text(json.dumps(output,indent=2)+"\n")
 for s,q in summary.items():
  print(s,"earlier",q["earlier"],"later",q["later"],
        "missed_major",len(q["major_down_missing_strict"]))
 print("AUDIT",len(output["daily_audit"]),p.stat().st_size)
if __name__=="__main__":main()
