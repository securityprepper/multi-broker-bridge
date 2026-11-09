"""Research-only semiconductor downside: what happens AFTER a causal warning?
Uses actual completed split-adjusted 5m SIP bars. No orders.
Compare stronger last-15m threshold 1/1.5/2pp with 2/2.5/3% total overlap.
"""
from __future__ import annotations
import json,argparse
from pathlib import Path
from datetime import datetime,timedelta,time
from collections import defaultdict
from statistics import mean
from research import v2_semi_emergency_precision as base
INPUTS=("/tmp/semis_52wk_5min_sip_adjusted.json",
        "/tmp/semis_peers_52wk_5min_adjusted.json")
MANIFEST="/tmp/v2-run15-sector-precision-work/v2_semis_research_cohort_2026-11-09.json"
TOTALS=(2.,2.5,3.)
MOMENTUM=(1.,1.5,2.)
SPLIT="2026-09-01"

def scored_eligible(ser,manifest):
    man=json.loads(Path(manifest).read_text())
    result=set()
    for sym,dates in man["cohort_by_symbol"].items():
        if sym not in base.SYMS:continue
        for d in dates:
            earlier=sorted(x for x in ser[sym] if x<d and "15:55" in ser[sym][x])
            if len(earlier)>=6 and d in ser[sym] and "15:55" in ser[sym][d]:
                result.add((sym,d))
    return result

def forward_price(ser,ev,mins):
    at=datetime.fromisoformat(ev["alert_at"])+timedelta(minutes=mins)
    day=at.date().isoformat()
    row=ser[ev["sym"]].get(day,{}).get(at.strftime("%H:%M"))
    # Mark is bar OPEN at target start, cannot be used as signal input.
    return row[1] if row and day==ev["day"] else None

def add_outcomes(ev,ser):
    r=dict(ev)
    for minutes in (30,60):
        future=forward_price(ser,ev,minutes)
        key="next"+str(minutes)
        r[key+"_open"]=future
        r[key+"_drop_pct"]=(100*(1-future/ev["sell_proxy"]) if future else None)
        r[key+"_early_sale_after30bp"]=(100*(1-future/ev["sell_proxy"])-.30 if future else None)
    return r

def classify(e):
    # This is a pure, as-of filter; NO future outcome keys enter.
    return (e["total_pct"],e["last15_pp"],e["alert_at"])

def score(rows,universe_major):
    hit=[x for x in rows if x["major"]]
    n=len(rows);scored=[x for x in rows if x["next30_early_sale_after30bp"] is not None]
    wins=[x for x in scored if x["next30_early_sale_after30bp"]>0]
    return {"alerts":n,"independent_days":len({x["day"] for x in rows}),
      "major_hits":len(hit),"major_total":universe_major,
      "sensitivity":round(len(hit)/universe_major,4) if universe_major else None,
      "nonmajor_warnings":n-len(hit),
      "major_before_minus5":sum(x["before_5"] for x in hit),
      "major_gap_already":sum(x["gap_already"] for x in hit),
      "30min_mark_available":len(scored),
      "30min_continues_down_ge1pp":sum(x["next30_drop_pct"]>=1 for x in scored),
      "30min_early_sale_positive":len(wins),
      "30min_sale_benefit_rate":round(len(wins)/len(scored),4) if scored else None,
      "30min_sale_mean_pp":round(mean(x["next30_early_sale_after30bp"] for x in scored),4) if scored else None,
      "early_sell_vs_next_regular_open_rate":round(sum(x["benefit_vs_open_30bp"]>0 for x in rows)/n,4) if n else None,
      "early_sell_vs_next_regular_open_mean_pp":round(mean(x["benefit_vs_open_30bp"] for x in rows),4) if n else None,
      "earliest_major_warning":min((x["alert_at"] for x in hit),default=None)}

def run(inputs=INPUTS,manifest=MANIFEST):
    parts={}
    for p in inputs:parts.update(json.loads(Path(p).read_text()))
    ser=base.parse(parts)
    eligible=scored_eligible(ser,manifest)
    majors={(s,d) for s,d in eligible if 100*(ser[s][d]["15:55"][2]/base.prior_price(ser[s],d)-1)<=-5}
    result={};all_events={}
    for total in TOTALS:
        for momentum in MOMENTUM:
            k=f"total{total:g}_15m{momentum:g}"
            events=[add_outcomes(x,ser) for x in base.first_signals(ser,total,momentum,"soxx_breadth")
                    if (x["sym"],x["day"]) in eligible]
            all_events[k]=events
            s={}
            for period,ok in (("earlier",lambda d:d<SPLIT),("later",lambda d:d>=SPLIT),("all",lambda d:True)):
                group=[e for e in events if ok(e["day"])]
                target={(sym,day) for sym,day in majors if ok(day)}
                stats=score(group,len(target))
                detected={(e["sym"],e["day"]) for e in group if e["major"]}
                stats["missed_major_count"]=len(target-detected)
                stats["missed_major_first_12"]=sorted(target-detected)[:12]
                stats["pre_regular_open_major_warnings"]=sum(e["major"] and datetime.fromisoformat(e["alert_at"]).time()<time(9,30) for e in group)
                s[period]=stats
            result[k]=s
    return {"stock_days":len(eligible),"major_declines":len(majors),
      "positive_and_nontrigger_days_in_denominator":True,
      "earlier_later_cutoff":SPLIT,
      "settings":{"total":TOTALS,"last15":MOMENTUM,"overlap_not_additive":True,
       "breadth":"SOXX and at least half peers weak"},
      "cases":result,
      "notes":["Historical 5m SIP bar OPEN price marks not executable quotes or fills.",
               "30m forward outcome is post-warning evaluation only; never live input.",
               "Missing exact future 30m bar is excluded from 30m percentage, never counted as winner.",
               "RTH open after first alert may be same-day if preopen; subsequent day otherwise.",
               "Premarket data only 04:00 onward; cannot answer preceding-evening protection.",
               "No V1 PAPER/LIVE modifications or broker orders."]},all_events

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    results,events=run()
    Path(a.output).write_text(json.dumps(results,indent=2,sort_keys=True))
    Path(a.output+".events.json").write_text(json.dumps(events,indent=0))
    print(json.dumps({"stock_days":results["stock_days"],"major":results["major_declines"],
      "later":{k:v["later"] for k,v in results["cases"].items()}},indent=2))
if __name__=="__main__":main()
