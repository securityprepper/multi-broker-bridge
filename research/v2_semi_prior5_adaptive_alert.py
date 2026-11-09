"""V2 RESEARCH ONLY: prior-five completed-session adaptive semiconductor downside alert.
No broker access/orders. Frozen candidate grid, as-of five-minute SIP candles.
"""
from __future__ import annotations
import argparse,json,math
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import mean
from research.v2_semi_emergency_precision import (
   SYMS,PIVOT,parse,prior_price,eligible,latest_close,fifteen_delta,rth_openings)

INPUTS=("/tmp/semis_52wk_5min_sip_adjusted.json",
        "/tmp/semis_peers_52wk_5min_adjusted.json")
CASES={
  "fixed2":("fixed",2.0,0.0),
  "fixed2p5":("fixed",2.5,0.0),
  "fixed3":("fixed",3.0,0.0),
  "prior5_abs0p80_min2":("adaptive",2.0,.8),
  "prior5_abs1p00_min2":("adaptive",2.0,1.0),
  "prior5_abs1p25_min2":("adaptive",2.0,1.25),
  "prior5_abs1p00_min2p5":("adaptive",2.5,1.0)}
MOM15=1.0

def earlier_six_complete_closes(days,decision_day):
    dates=sorted(d for d,r in days.items() if d<decision_day and "15:55" in r)
    return [days[d]["15:55"][2] for d in dates[-6:]] if len(dates)>=6 else None

def prior5_mean_abs_close_pct(days,day):
    closes=earlier_six_complete_closes(days,day)
    if closes is None:return None
    return mean(abs(100*(b/a-1)) for a,b in zip(closes,closes[1:]))

def asof_threshold(case,days,day):
    typ,floor,mult=CASES[case]
    vol=prior5_mean_abs_close_pct(days,day)
    if vol is None:return None
    return floor if typ=="fixed" else max(floor,vol*mult)

def model_signal(ser,sym,day,threshold,openings):
    days=ser[sym]
    old=prior_price(days,day)
    if old is None:return None
    last=latest_close(ser,sym,day,"15:55")
    if last is None:return None
    for hm,row in sorted(days[day].items()):
        t=row[0]
        if not (4<=t.hour<16) or hm=="15:55":continue
        if not eligible(ser,sym,day,hm,old,threshold,MOM15,"soxx_breadth"):continue
        # Candle starting t completes at t+5; next bar starts at t+5.
        alert=t+timedelta(minutes=5)
        nxt=days[day].get(alert.strftime("%H:%M"))
        if nxt is None:continue
        # Following RTH opening is the first >= alert (may be same day's opening
        # after a premarket warning), not evidence available to the live signal.
        fut=[(d,o,p) for d,o,p in openings[sym] if o>=alert]
        if not fut:continue
        next_date,next_at,next_open=fut[0]
        opening=next((p for d,o,p in openings[sym] if d==day),None)
        return {"symbol":sym,"day":day,"at":alert.isoformat(),
           "price":row[2],"close_pct":100*(last/old-1),
           "alert_pct":100*(row[2]/old-1),
           "last15_pctpoints":fifteen_delta(ser,sym,day,hm,old),
           "major":100*(last/old-1)<=-5,
           "before_minus5":100*(row[2]/old-1)>-5,
           "already_gapped_minus5":bool(opening and 100*(opening/old-1)<=-5),
           "next_bar_open":nxt[1],
           "next_regular_open":next_open,"next_open_date":next_date,
           "sell_adv_30bp":100*(nxt[1]-next_open)/old-.30,
           "sell_adv_60bp":100*(nxt[1]-next_open)/old-.60,
           "threshold":threshold}
    return None

def score(rows,total_major):
    n=len(rows)
    days=len({r["day"] for r in rows})
    if not n:return {"alerts":0,"independent_days":0,"major_total":total_major}
    hit=[r for r in rows if r["major"]]
    return {"alerts":n,"independent_days":days,
        "major_hits":len(hit),"major_total":total_major,
        "sensitivity":round(len(hit)/total_major,4) if total_major else None,
        "nonmajor_warnings":n-len(hit),
        "major_before_minus5":sum(x["before_minus5"] for x in hit),
        "major_already_gap_minus5":sum(x["already_gapped_minus5"] for x in hit),
        "model_early_sale_profitable":sum(x["sell_adv_30bp"]>0 for x in rows),
        "modeled_early_sale_precision":round(sum(x["sell_adv_30bp"]>0 for x in rows)/n,4),
        "mean_adv_30bp_pp":round(mean(r["sell_adv_30bp"] for r in rows),4),
        "mean_adv_60bp_pp":round(mean(r["sell_adv_60bp"] for r in rows),4),
        "day_equal_mean_30bp_pp":round(mean(mean(r["sell_adv_30bp"] for r in rows if r["day"]==d)
                                     for d in {r["day"] for r in rows}),4),
        "earliest_major_warning":min((r["at"] for r in hit),default=None)}

def run(input_paths=INPUTS,manifest=None):
    raw={}
    for p in input_paths:raw.update(json.loads(Path(p).read_text()))
    ser=parse(raw)
    if manifest is None:
        manifest=Path("/tmp/v2-run15-sector-precision-work/v2_semis_research_cohort_2026-11-09.json")
    man=json.loads(Path(manifest).read_text())
    eligible={(sym,day) for sym,dates in man["cohort_by_symbol"].items() for day in dates
              if sym in SYMS and prior5_mean_abs_close_pct(ser[sym],day) is not None}
    # The denominator is frozen for ALL candidates; never use a filter's own denominators.
    observed_major={(s,d) for s,d in eligible
                    if latest_close(ser,s,d,"15:55") is not None and
                       100*(latest_close(ser,s,d,"15:55")/prior_price(ser[s],d)-1)<=-5}
    opens={s:rth_openings(ser,s) for s in SYMS}
    outputs={}
    all_events={}
    for case in CASES:
        found=[]
        for s,d in sorted(eligible):
            threshold=asof_threshold(case,ser[s],d)
            if threshold is None:continue
            e=model_signal(ser,s,d,threshold,opens)
            if e:found.append(e)
        summary={}
        for name,select in [("all",lambda day:True),
                            ("earlier",lambda day:day<PIVOT),
                            ("later",lambda day:day>=PIVOT)]:
            subset=[e for e in found if select(e["day"])]
            total=sum(select(d) for s,d in observed_major)
            rows=score(subset,total)
            detected={(e["symbol"],e["day"]) for e in subset if e["major"]}
            missed=sorted((s,d) for s,d in observed_major if select(d) and (s,d) not in detected)
            rows["missed_severe_count"]=len(missed)
            rows["missed_severe_examples"]=missed[:10]
            summary[name]=rows
        outputs[case]=summary
        all_events[case]=found
    return {"input_sources":list(input_paths),"cohort_frozen_stockdays":len(eligible),
        "cohort_major_down_close_close":len(observed_major),
        "prior5_required":True,"momentum_overlap_pp":MOM15,
        "breadth_confirmation":"SOXX -0.5% and >= half other peers -0.5%",
        "cases":outputs,
        "notes":["Prior-five absolute regular-close returns computed using six earlier complete closes only",
                 "No same-day prices in any prior-five threshold calculation",
                 "Later period 2026-09-01 through 2026-11-06 is frozen OOS evaluation",
                 "Simulated next-bar/next-open price proxy not executable bid/ask or broker fills",
                 "No LIVE/PAPER order actions"]},all_events

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True)
    args=ap.parse_args()
    out,events=run()
    Path(args.output).write_text(json.dumps(out,indent=2))
    Path(args.output+".events.json").write_text(json.dumps(events))
    print(json.dumps({k:v["later"] for k,v in out["cases"].items()},indent=2))
