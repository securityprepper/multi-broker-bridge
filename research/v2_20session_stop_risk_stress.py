"""Research-only stop risk stress for 20 historical SIP 1m semiconductor sessions.

Import existing V2 frozen 09:35 entry rule; do not touch brokerage.
Every stop uses a COMPLETED one-minute close and fills only at NEXT minute OPEN.
The final 14:40 ET opening mark is an illustrative latest-flat reference.
"""
import json
import statistics
from pathlib import Path
from v2_20session_anti_churn_replay import (
    SIP20,prior_5_history,previous_five,daily_1min,reconcile_sector_price_basis,
    sign_at_window,eligible_stocks,SYMS,ALL
)

POLICIES={
    "hold":"hold",
    "hard_stop_1p5":1.5,
    "hard_stop_2p5":2.5,
    "hard_stop_4":4.0,
    "hard_stop_6":6.0,
    "trail_1p5_after_1":("trail",1.5,1.0),
    "trail_2p5_after_1":("trail",2.5,1.0),
}

def model_exit(bars,symbol,side,stop):
    t=sorted(bars[symbol])
    assert t[5]=="09:35" and t[-1]=="14:40"
    entry=float(bars[symbol][t[5]][0])
    if entry<=0:raise ValueError("non-positive entry")
    peak=0.0
    adverse=0.0
    reason="TIME"
    target=310
    for j in range(5,310):
        # Price bar j is completed at start time j+1. Execution: opening mark j+1.
        cur=float(bars[symbol][t[j]][3])
        signed=side*100*(cur/entry-1)
        peak=max(peak,signed)
        adverse=min(adverse,signed)
        if isinstance(stop,(float,int)) and signed <= -stop:
            target=j+1;reason="HARD_STOP"
            break
        if isinstance(stop,tuple):
            _,drawdown,arm=stop
            if peak>=arm and peak-signed>=drawdown:
                target=j+1;reason="TRAIL_FROM_MAX_FAVORABLE_CLOSE"
                break
    end=float(bars[symbol][t[target]][0])
    gross=side*100*(end/entry-1)
    return {"entry":entry,"exit":end,"entry_clock":t[5],"exit_clock":t[target],
            "gross_pct":round(gross,5),"reason":reason,"hold_minutes":target-5,
            "worst_completed_close_pct_to_exit":round(adverse,4)}

def aggregate(rows):
    r=[x["gross_pct"] for x in rows]
    if not r:return {"trades":0}
    return {"trades":len(r),
      "win_after_30bp":sum(x>.30 for x in r),
      "win_pct_after_30bp":round(100*sum(x>.30 for x in r)/len(r),2),
      "win_after_60bp":sum(x>.60 for x in r),
      "mean_net_30bp":round(statistics.mean(x-.30 for x in r),4),
      "mean_net_60bp":round(statistics.mean(x-.60 for x in r),4),
      "worst_net_30bp":round(min(x-.3 for x in r),4),
      "max_adverse_close_pct_mean":round(statistics.mean(x["worst_completed_close_pct_to_exit"] for x in rows),4),
      "trades_below_minus_2pct_net":sum(x-.3<=-2 for x in r),
      "trades_below_minus_4pct_net":sum(x-.3<=-4 for x in r),
      "mean_minutes_held":round(statistics.mean(x["hold_minutes"] for x in rows),2),
      "stops":sum(x["reason"]!="TIME" for x in rows)}

def run(raw,history):
    records=[]
    for day in sorted(raw):
        bars=daily_1min(raw,day)
        if not bars:continue
        prior={s:previous_five(history[s],day) for s in ALL}
        if not all(prior.values()):continue
        prev={s:prior[s][-1] for s in ALL}
        reconcile_sector_price_basis(bars,prev["SOXX"])
        sign=sign_at_window(bars,prev)
        if not sign:continue
        selected=eligible_stocks(bars,prev,sign)
        for sym in selected:
            for name,policy in POLICIES.items():
                x=model_exit(bars,sym,sign,policy)
                records.append({"day":day,"sym":sym,"side":"UP" if sign==1 else "DOWN",
                                "policy":name,**x})
    return records

def summarize(events):
    days=sorted({x["day"] for x in events})
    early=set(days[:len(days)//2]);later=set(days[len(days)//2:])
    out={}
    for name in POLICIES:
        v=[x for x in events if x["policy"]==name]
        out[name]={"full":aggregate(v),
                   "earlier":aggregate([x for x in v if x["day"] in early]),
                   "later":aggregate([x for x in v if x["day"] in later])}
    return {"market_days":20,"signal_days":len(days),
            "split_days_earlier":sorted(early),"split_days_later":sorted(later),
            "policies":out}

if __name__=="__main__":
    events=run(json.loads(SIP20.read_text()),prior_5_history())
    res=summarize(events)
    p=Path("/tmp/v2-run21-stop-risk-stress-20261109.json")
    p.write_text(json.dumps({"scope":"20 complete 1m SIP session sample, 09:35 ET 3-constituent long/short proxy, last 13:40 Chicago",
             "inputs":"Historical SIP TRADE open/close, not NBBO or broker fills; 30/60bp illustrative round-trip friction",
             "summary":res,"events":events},indent=2))
    print(json.dumps(res,indent=2))
