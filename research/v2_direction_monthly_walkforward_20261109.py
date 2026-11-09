"""V2 research ONLY: monthly rolling walk-forward sector-direction accuracy.
Frozen each month using strictly EARLIER completed days; no future data in signals.
No broker actions, news/futures synchronization, or executable quote evidence.
"""
from __future__ import annotations
import argparse,json,importlib.util
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location("direction",ROOT/"v2_direction_walkforward_20261109.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
CLOCKS=("08:30","09:25","10:00","11:00","13:00")
# Preceding evening examined but not promoted based on unreliable train observations.
MONTHS=tuple(f"2026-{m:02d}-01" for m in range(4,12))

def first_monthly_forecasts(days,selected,rows_by_policy):
    """One time-stamped forecast per day. No lookahead or after-close fallback."""
    out=[];times=defaultdict(int)
    for day in days:
        chosen=None;representative=None
        for clock in CLOCKS:
            policy=selected.get(clock)
            if not policy:continue
            item=rows_by_policy[policy].get(day)
            if item is None:continue
            if representative is None:representative=item
            if item["prediction"]!="ABSTAIN":
                chosen=item;times[clock]+=1;break
        if chosen:out.append(chosen)
        else:
            # Do not silently discard months/dates lacking any trained policy:
            # preserve denominator as an explicit ABSTAIN when reference features exist.
            if representative is None:
                representative=rows_by_policy.get(("10:00","etf",.10),{}).get(day)
            if representative is None:
                representative=next((table[day] for table in rows_by_policy.values()
                    if day in table),None)
            if representative:
                out.append({**representative,"prediction":"ABSTAIN","emergency":False})
    return out,dict(times)

def train_choice(rows_by_policy,clock,month):
    eligible=[]
    for (cl,rule,thr),byday in rows_by_policy.items():
        if cl!=clock:continue
        prior=[r for day,r in byday.items() if day<month]
        if len(prior)<80:continue
        sc=d.score(prior)
        if d.is_eligible(sc):
            eligible.append(((cl,rule,thr),sc))
    return (sorted(eligible,key=lambda kv:(-(kv[1]["balanced_recall"] or 0),
             -kv[1]["coverage"],-kv[1]["accuracy"],kv[0]))[0][0]
            if eligible else None)

def evaluate_sector(sector):
    cache=d.load_sector(sector);etf=cache[0][0]
    all_dates=sorted({date for s,date in cache[2] if s==etf and date>="2026-04-01"
                      and all((sym,date) in cache[2] and (sym,date) in cache[3]
                        and (sym,date) in cache[4] for sym in cache[0])})
    rows_by_policy={}
    for clock in CLOCKS:
        for rule in d.RULES:
            for thr in d.THRESHOLDS:
                rows=d.all_rows(sector,clock,rule,thr,cache)
                rows_by_policy[(clock,rule,thr)]={r["day"]:r for r in rows}
    months={};all_oos=[];earliest=defaultdict(int)
    for ix,month in enumerate(MONTHS):
        nxt=MONTHS[ix+1] if ix+1<len(MONTHS) else "2026-12-01"
        testdays=[day for day in all_dates if month<=day<nxt]
        if not testdays:continue
        selected={clock:train_choice(rows_by_policy,clock,month) for clock in CLOCKS}
        selected={clock:p for clock,p in selected.items() if p is not None}
        rows,times=first_monthly_forecasts(testdays,selected,rows_by_policy)
        sc=d.score(rows)
        months[month[:7]]={"days":len(testdays),"scored_days":sc["days"],
           "issued":sc["issued"],"accuracy":sc["accuracy"],"coverage":sc["coverage"],
           "up_precision":sc["up_precision"],"down_precision":sc["down_precision"],
           "correct":sc["correct"],"wrong":sc["wrong"],
           "earliest_checkpoint_counts":times,"qualified_policies":
            {c:{"rule":p[1],"threshold":p[2]} for c,p in selected.items()}}
        all_oos+=rows
        for c,n in times.items():earliest[c]+=n
    total=d.score(all_oos)
    emergency=[r for r in all_oos if r["emergency"]]
    true=[r for r in emergency if (r["prediction"]=="UP" and r["significant_up"])
                              or (r["prediction"]=="DOWN" and r["significant_down"])]
    severe=[r for r in all_oos if r["significant_up"] or r["significant_down"]]
    late=[r for r in true if abs(r["observed_sector_pct"])>=r["severity_threshold_pct"]]
    total.update({"emergency_signals":len(emergency),"emergency_true":len(true),
      "emergency_false":len(emergency)-len(true),
      "significant_session_days":len(severe),
      "significant_day_first_correct":sum((r["prediction"]=="UP" and r["significant_up"])
                              or (r["prediction"]=="DOWN" and r["significant_down"]) for r in severe),
      "emergency_already_severe":len(late),
      "earliest_severe_warning_et":min((r["bar_available_at"] for r in true),default=None),
      "prediction_times":dict(earliest)})
    return {"rolling_oos":total,"by_month":months,
            "source_days":len(all_dates),"qualified_months":sum(bool(v["qualified_policies"]) for v in months.values())}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True)
    a=p.parse_args()
    report={"selection":"At each calendar month 2026-04 through 2026-11 select only from prior completed sessions, then score that month.",
       "strict_asof":True,"broker_operations":False,"sectors":{}}
    for sector in d.SECTORS:
        report["sectors"][sector]=evaluate_sector(sector)
    Path(a.output).write_text(json.dumps(report,indent=2,sort_keys=True))
    print(json.dumps({s:v["rolling_oos"] for s,v in report["sectors"].items()},indent=2))
if __name__=="__main__":main()