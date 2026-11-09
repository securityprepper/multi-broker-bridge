"""V2 RESEARCH ONLY: gold-to-miner as-of 5m SIP leading-signal test.
No broker access. INPUT BARS ARE START-TIMESTAMPED; use only completed candles.
BOTH long and downside watch outcomes assessed on EVERY completed gold/miner day.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime, timedelta, time
from math import sqrt
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
BARS_DIR=Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
BOATS_DIR=Path("/tmp/v2-run15-sector-precision-work/alpaca_boats")
SYMBOLS=("GLD","GDX","GDXJ","NEM","AEM","KGC")
MINERS=("GDX","GDXJ","NEM","AEM","KGC")
D=timedelta(minutes=5)
SPLIT="2026-09-01"
RTH_OPEN=time(9,30)
RTH_END=time(15,55)
PROTOCOLS=("gold_only","miner_only","gold_gdx","gold_breadth")
CLOCKS=("09:25","09:45")

def wilson(w,n):
    if n==0:return 0.0
    p=w/n;z=1.96;z2=z*z
    return (p+z2/(2*n)-z*sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)

def parse(raw):
    ts=datetime.fromisoformat(raw.replace("Z","+00:00")).astimezone(ET)
    return ts

def load_data(folder=BARS_DIR):
    sessions=defaultdict(dict)
    source={}
    for sym in SYMBOLS:
        path=folder/(sym+"_sip.json")
        j=json.loads(path.read_text())
        if not (j["feed"]=="sip" and j["adjustment"]=="split" and j["timeframe"]=="5Min"):
            raise ValueError("historical feed adjustment mismatch: "+sym)
        source[sym]={"bars":len(j["bars"]),"retrieved_at":j["retrieved_at"]}
        for data in j["bars"]:
            t=parse(data[0])
            if data[1] and data[4]>0:
                sessions[(sym,t.date().isoformat())][t]=(float(data[1]),float(data[2]),float(data[3]),float(data[4]),int(data[5]))
    return sessions,source

def at(bars,decision,minimum=time(4,0),max_age_min=15):
    # Latest available bar MUST end before or at decision; session-specific freshness.
    options=[(t,v) for t,v in bars.items() if minimum<=t.time() and t+D<=decision and
             0<=(decision-(t+D)).total_seconds()/60<=max_age_min]
    if not options:return None
    t,v=max(options,key=lambda x:x[0])
    return v[3],t.isoformat(),v[4]

def open_mark(bars,clock):
    for t,v in bars.items():
        if t.time()==clock:return v[0]
    return None

def complete_sessions(sessions):
    full={}
    for k,bars in sessions.items():
        rth=sorted((t,v) for t,v in bars.items() if RTH_OPEN<=t.time()<=RTH_END)
        if len(rth)<65 or rth[0][0].time()>time(9,35) or rth[-1][0].time()<time(15,50):
            continue
        full[k]={"open":rth[0][1][0],"close":rth[-1][1][3],"low":min(v[2] for _,v in rth),
                 "high":max(v[1] for _,v in rth),"rth_count":len(rth)}
    return full

def historical_context(full):
    prev={}; prior5={}; nxt={}; grouped=defaultdict(list)
    for (sym,day),s in full.items():grouped[sym].append((day,s))
    for sym,items in grouped.items():
        items.sort()
        for i,(day,s) in enumerate(items):
            if i>=1:prev[(sym,day)]=items[i-1][1]["close"]
            if i>=5:prior5[(sym,day)]=[x[1]["close"] for x in items[i-5:i]]
            if i+1<len(items):nxt[(sym,day)]=items[i+1][1]["open"]
    return prev,prior5,nxt

def features(day,clock,sessions,prev,prior5):
    hh,mm=map(int,clock.split(":"))
    # Obtain date from local market sessions, not naive UTC date.
    decision=datetime.fromisoformat(day).replace(tzinfo=ET,hour=hh,minute=mm)
    f={}
    for sym in SYMBOLS:
        p=prev.get((sym,day))
        hist=prior5.get((sym,day))
        if p is None or hist is None:continue
        a=at(sessions.get((sym,day),{}),decision,minimum=time(4,0),max_age_min=15)
        if a is None:continue
        f[sym]={"pct":(a[0]/p-1)*100,"price":a[0],"seen_at":a[1],"volume":a[2],
                "prior5":(p/hist[0]-1)*100}
    return f

def qualifies(feat,rule,side):
    sign=1 if side=="up" else -1
    gold=feat.get("GLD");gdx=feat.get("GDX")
    gold_ok=bool(gold and sign*gold["pct"]>=.25)
    gdx_ok=bool(gdx and sign*gdx["pct"]>=.40)
    available=[feat.get(s) for s in ("NEM","AEM","KGC")]
    breadth=sum(bool(x and sign*x["pct"]>=.40) for x in available)>=2
    if rule=="gold_only":return gold_ok
    if rule=="miner_only":return gdx_ok and breadth
    if rule=="gold_gdx":return gold_ok and gdx_ok
    if rule=="gold_breadth":return gold_ok and gdx_ok and breadth
    raise ValueError(rule)

def outcome(prior,open_price,close_price):
    total=(close_price/prior-1)*100
    rth=(close_price/open_price-1)*100
    return {"close_pct":total,"rth_pct":rth,
            "major_up":max(total,rth)>=3,"major_down":min(total,rth)<=-3,
            "gap_down":(open_price/prior-1)*100<=-3}

def stats(rows,side):
    n=len(rows)
    if not n:return {"count":0,"independent_days":0}
    days=len({r["day"] for r in rows})
    wins=sum(r["net_pct"]>0 for r in rows)
    loss_days=sum(r["severe"] for r in rows)
    return {"count":n,"independent_days":days,"after_cost_profitable":wins,
      "precision_after_cost":round(wins/n,4),"wilson_lower_95":round(wilson(wins,n),4),
      "mean_net30_pct":round(mean(r["net_pct"] for r in rows),4),
      "mean_net60_pct":round(mean(r["net60_pct"] for r in rows),4),
      "major_move_hits":loss_days,
      "major_move_precision":round(loss_days/n,4),
      "gap_already_ge3":sum(r["gap_down"] for r in rows) if side=="down" else None,
      "positive_trade_days":len({r["day"] for r in rows if r["net_pct"]>0}),
      "date_equal_net30_pct":round(mean(mean(q["net_pct"] for q in rows if q["day"]==d) for d in {r["day"] for r in rows}),4),
      "earliest_major_warning":min((r["signal_at"] for r in rows if r["severe"]),default=None)}

def run(data_dir=BARS_DIR):
    sessions,source=load_data(data_dir)
    full=complete_sessions(sessions)
    prev,prior5,nxt=historical_context(full)
    # Outcome audit including NO-SIGNAL dates.
    audited=[]
    eligible=[]
    for (sym,day),today in sorted(full.items()):
        if sym not in MINERS or (sym,day) not in prev:continue
        o=outcome(prev[(sym,day)],today["open"],today["close"])
        audited.append({"symbol":sym,"day":day,**o})
        if (sym,day) in prior5:eligible.append({"symbol":sym,"day":day,**o})
    summaries={}
    samples=[]
    for clock in CLOCKS:
        enter=time(9,35) if clock=="09:25" else time(9,50)
        for rule in PROTOCOLS:
            for side in ("up","down"):
                result=[]
                signals=set()
                for day in sorted({d for _,d in full}):
                    f=features(day,clock,sessions,prev,prior5)
                    if not qualifies(f,rule,side):continue
                    for sym in MINERS:
                        key=(sym,day)
                        if key not in full or key not in prev or key not in prior5:continue
                        entry=open_mark(sessions.get(key,{}),enter)
                        exit14=open_mark(sessions.get(key,{}),time(14,0))
                        following=nxt.get(key)
                        if not entry or not exit14:continue
                        mark=outcome(prev[key],full[key]["open"],full[key]["close"])
                        # BUY: positive price move makes money.
                        # DOWN/WATCH: hypothetical early sale beats selling 14:00.
                        advantage=((exit14/entry-1)*100 if side=="up" else
                                   (entry/exit14-1)*100)
                        signal_date=day+"T"+clock+":00"
                        row={"day":day,"symbol":sym,"signal_at":signal_date,
                             "entry":round(entry,4),"exit14":round(exit14,4),
                             "net_pct":advantage-.30,"net60_pct":advantage-.60,
                             "severe":mark["major_up"] if side=="up" else mark["major_down"],
                             "gap_down":mark["gap_down"],
                             "close_pct":round(mark["close_pct"],3),
                             "next_open_adv_pp":round((entry-following)/prev[key]*100-.30,4)
                                                if following and side=="down" else None}
                        signals.add(key)
                        result.append(row)
                sub={}
                for label,predicate in (("all",lambda d: True),
                                        ("earlier",lambda d:d<SPLIT),
                                        ("later",lambda d:d>=SPLIT)):
                    group=[r for r in result if predicate(r["day"])]
                    universe=[x for x in eligible if predicate(x["day"])]
                    major=sum(x["major_up"] if side=="up" else x["major_down"] for x in universe)
                    hit=len({(r["symbol"],r["day"]) for r in group if r["severe"]})
                    sub[label]={**stats(group,side),"total_major_eligible":major,
                       "major_move_coverage":round(hit/major,4) if major else None,
                       "missed_major":major-hit,"nonmajor_signals":len(group)-hit}
                summaries[f"{clock}_{rule}_{side}"]=sub
                samples.extend(result)
    boats_coverage={}
    for sym in SYMBOLS:
        j=json.loads((data_dir.parent/"alpaca_boats"/(sym+"_boats.json")).read_text())
        # Bar prints only, NOT NBBO quotations, and frequently very sparse.
        boats_coverage[sym]={"bars":len(j.get("bars",[])),
           "active_et_dates":len({parse(a[0]).date().isoformat() for a in j.get("bars",[])})}
    output={"inputs":source,"boats_prints":boats_coverage,"full_complete_miner_stockdays":len(audited),
      "prior5_eligible_miner_stockdays":len(eligible),"total_major_up":sum(a["major_up"] for a in eligible),
      "total_major_down":sum(a["major_down"] for a in eligible),
      "summary":summaries,
      "notes":["SIP data are 5-minute OHLC START time, only completed bars used for signals",
               "GLD leader is a traded ETF price, not spot gold or futures",
               "BOATS feed files are BARS, NOT executable bids/asks; no broker fills inferred",
               "Hypothetical entry at 09:35 or 09:50 OPEN, exit at 14:00 OPEN with 30/60bp adverse cost",
               "Signals conditioned on >=5 strictly PRIOR completed stock and GLD sessions",
               "OOS later from September 1, frozen a priori signal definitions; correlated miner stockdays not independent",
               "Downside exit benefit compared to 14:00 and next regular open is proxy, not proven executable trade",
               "No 2026-11-09 bars in dataset; cannot evaluate this morning's gold move directly"] }
    return output,samples,audited

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);p.add_argument("--data-dir",default=str(BARS_DIR))
    a=p.parse_args()
    summary,events,audit=run(Path(a.data_dir))
    Path(a.output).write_text(json.dumps(summary,indent=2,sort_keys=True))
    Path(a.output+".events.json").write_text(json.dumps(events,indent=0))
    Path(a.output+".audit.json").write_text(json.dumps(audit,indent=0))
    print(json.dumps({"eligible":summary["prior5_eligible_miner_stockdays"],
      "major_up":summary["total_major_up"],"major_down":summary["total_major_down"],
      "summary":{k:v["later"] for k,v in summary["summary"].items()}},indent=2))

if __name__=="__main__":main()
