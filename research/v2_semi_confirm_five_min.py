"""Research-only as-of continuation after the first semiconductor weak warning.

No broker execution. The owner overlap condition stays -2.5% TOTAL
INCLUDING -1.0 percentage point in the preceding 15 minutes.
"""
from __future__ import annotations
import json,argparse
from pathlib import Path
from datetime import datetime,timedelta,time
from collections import defaultdict
from statistics import mean
from research import v2_semi_emergency_precision as b
from research import v2_semi_postalert_followthrough as priorstudy

SPLIT="2026-09-01"
GATES=("stock","stock_sector")
DELAYS=(5,10)
EXTRA_WEAKNESS=(0.00,.10,.25)
STOCKDAYS=priorstudy.MANIFEST

def eligible_confirm(event,ser,delay,minimum,gate):
    """Only completed bar closes visible by confirmation instant."""
    t0=datetime.fromisoformat(event["alert_at"])
    tc=t0+timedelta(minutes=delay)
    sym=event["sym"];day=event["day"]
    if tc.date().isoformat()!=day:return None
    # Completed bar starts five minutes before confirmation instant.
    hm=(tc-timedelta(minutes=5)).strftime("%H:%M")
    initial_hm=(t0-timedelta(minutes=5)).strftime("%H:%M")
    cur=b.latest_close(ser,sym,day,hm)
    first=b.latest_close(ser,sym,day,initial_hm)
    prev=b.prior_price(ser[sym],day)
    if cur is None or first is None or prev is None:return None
    delta=100*(cur-first)/prev
    if delta> -minimum:return None
    if gate=="stock_sector":
        sox=b.latest_close(ser,"SOXX",day,hm)
        old=b.latest_close(ser,"SOXX",day,initial_hm)
        psox=b.prior_price(ser["SOXX"],day)
        if sox is None or old is None or psox is None:return None
        if 100*(sox-old)/psox> -minimum:return None
    elif gate!="stock":raise ValueError(gate)
    # Conservative 5-minute latency AFTER verification, not zero-time fill.
    entrytime=tc+timedelta(minutes=5)
    bar=ser[sym].get(day,{}).get(entrytime.strftime("%H:%M"))
    if bar is None or entrytime.date().isoformat()!=day:return None
    entry=bar[1]
    if entry<=0:return None
    # Select next regular opening in time order, not an earlier session open.
    nxt=next(((d,t,p) for d,t,p in b.rth_openings(ser,sym) if t>entrytime),None)
    if nxt is None:return None
    later_day,regular_at,regular_px=nxt
    after=100*(entry-regular_px)/prev-.30
    major_before=100*(cur/prev-1)>-5
    return {"symbol":sym,"day":day,"original_alert":event["alert_at"],
       "confirmation_time":tc.isoformat(),
       "extra_weakness_pp":round(delta,4),"gate":gate,"delay_minutes":delay,
       "threshold":minimum,"entry_time":entrytime.isoformat(),
       "entry_price_mark":entry,
       "next_regular_open":regular_px,
       "next_regular_open_at":regular_at.isoformat(),
       "sell_advantage_next_open_30bp":round(after,5),
       "major":event["major"],
       "already_minus5_at_confirm":not major_before,
       "original_total_pct":event["total_pct"],
       "original_15m_pp":event["last15_pp"]}

def stats(rows,major_total):
    n=len(rows);hit=[x for x in rows if x["major"]]
    return {"alerts":n,"days":len({x["day"] for x in rows}),
      "major_hits":len(hit),"major_total":major_total,
      "severe_coverage_pct":round(len(hit)/major_total*100,2) if major_total else None,
      "nonmajor_warnings":n-len(hit),
      "major_before_already_minus5":sum(not x["already_minus5_at_confirm"] for x in hit),
      "sell_beneficial_count":sum(x["sell_advantage_next_open_30bp"]>0 for x in rows),
      "sell_beneficial_pct":round(sum(x["sell_advantage_next_open_30bp"]>0 for x in rows)/n*100,2) if n else None,
      "mean_next_open_sell_adv_pp":round(mean(x["sell_advantage_next_open_30bp"] for x in rows),4) if n else None,
      "earliest_major_warning":min((x["confirmation_time"] for x in hit),default=None),
      "missed_severe":major_total-len(hit)}

def build(data_paths=priorstudy.INPUTS,manifest=STOCKDAYS):
    ser={}
    for path in data_paths:ser.update(json.loads(Path(path).read_text()))
    ss=b.parse(ser)
    eligible=priorstudy.scored_eligible(ss,manifest)
    majors={(sym,day) for sym,day in eligible if 100*(ss[sym][day]["15:55"][2]/b.prior_price(ss[sym],day)-1)<=-5}
    initial=[ev for ev in b.first_signals(ss,2.5,1.0,"soxx_breadth")
           if (ev["sym"],ev["day"]) in eligible]
    allrows={};out={}
    for delay in DELAYS:
      for threshold in EXTRA_WEAKNESS:
       for gate in GATES:
        key=f"{gate}_delay{delay}_extra{threshold:.2f}"
        data=[x for ev in initial if
             (x:=eligible_confirm(ev,ss,delay,threshold,gate)) is not None]
        allrows[key]=data
        periods={}
        for per,check in (("earlier",lambda d:d<SPLIT),
                          ("later",lambda d:d>=SPLIT)):
            e=[x for x in data if check(x["day"])]
            tar=sum(check(d) for _,d in majors)
            periods[per]=stats(e,tar)
        out[key]=periods
    base={}
    for per,check in (("earlier",lambda d:d<SPLIT),("later",lambda d:d>=SPLIT)):
        ev=[e for e in initial if check(e["day"])]
        target=sum(check(d) for _,d in majors)
        base[per]={"major_total":target,"alerts":len(ev),
           "major_hits":sum(e["major"] for e in ev),
           "nonmajor":sum(not e["major"] for e in ev),
           "mean_next_open_sell_adv_pp":round(mean(e["benefit_vs_open_30bp"] for e in ev),4) if ev else None,
           "positive_sell_pct":round(100*sum(e["benefit_vs_open_30bp"]>0 for e in ev)/len(ev),2) if ev else None}
    return {"total_stockdays":len(eligible),"major_down":len(majors),
      "cohort":"previous close-to-close <=-5%, strictly prior-five-complete-history eligible",
      "owner_overlap_rule":"-2.5% TOTAL including -1.0pp over last 15min, SOXX/peers confirmed",
      "original_alerts":base,"cases":out,
      "disclaimers":["Confirmation is new as-of 5m bar(s), not an outcome label or retrospective condition.",
         "A further 5min execution latency is imposed after confirmation.",
         "This is a counterfactual EXIT vs next regular opening, not actual broker selling.",
         "Market bar OPEN marks are not NBBO bids/asks, BOATS prints or guaranteed fills.",
         "Failure to confirm is NOT permission to remove urgent WATCH or real protective exits.",
         "Original first_signals eligibility includes same-day close only for outcome audit/cohort, never alert conditions.",
         "All V1 PAPER/LIVE timers/orders, IBKR execution and broker safeguards untouched."]},allrows

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);args=p.parse_args()
    r,rows=build()
    Path(args.output).write_text(json.dumps(r,indent=2))
    Path(args.output+".events.json").write_text(json.dumps(rows))
    print(json.dumps({"stockdays":r["total_stockdays"],"severe":r["major_down"],
       "original":r["original_alerts"],"later":{k:v["later"] for k,v in r["cases"].items()}},indent=2))
if __name__=="__main__":main()
