"""V2-only, read-only directional early-warning, continuation, next-open stress.

Takes frozen train-selected as-of forecast events, not broker accounts.
No commission or bid/ask observations; 30bp proxy is a sensitivity ONLY.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from collections import defaultdict
from statistics import mean

CLOCK_ORDER=("PREV_EVENING","08:30","09:25","10:00","11:00","13:00")
COST_BPS=30

def continuation(row):
    """Percent move from actually observed completed-bar mark to same-day final close.
    Actual close is used ONLY to evaluate after recorded signal, never to generate it.
    """
    mark=row["sector_mark_price"]
    final=row["regular_close_price"]
    if not mark or not final or mark<=0 or final<=0:return None
    side=row["prediction"]
    if side=="ABSTAIN":return None
    direction=1 if side=="UP" else -1
    return direction*100*(final/mark-1)

def hypothetical_sell_advantage(row,friction_bps=COST_BPS):
    """For existing long, sale at as-of mark vs holding to next regular open.
    Positive means early sale HELPED; excludes spread/partial fill latency.
    """
    if row["prediction"]!="DOWN":return None
    nxt=row["next_regular_open"]
    mark=row["sector_mark_price"]
    if not nxt or not mark or mark<=0:return None
    return 100*(mark-nxt)/mark-friction_bps/100

def stats_forecasts(rows):
    issued=[r for r in rows if r["prediction"]!="ABSTAIN"]
    correct=[r for r in issued if r["prediction"]==r["actual"]]
    up=[r for r in issued if r["prediction"]=="UP"]
    down=[r for r in issued if r["prediction"]=="DOWN"]
    move=[continuation(r) for r in issued]
    move=[x for x in move if x is not None]
    sales=[hypothetical_sell_advantage(r) for r in down]
    sales=[x for x in sales if x is not None]
    big=[r for r in rows if r["significant_up"] or r["significant_down"]]
    good_emerg=[r for r in issued if r["emergency"] and (
        (r["prediction"]=="UP" and r["significant_up"]) or
        (r["prediction"]=="DOWN" and r["significant_down"]))]
    bad_emerg=[r for r in issued if r["emergency"] and r not in good_emerg]
    lost=[r for r in rows if (r["significant_up"] and r["prediction"]!="UP")
                            or (r["significant_down"] and r["prediction"]!="DOWN")]
    wrong_major=[{"day":r["day"],"predicted":r["prediction"],
        "actual":r["actual"],"close_pct":r["close_pct"],"checkpoint":r["checkpoint"]}
        for r in lost]
    early=[r for r in good_emerg if abs(r["observed_sector_pct"])<r["severity_threshold_pct"]]
    return {"available_days":len(rows),"issued":len(issued),"correct":len(correct),
        "accuracy":round(len(correct)/len(issued),4) if issued else None,
        "coverage":round(len(issued)/len(rows),4) if rows else 0,
        "up_precision":round(sum(r["actual"]=="UP" for r in up)/len(up),4) if up else None,
        "down_precision":round(sum(r["actual"]=="DOWN" for r in down)/len(down),4) if down else None,
        "significant_days":len(big),
        "significant_direction_missed":len(lost),"first_severe_misses":wrong_major[:8],
        "emergency_true":len(good_emerg),"emergency_false":len(bad_emerg),
        "emergency_pre_severity":len(early),
        "earliest_true_emergency":min((r["bar_available_at"] for r in good_emerg),default=None),
        "post_signal_same_day_continuation_positive":sum(x>0 for x in move),
        "post_signal_same_day_continuation_count":len(move),
        "mean_post_signal_directional_pct":round(mean(move),4) if move else None,
        "sell_better_than_next_open_count":sum(x>0 for x in sales),
        "sell_vs_next_open_count":len(sales),
        "mean_sell_adv_next_open_30bp":round(mean(sales),4) if sales else None}

def evaluate(summary,audit):
    grouped=defaultdict(lambda:defaultdict(dict))
    for row in audit:
        grouped[row["sector"]][row["day"]][row["checkpoint"]]=row
    output={"method":"Select earliest previously TRAIN-qualified forecast on each later historical day; never use holdout to choose rules.",
      "cost_model":"30bp proxy only; not actual quote or fill; no PAPER or LIVE actions",
      "sectors":{}}
    for sector,days in sorted(grouped.items()):
        qualified={clock for clock,x in summary["sectors"][sector]["checkpoint_results"].items()
                   if x.get("policy")=="QUALIFIED"}
        first=[];rev=0;last_wrong_examples=[];checkpoints=defaultdict(list)
        for day,clocks in sorted(days.items()):
            candidates=[clocks[c] for c in CLOCK_ORDER
                if c in qualified and c in clocks and clocks[c]["prediction"]!="ABSTAIN"]
            if candidates:
                r=candidates[0];first.append(r)
                if any(x["prediction"]!=r["prediction"] for x in candidates[1:]):rev+=1
            else:
                # Add no-signal row for this completed sector-day from earliest available clock.
                r=next((clocks[c] for c in CLOCK_ORDER if c in clocks),None)
                if r is None:continue
                first.append({**r,"prediction":"ABSTAIN","emergency":False})
        for c in CLOCK_ORDER:
            if c not in qualified:continue
            sub=[d[c] for d in days.values() if c in d]
            checkpoints[c]=stats_forecasts(sub)
        firststats=stats_forecasts(first)
        firststats["forecast_reversals_on_days_with_signal"]=rev
        firststats["qualified_clocks"]=sorted(qualified,key=CLOCK_ORDER.index)
        firststats["earliest_issued_at"]=min((r["bar_available_at"] for r in first
                if r["prediction"]!="ABSTAIN"),default=None)
        # Separate >=5% semis RTH/prev-close stress, not derived from winner labels.
        if sector=="semiconductors":
            semimajor=[r for r in first if max(r["close_pct"],r["rth_pct"])>=5
                       or min(r["close_pct"],r["rth_pct"])<=-5]
            found=[r for r in semimajor if (r["prediction"]=="UP" and
                      max(r["close_pct"],r["rth_pct"])>=5) or
                    (r["prediction"]=="DOWN" and min(r["close_pct"],r["rth_pct"])<=-5)]
            firststats["semi_5pct_days"]=len(semimajor)
            firststats["semi_5pct_first_direction_correct"]=len(found)
            firststats["semi_5pct_first_missed_or_wrong"]=[
                 r["day"] for r in semimajor if r not in found]
        output["sectors"][sector]={"first_train_qualified_forecast":firststats,
                                  "qualified_checkpoint_outcomes":dict(checkpoints)}
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument("--summary",required=True)
    p.add_argument("--audit",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    data=evaluate(json.loads(Path(a.summary).read_text()),
                  json.loads(Path(a.audit).read_text()))
    Path(a.output).write_text(json.dumps(data,indent=2,sort_keys=True))
    print(json.dumps({s:r["first_train_qualified_forecast"] for s,r in data["sectors"].items()},indent=2))
if __name__=="__main__":main()