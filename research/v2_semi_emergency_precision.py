"""V2 research-only: 2.0/2.5/3.0% overlapping weakness stress across 52-week SIP 5m bars.

Uses only COMPLETED bars and the previous RTH session close at alert time.
Signal definitions and evaluation timestamps are separate. No broker orders.
"""
from __future__ import annotations
import json,sys,math
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ET=ZoneInfo("America/New_York")
SYMS=("AMD","MU","SNDK","SOXX","NVDA","AVGO","WDC","TSM","INTC")
PIVOT="2026-09-01"
def parse(parts):
    series={}
    for symbol,rows in parts.items():
        daily=defaultdict(dict)
        for t,v in rows.items():
            loc=datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(ET)
            if not (0<=loc.hour<24):continue
            if loc.weekday()>=5:continue
            daily[loc.date().isoformat()][loc.strftime("%H:%M")]=(loc,float(v[0]),float(v[3]))
        series[symbol]=dict(daily)
    return series

def prior_price(days,day):
    history=[d for d in sorted(days) if d<day and "15:55" in days[d]]
    return days[history[-1]]["15:55"][2] if history else None

def latest_close(ser,sym,day,hm):
    tup=ser.get(sym,{}).get(day,{}).get(hm)
    return tup[2] if tup else None

def fifteen_delta(ser,sym,day,hm,prior):
    row=ser[sym][day][hm]
    tm=(row[0]-timedelta(minutes=15)).strftime("%H:%M")
    before=latest_close(ser,sym,day,tm)
    return None if before is None else 100*(row[2]-before)/prior

def eligible(ser,sym,day,hm,prior,total,min_last15,confirmation="none"):
    px=latest_close(ser,sym,day,hm)
    if px is None or px>prior*(1-total/100):return False
    m=fifteen_delta(ser,sym,day,hm,prior)
    if m is None or m> -min_last15:return False
    if confirmation=="none":return True
    soxx=latest_close(ser,"SOXX",day,hm)
    psoxx=prior_price(ser["SOXX"],day)
    if soxx is None or psoxx is None or 100*(soxx/psoxx-1)>-.5:return False
    if confirmation=="soxx":return True
    peers=[x for x in SYMS if x not in (sym,"SOXX")]
    deltas=[]
    for x in peers:
        p=prior_price(ser[x],day);cur=latest_close(ser,x,day,hm)
        if p is None or cur is None:return False
        deltas.append(100*(cur/p-1))
    return sum(v<=-.5 for v in deltas)>=math.ceil(len(peers)/2)

def rth_openings(ser,sym):
    return sorted((day,rows["09:30"][0],rows["09:30"][1]) for day,rows in ser[sym].items() if "09:30" in rows)

def first_signals(ser,threshold,momentum,confirmation):
    found=[]
    opens={sym:rth_openings(ser,sym) for sym in SYMS}
    for sym in SYMS:
        days=ser[sym]
        for day in sorted(days):
            previous=prior_price(days,day)
            curclose=latest_close(ser,sym,day,"15:55")
            if previous is None or curclose is None:continue
            major=100*(curclose/previous-1)<=-5.
            for hm,row in sorted(days[day].items()):
                loc=row[0]
                if not ((loc.hour>=4 and loc.hour<16) or (loc.hour==15 and loc.minute<=50)):continue
                if hm=="15:55":continue
                if not eligible(ser,sym,day,hm,previous,threshold,momentum,confirmation):continue
                alert=row[0]+timedelta(minutes=5)
                # At a completed bar, only the NEXT five-minute opening is a proxy.
                next_time=(row[0]+timedelta(minutes=5)).strftime("%H:%M")
                nxt=days[day].get(next_time)
                if nxt is None:continue
                future=[(d,t,p) for d,t,p in opens[sym] if t>=alert and d>=day]
                if not future:continue
                open_day,open_time,open_px=future[0]
                gap_prior=next((p for d,t,p in opens[sym] if d==day),None)
                # A warning on a day that already gapped -5% cannot prevent the overnight gap.
                gap_already=gap_prior is not None and 100*(gap_prior/previous-1)<=-5
                before5=100*(row[2]/previous-1)>-5
                sell_px=nxt[1]
                # Holding until the subsequent regular opening, with 30bp total modeled friction.
                benefit=100*(sell_px-open_px)/previous-.30
                found.append({"sym":sym,"day":day,"alert_at":alert.isoformat(),
                   "price_at_signal":row[2],"sell_proxy":sell_px,
                   "next_regular_open_at":open_time.isoformat(),"next_regular_open":open_px,
                   "close_pct":round(100*(curclose/previous-1),4),
                   "total_pct":round(100*(row[2]/previous-1),4),
                   "last15_pp":round(fifteen_delta(ser,sym,day,hm,previous),4),
                   "major":major,"before_5":before5,
                   "gap_already":gap_already,"benefit_vs_open_30bp":round(benefit,5),
                   "benefit_vs_open_60bp":round(benefit-.30,5)})
                break
    return found

def summarize(events,eligible_severe):
    n=len(events);hits=[x for x in events if x["major"]];others=[x for x in events if not x["major"]]
    winners=[x for x in events if x["benefit_vs_open_30bp"]>0]
    means=lambda arr:round(sum(arr)/len(arr),4) if arr else None
    return {"alerts":n,"major_hits":len(hits),"major_coverage":round(len(hits)/eligible_severe,4) if eligible_severe else None,
      "nonmajor_warnings":len(others),"major_before_5":sum(x["before_5"] for x in hits),
      "major_gap_already":sum(x["gap_already"] for x in hits),
      "early_sell_benefit_positive":len(winners),"early_sell_precision":round(len(winners)/n,4) if n else None,
      "mean_early_sell_vs_next_open_pp":means([x["benefit_vs_open_30bp"] for x in events]),
      "mean_60bp":means([x["benefit_vs_open_60bp"] for x in events]),
      "independent_days":len({x["day"] for x in events}),
      "earliest_major":min((x["alert_at"] for x in hits),default=None)}

def main():
    outfile=Path(sys.argv[1]) if len(sys.argv)>1 else Path("/tmp/v2-run15-semi-thresholds.json")
    raw={}
    for p in ("/tmp/semis_52wk_5min_sip_adjusted.json","/tmp/semis_peers_52wk_5min_adjusted.json"):
        raw.update(json.loads(Path(p).read_text()))
    ser=parse(raw)
    majors={(s,d) for s in SYMS for d,r in ser[s].items()
       if prior_price(ser[s],d) is not None and "15:55" in r and
       100*(r["15:55"][2]/prior_price(ser[s],d)-1)<=-5}
    complete={(s,d) for s in SYMS for d,r in ser[s].items()
         if prior_price(ser[s],d) is not None and "15:55" in r}
    baseline=json.loads(Path("/tmp/v2-run10-daily-audit.json").read_text())
    matched={(x["sym"],x["day"]) for x in baseline}
    majors={(x["sym"],x["day"]) for x in baseline if x["major_down"]}
    complete=matched
    cases={}
    for threshold in (2.,2.5,3.):
     for last in (.5,1.,1.5):
      for confirm in ("none","soxx","soxx_breadth"):
       key=f"total{threshold}_15min{last}_{confirm}"
       events=[e for e in first_signals(ser,threshold,last,confirm) if (e["sym"],e["day"]) in matched]
       cases[key]={"all":summarize(events,len(majors)),
         "earlier":summarize([e for e in events if e["day"]<PIVOT],sum(d<PIVOT for s,d in majors)),
         "later":summarize([e for e in events if e["day"]>=PIVOT],sum(d>=PIVOT for s,d in majors))}
    # Select a frozen earlier-period variant only; report OOS later without selecting on later labels.
    qualified=[(k,v) for k,v in cases.items()
       if v["earlier"]["independent_days"]>=30 and v["earlier"]["alerts"]>=50]
    qualified.sort(key=lambda kv:(
       kv[1]["earlier"]["early_sell_precision"] or 0,
       kv[1]["earlier"]["mean_early_sell_vs_next_open_pp"] or -999),reverse=True)
    selected=qualified[0][0] if qualified else None
    report={"source":"Existing 52-week split-adjusted Alpaca SIP OHLC 5m only; NO quote/BOATS/fills",
      "method":"Owner overlap: -threshold total from prior completed RTH close including -momentum percentage points over preceding 15m. Bar available at start+5m; modeled exit at next 5m open; compare to following eligible RTH open minus 30bp and 60bp adverse costs. No order placement.",
      "full_stockdays":len(complete),"major_down_stockdays":len(majors),
      "earlier_major":sum(d<PIVOT for s,d in majors),"later_major":sum(d>=PIVOT for s,d in majors),
      "selected_earlier_only":selected,
      "selected_later_holdout":cases[selected]["later"] if selected else None,
      "threshold_grid":cases}
    outfile.write_text(json.dumps(report,indent=2))
    print(json.dumps({"stockdays":len(complete),"majors":len(majors),"selected":selected,
       "selected_later":report["selected_later_holdout"],
       "key_cases":{k:cases[k] for k in ("total2.0_15min1.0_none",
                                      "total2.5_15min1.0_none",
                                      "total3.0_15min1.0_none",
                                      "total2.5_15min1.0_soxx_breadth")}},indent=2))
if __name__=="__main__":main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]