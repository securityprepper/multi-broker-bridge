"""V2 offline selected-direction FORECAST replay: all completed historical sessions.

Policies are frozen from the earlier portion; this is descriptive diagnostic
replay, not independent accuracy validation, not trading authorization.
"""
from __future__ import annotations
import argparse,json,importlib.util
from pathlib import Path
from collections import defaultdict
from statistics import mean

ROOT=Path(__file__).parent
def import_file(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod
d=import_file("v2_dir","v2_direction_walkforward_20261109.py")
f=import_file("v2_follow","v2_direction_followthrough_20261109.py")
CLOCK_ORDER=d.CLOCKS

def choose_first(rows):
    byday=defaultdict(dict)
    for r in rows:byday[r["day"]][r["checkpoint"]]=r
    out=[]
    for day,clocks in sorted(byday.items()):
        chosen=next((clocks[c] for c in CLOCK_ORDER
                     if c in clocks and clocks[c]["prediction"]!="ABSTAIN"),None)
        if chosen is not None:out.append(chosen)
        else:
            earliest=next((clocks[c] for c in CLOCK_ORDER if c in clocks),None)
            if earliest:out.append({**earliest,"prediction":"ABSTAIN","emergency":False})
    return out

def severe_label(r,sector):
    if sector=="semiconductors":
        up=max(r["close_pct"],r["rth_pct"])>=5
        down=min(r["close_pct"],r["rth_pct"])<=-5
    else:
        up=r["significant_up"];down=r["significant_down"]
    return up,down

def analyze_sector(sector,summary):
    selected=summary["sectors"][sector]["checkpoint_results"]
    qualified=[(clock,v["rule"],v["threshold_pct"])
       for clock,v in selected.items() if v.get("policy")=="QUALIFIED"]
    if not qualified:return {"status":"NO_TRAINING_QUALIFIED_RULE"}
    cache=d.load_sector(sector)
    chosen=[]
    for clock,rule,thr in qualified:
        chosen.extend(d.all_rows(sector,clock,rule,thr,cache))
    first=choose_first(chosen)
    big_up=[];big_down=[];first_correct_up=[];first_correct_down=[]
    miss=[];too_late=[];preopen=[];prev_evening=[]
    for r in first:
        up,down=severe_label(r,sector)
        if up:big_up.append(r)
        if down:big_down.append(r)
        if not (up or down):continue
        okay=(up and r["prediction"]=="UP") or (down and r["prediction"]=="DOWN")
        if okay:
            (first_correct_up if up else first_correct_down).append(r)
            if r["checkpoint"] in ("PREV_EVENING","08:30","09:25"):
                preopen.append(r)
            if r["checkpoint"]=="PREV_EVENING":prev_evening.append(r)
            if abs(r["observed_sector_pct"])>=(5 if sector=="semiconductors"
                        else r["severity_threshold_pct"]):too_late.append(r)
        else:
            miss.append({"day":r["day"],"predicted":r["prediction"],
               "realized_close_pct":r["close_pct"],"rth_pct":r["rth_pct"],
               "earliest_qualifying_checkpoint":r["checkpoint"]})
    down_sells=[f.hypothetical_sell_advantage(r) for r in first_correct_down]
    down_sells=[x for x in down_sells if x is not None]
    upside_remaining=[f.continuation(r) for r in first_correct_up]
    upside_remaining=[x for x in upside_remaining if x is not None]
    # First forecast here is only the first train-qualified checkpoint; it is
    # not equivalent to a true preceding-evening warning if no such rule qualifies.
    return {"complete_days":len(first),
      "major_up_days":len(big_up),"major_down_days":len(big_down),
      "major_up_first_correct":len(first_correct_up),
      "major_down_first_correct":len(first_correct_down),
      "major_warning_preopen":len(preopen),"major_warning_previous_evening":len(prev_evening),
      "major_warning_after_already_beyond_severity":len(too_late),
      "missed_major_day_count":len(miss),"sample_misses":miss[:12],
      "earliest_major_down_correct_et":min((r["bar_available_at"] for r in first_correct_down),default=None),
      "earliest_major_up_correct_et":min((r["bar_available_at"] for r in first_correct_up),default=None),
      "severe_down_early_sell_benefit_vs_next_open_30bp":round(mean(down_sells),4) if down_sells else None,
      "severe_down_early_sell_positive":sum(x>0 for x in down_sells),
      "severe_down_early_sell_comparisons":len(down_sells),
      "severe_up_remaining_move_mean_pct":round(mean(upside_remaining),4) if upside_remaining else None,
      "qualified_clocks":[c for c,_,_ in qualified],
      "nov2_2026":next(({"checkpoint":r["checkpoint"],"forecast":r["prediction"],
            "actual":r["actual"],"observed_sector_pct":r["observed_sector_pct"],
            "sector_close_pct":r["close_pct"],"bar_available_at":r["bar_available_at"]}
           for r in first if r["day"]=="2026-11-02"),None)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--summary",required=True)
    ap.add_argument("--output",required=True);a=ap.parse_args()
    summary=json.loads(Path(a.summary).read_text())
    result={"qualifier":"Training-only frozen candidate selection; full sample is descriptive not OOS.",
       "no_broker_orders":True,"sectors":{}}
    for sector in d.SECTORS:
        result["sectors"][sector]=analyze_sector(sector,summary)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()