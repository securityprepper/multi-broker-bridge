"""V2-only 20-session SIP 1m upside/downside anti-churn stress replay.

No broker actions; no use of today's 1m or future bar as a signal input.
Signals at 09:35 ET use completed 09:34 ET bar + prior FIVE completed RTH closes.
Fills at next available 09:35 open, exits at NEXT bar OPEN following completed
trigger close. Final hold mark at 14:40 ET = 13:40 America/Chicago.
2026-10-12 through 2026-11-06. No margin/borrow/queue fills verified.
"""
import json,math,collections
from pathlib import Path
from datetime import datetime,time
from zoneinfo import ZoneInfo
ET=ZoneInfo("America/New_York")
SIP20=Path("/tmp/sector_complete_20session_alpaca_mixed.json")
SIP5=Path("/tmp/semis_52wk_5min_sip_adjusted.json")
SYMS=("AMD","MU","SNDK")
ALL=("SOXX",)+SYMS
STRATS=("hold_1340_CT","one_min_sector_tight","one_pct_target_stop","five_min_trend_aware","one_min_one_reentry")
COST=.30

def tparse(s):
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(ET)

def daily_1min(all_data,day):
    result={}
    for sym in ALL:
        o={}
        for ts,a in all_data[day][sym].items():
            t=tparse(ts)
            if t.date().isoformat()!=day or not (time(9,30)<=t.time()<=time(14,40)):continue
            if a[5]!="sip":continue
            o[t.strftime("%H:%M")]=list(a)
        if not all(x in o for x in ("09:34","09:35","14:40")):
            return None
        if len(o)!=311:return None
        result[sym]=o
    return result

def prior_5_history(path=SIP5):
    j=json.loads(path.read_text());h={}
    for sym in ALL:
        by={}
        for iso,a in j[sym].items():
            t=tparse(iso)
            if t.time()==time(15,55) and float(a[3])>0:
                by[t.date().isoformat()]=float(a[3])
        h[sym]=sorted(by.items())
    return h

def previous_five(series,day):
    eligible=[p for d,p in series if d<day]
    return eligible[-5:] if len(eligible)>=5 else None

def reconcile_sector_price_basis(daybars, previous_close):
    """Normalize raw SOXX 1m to the prior-five split-adjusted 5m basis.

    As-of 09:35 ET only: 09:34 completed 1m + PREVIOUS completed RTH close.
    Fail closed on unrecognized ratio, never infer from same-day final close.
    """
    current=daybars["SOXX"]["09:34"][3]
    ratio=current/previous_close
    if 2.50<=ratio<=3.50:
        factor=3
    elif .65<=ratio<=1.45:
        factor=1
    else:
        raise ValueError("Unknown SOXX 1m/5m price basis; refuse day")
    if factor!=1:
        for row in daybars["SOXX"].values():
            for i in range(4):
                row[i]=float(row[i])/factor
    return factor

def sign_at_window(daybars, prev, obs="09:34", threshold=.20):
    pct={s:100*(daybars[s][obs][3]/prev[s]-1) for s in ALL}
    q=[d for d in (1,-1) if d*pct["SOXX"]>=threshold and
       sum(d*pct[s]>=threshold for s in SYMS)>=2]
    return q[0] if len(q)==1 else 0

def eligible_stocks(daybars,prev,sign,obs="09:34", threshold=.20):
    return [s for s in SYMS if sign*100*(daybars[s][obs][3]/prev[s]-1)>=threshold]

def outcome(daybars,sym,sign,start_index,policy):
    times=sorted(daybars[sym])
    assert times[0]=="09:30" and times[-1]=="14:40"
    entry=daybars[sym][times[start_index]][0]
    if entry<=0:raise ValueError("bad entry")
    stop_index=len(times)-1
    reason="TIME_1340_CT"
    soxx=daybars["SOXX"]
    peak=entry
    # The exit check uses ONLY completed candle at index i; fill next i+1 OPEN
    for i in range(start_index,len(times)-1):
        p=daybars[sym][times[i]][3]
        prev=daybars[sym][times[i-1]][3] if i>start_index else entry
        s=soxx[times[i]][3]
        s1=soxx[times[i-1]][3] if i>start_index else s
        peak=max(peak,p) if sign==1 else min(peak,p)
        signed=sign*100*(p/entry-1)
        prev_min_signed=sign*100*(p/prev-1)
        sec_1m=sign*100*(s/s1-1)
        if policy in ("one_min_sector_tight","one_min_one_reentry"):
            should_exit=(prev_min_signed<=-.15 and sec_1m<=-.10)
            if should_exit:reason="ONE_MIN_REVERSAL"
        elif policy=="one_pct_target_stop":
            should_exit=abs(signed)>=1
            if should_exit:reason="ONE_PCT_CLOSE_LEVEL"
        elif policy=="five_min_trend_aware":
            a5=daybars[sym][times[i-5]][3] if i>=start_index+5 else entry
            ss5=soxx[times[i-5]][3] if i>=start_index+5 else s
            stock_5=sign*100*(p/a5-1)
            sec_5=sign*100*(s/ss5-1)
            should_exit=(signed<=-2.5 or (i>=start_index+10 and stock_5<=-.4 and sec_5<=-.4))
            if should_exit:reason="FIVE_MIN_TREND_OR_EMERGENCY"
        else:should_exit=False
        if should_exit:
            stop_index=i+1
            break
    exit_price=daybars[sym][times[stop_index]][0]
    gross=sign*100*(exit_price/entry-1)
    return {"symbol":sym,"policy":policy,"side":"UP" if sign==1 else "DOWN",
      "entry_at":times[start_index],"exit_at":times[stop_index],
      "gross_pct":round(gross,5),"net30_pct":round(gross-COST,5),
      "reason":reason,"duration_min":stop_index-start_index}

def run(all_data,hist):
    rows=[]
    for day in sorted(all_data):
        bars=daily_1min(all_data,day)
        if not bars:continue
        prior={s:previous_five(hist[s],day) for s in ALL}
        if not all(prior.values()):continue
        prev={s:prior[s][-1] for s in ALL}
        reconcile_sector_price_basis(bars,prev["SOXX"])
        sign=sign_at_window(bars,prev)
        for policy in STRATS:
            if not sign:
                rows.append({"day":day,"policy":policy,"signal":"ABSTAIN","forecast_count":0,"results":[]})
                continue
            selected=eligible_stocks(bars,prev,sign)
            trades=[]
            for sym in selected:
                first=outcome(bars,sym,sign,5,policy)
                trades.append(first)
                if policy=="one_min_one_reentry" and first["reason"]!="TIME_1340_CT":
                    exit_ind=sorted(bars[sym]).index(first["exit_at"])
                    # as-of 15m quiet period, 5m peer+sector confirming *same* direction
                    for i in range(exit_ind+15,310):
                        tm=sorted(bars[sym])[i-1] # last COMPLETED candle at candidate time
                        if sign_at_window(bars,prev,tm,threshold=.20)!=sign:continue
                        if sym not in eligible_stocks(bars,prev,sign,tm,threshold=.20):continue
                        trades.append(outcome(bars,sym,sign,i,policy))
                        break
            rows.append({"day":day,"policy":policy,"signal":"UP" if sign==1 else "DOWN","forecast_count":len(selected),"results":trades})
    return rows

def summarize(rows):
    out={}
    for policy in STRATS:
        days=[x for x in rows if x["policy"]==policy]
        trials=[t for x in days for t in x["results"]]
        early=days[:10];later=days[10:]
        def agg(sample):
            v=[t for x in sample for t in x["results"]];r=[t["net30_pct"] for t in v]
            day_means=[sum(t["net30_pct"] for t in x["results"])/len(x["results"]) for x in sample if x["results"]]
            return {"market_days":len(sample),"signal_days":sum(bool(x["results"]) for x in sample),
             "trade_count":len(v),"up_trades":sum(t["side"]=="UP" for t in v),
             "down_trades":sum(t["side"]=="DOWN" for t in v),
             "after_30bp_winners":sum(a>0 for a in r),
             "win_pct_after30":round(100*sum(a>0 for a in r)/len(r),2) if r else None,
             "mean_gross_pct":round(sum(t["gross_pct"] for t in v)/len(v),4) if v else None,
             "mean_after30_pct":round(sum(r)/len(r),4) if r else None,
             "mean_signal_day_after30_pct":round(sum(day_means)/len(day_means),4) if day_means else None,
             "mean_hold_minutes":round(sum(t["duration_min"] for t in v)/len(v),2) if v else None,
             "one_min_triggers":sum(t["reason"]=="ONE_MIN_REVERSAL" for t in v)}
        out[policy]={"total":agg(days),"earlier10":agg(early),"later10":agg(later)}
    return out

if __name__=="__main__":
    d=json.loads(SIP20.read_text())
    rows=run(d,prior_5_history())
    report={"scope":"20 independent market days Oct12-Nov6 2026, 1Min SIP research not actual V1 fills",
       "timing":"09:34 completed 1m forecast, 09:35 next minute OPEN entry; close-trigger next bar OPEN exits; latest 14:40 ET=13:40 Chicago flat",
       "friction":"0.30 percentage points round trip per trade proxy, no broker bid/ask/short eligibility",
       "thresholds":"SOXX >=.2% from previous regular close + at least 2 of 3 AMD MU SNDK >=.2%, trade qualifying stocks; prior5 complete regular closes validated",
       "summary":summarize(rows),"daily":rows}
    p=Path("/tmp/v2-run20-anti-churn-results.json");p.write_text(json.dumps(report,indent=2))
    print(json.dumps(report["summary"],indent=2))
