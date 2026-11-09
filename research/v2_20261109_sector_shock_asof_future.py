"""Research-only V2 ETF shock forward replay, 2026-11-09.

Use completed split-adjusted SIP 5m trade-bar CLOSE (not intrabar highs),
same-session OPEN for RTH baseline and prior regular-session CLOSE for night.
Chronological 70/30 split; no fitted parameter on holdout. One earliest event
per date/sector/mode. Returns ALWAYS start at signal-time close. Research,
not executable bid/ask, authorization or a trading algorithm.
"""
from __future__ import annotations
import csv,json,math
from collections import defaultdict
from datetime import datetime,timedelta,time
from pathlib import Path
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
CT=ZoneInfo("America/Chicago")
BASE=Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
GOLD=Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
FILES={
"semiconductors":("SOXX",("AMD","MU","SNDK"),2.0,3.0),
"gold_miners":("GDX",("NEM","AEM","KGC"),2.0,2.0),
"energy":("XLE",("XOM","CVX"),3.0,3.0),
"financials":("XLF",("JPM","BAC"),3.0,3.0),
"industrials":("XLI",("CAT","GE"),3.0,3.0),
"healthcare":("XLV",("UNH","LLY"),3.0,3.0),
"software":("IGV",("MSFT","CRM"),3.0,3.0),
}
def source_path(sym):
    if sym in ("SOXX","AMD","MU","SNDK"):
        return "/tmp/semis_52wk_5min_sip_adjusted.json"
    p=GOLD/(sym+"_sip.json")
    if p.exists():return str(p)
    return str(BASE/(sym+"_sip.json"))

def load(sym):
    blob=json.load(open(source_path(sym)))
    if sym in blob and isinstance(blob[sym],dict):
        rows=((stamp,row) for stamp,row in blob[sym].items())
    else:
        assert blob["feed"]=="sip" and blob["timeframe"]=="5Min" and blob["adjustment"]=="split"
        rows=((r[0],r[1:]) for r in blob["bars"])
    out=defaultdict(dict)
    for stamp,values in rows:
        dt=datetime.fromisoformat(stamp.replace("Z","+00:00")).astimezone(ET)
        if dt.weekday()>=5:continue
        start=dt.time()
        if not (time(4)<=start<time(20)):continue
        op,high,low,close=[float(x) for x in values[:4]]
        if min(op,high,low,close)<=0:continue
        end=dt+timedelta(minutes=5)
        out[dt.date().isoformat()][end]=(op,high,low,close)
    return out

def valid_regular(day):
    arr={t:v for t,v in day.items() if time(9,35)<=t.time()<=time(16)}
    open_t=next((t for t in arr if t.time()==time(9,35)),None)
    close_t=next((t for t in arr if t.time()==time(16)),None)
    if open_t is None or close_t is None or len(arr)<65:return None
    return {"open":arr[open_t][0],"close":arr[close_t][3],"bars":dict(sorted(arr.items()))}

def pct(future,origin):
    return (future/origin-1)*100

def crossed(close,origin,threshold):
    delta=pct(close,origin)
    return 1 if delta>=threshold-1e-9 else (-1 if delta<=-threshold+1e-9 else 0)

def one_or_confirmed(bars,baseline,threshold,mode,breadth_peers=None):
    """Returns earliest eligible (completed bar END, price, direction).
    breadth_peers maps ticker to {complete 5m END: close}; caller guarantees
    ref values are based on earlier/current complete RTH/previous session.
    """
    prior_end=None;prior_direction=0
    for dt,close in sorted(bars.items()):
        side=crossed(close,baseline,threshold)
        if side==0:
            prior_end=dt;prior_direction=0
            continue
        if mode in ("two_close","breadth"):
            if prior_direction!=side or prior_end is None or dt-prior_end!=timedelta(minutes=5):
                prior_end=dt;prior_direction=side
                continue
        if mode=="breadth":
            agree=0;needed=2
            for bars_ref,peer_ref in breadth_peers or []:
                # Only completed, sufficiently current data qualify.
                vals=[(t,v) for t,v in bars_ref.items() if t<=dt and timedelta(0)<=dt-t<=timedelta(minutes=10)]
                if not vals:continue
                close_peer=max(vals,key=lambda z:z[0])[1]
                if crossed(close_peer,peer_ref,0.25)==side:agree+=1
            if agree<needed:
                prior_end=dt;prior_direction=side
                continue
        return dt,close,side
    return None

def session_bars(etf,date):
    return valid_regular(etf.get(date,{}))

def day_case(etf,peers,dates,date,thr,mode):
    today=session_bars(etf,date)
    if not today:return None
    bars={t:v[3] for t,v in today["bars"].items()}
    basis=[]
    for sym,ser in peers.items():
        s=session_bars(ser,date)
        if s:
            basis.append(({t:v[3] for t,v in s["bars"].items()},s["open"]))
    z=one_or_confirmed(bars,today["open"],thr,mode,basis)
    if not z:return None
    return {"date":date,"signal_end":z[0],"price":z[1],"side":z[2],
            "entry_basis":"rth_open","threshold":thr,"origin":today["open"],
            "mode":mode,"future_bars":bars,"next_open":None,
            "rth_entry_eligible":z[0].time()<=time(14,15)}

def night_case(etf,peers,dates,i,thr,mode):
    if i==0:return None
    day=dates[i];prev=dates[i-1];old=session_bars(etf,prev)
    new=session_bars(etf,day)
    if not old or not new:return None
    # SIP only: 16-20 ET post on earlier session, 04-09:30 ET pre.
    etf_ext={}
    for t,v in etf[prev].items():
        if time(16,5)<=t.time()<=time(20) :etf_ext[t]=v[3]
    for t,v in etf[day].items():
        if time(4,5)<=t.time()<=time(9,30):etf_ext[t]=v[3]
    basis=[]
    for sym,ser in peers.items():
        po=session_bars(ser,prev)
        if not po:continue
        ext={}
        for t,v in ser.get(prev,{}).items():
            if time(16,5)<=t.time()<=time(20):ext[t]=v[3]
        for t,v in ser.get(day,{}).items():
            if time(4,5)<=t.time()<=time(9,30):ext[t]=v[3]
        basis.append((ext,po["close"]))
    z=one_or_confirmed(etf_ext,old["close"],thr,mode,basis)
    if not z:return None
    return {"date":day,"signal_end":z[0],"price":z[1],"side":z[2],
            "entry_basis":"prev_rth_close","threshold":thr,"origin":old["close"],
            "mode":mode,"rth_entry_eligible":False,
            "future_bars":{t:v[3] for t,v in new["bars"].items()},
            "next_open":new["open"]}

def forward(event,session):
    """Exact wall-clock post-signal mark. Missing outcomes stay missing."""
    signal=event["signal_end"];r={}
    if session=="day":
        for minutes in (15,60):
            value=event["future_bars"].get(signal+timedelta(minutes=minutes))
            r[str(minutes)+"m"]=pct(value,event["price"])*event["side"] if value else None
        for label,goal in (("1330",time(13,30)),("1440",time(14,40)),("1600",time(16))):
            cand=[p for t,p in event["future_bars"].items() if t.time()==goal and t>signal]
            r[label]=pct(cand[0],event["price"])*event["side"] if cand else None
    else:
        p=event["next_open"]
        r["next_open"]=pct(p,event["price"])*event["side"] if p else None
        for label,goal in (("1000",time(10)),("1330",time(13,30))):
            cand=[p for t,p in event["future_bars"].items() if t.time()==goal and t>signal]
            r[label]=pct(cand[0],event["price"])*event["side"] if cand else None
    return r

def summarize(events,split,session):
    out={"n":len(events),"up":sum(e["side"]>0 for e in events),
         "down":sum(e["side"]<0 for e in events),"first_event":None}
    if events:
        z=min(events,key=lambda x:x["signal_end"])
        out["first_event"]=z["signal_end"].astimezone(CT).isoformat()
    for horizon in (("15m","60m","1330","1440","1600") if session=="day" else ("next_open","1000","1330")):
        valid=[e["forward"][horizon] for e in events if e["forward"][horizon] is not None]
        n=len(valid)
        out[horizon]={"observed":n,"correct":sum(v>=0.05 for v in valid),
             "wrong":sum(v<=-0.05 for v in valid),
             "flat_under_005pp":sum(abs(v)<0.05 for v in valid),
             "after_30bp_profitable":sum(v>0.30 for v in valid),
             "win_pct":round(100*sum(v>=0.05 for v in valid)/n,2) if n else None,
             "net_win_pct_30bp":round(100*sum(v>0.30 for v in valid)/n,2) if n else None,
             "mean_signed_pct":round(sum(valid)/n,4) if n else None,
             "mean_net_30bp":round(sum(valid)/n-.30,4) if n else None,
             "worst_signed_pct":round(min(valid),4) if n else None}
    return out

def run():
    cache={sym:load(sym) for sym in sorted({s for s,peers,d,n in FILES.values() for s in (s,*peers)})}
    output={};records=[]
    for sector,(etfsym,peer_syms,day_thr,night_thr) in FILES.items():
        etf=cache[etfsym];peers={p:cache[p] for p in peer_syms}
        dates=sorted(d for d in etf if session_bars(etf,d))
        split_i=int(len(dates)*.7);cutoff=dates[split_i]
        sector_result={"etf":etfsym,"peer_breadth":list(peer_syms),
                       "date_start":dates[0],"date_end":dates[-1],
                       "day_threshold_pct":day_thr,"night_threshold_pct":night_thr,
                       "n_completed_sessions":len(dates),"holdout_start":cutoff,
                       "n_holdout_days":len(dates)-split_i}
        for session in ("day","night"):
            for mode in ("one_close","two_close","breadth"):
                cases=[]
                for i,day in enumerate(dates):
                    e=day_case(etf,peers,dates,day,day_thr,mode) if session=="day" else night_case(etf,peers,dates,i,night_thr,mode)
                    if e:
                        e["forward"]=forward(e,session)
                        cases.append(e)
                        records.append({
                           "sector":sector,"etf":etfsym,"session":session,"mode":mode,
                           "day":day,"split":"later" if day>=cutoff else "earlier",
                           "signal_ct":e["signal_end"].astimezone(CT).isoformat(),
                           "signal_et":e["signal_end"].isoformat(),
                           "side":"UP" if e["side"]>0 else "DOWN",
                           "rth_entry_eligible":e["rth_entry_eligible"],
                           "reference":round(e["origin"],5),"signal_price":round(e["price"],5),
                           "already_moved_pct":round(pct(e["price"],e["origin"]),5),
                           **{k+"_signed_fwd_pct":round(v,5) if v is not None else "" for k,v in e["forward"].items()}
                        })
                k=session+"_"+mode
                sector_result[k]={
                    "all":summarize(cases,cutoff,session),
                    "earlier":summarize([e for e in cases if e["date"]<cutoff],cutoff,session),
                    "later":summarize([e for e in cases if e["date"]>=cutoff],cutoff,session),
                    "rth_eligible_later":summarize([e for e in cases if e["date"]>=cutoff and e["rth_entry_eligible"]],cutoff,session) if session=="day" else None,
                    "abstained_all":len(dates)-len(cases),
                    "abstained_holdout":len(dates)-split_i-sum(e["date"]>=cutoff for e in cases),
                }
        output[sector]=sector_result
    result=Path("/tmp/v2_20261109_sector_shock_asof_future_summary.json")
    result.write_text(json.dumps(output,indent=2)+"\n")
    path=Path("/tmp/v2_20261109_sector_shock_asof_future_events.csv")
    with path.open("w",newline="") as f:
        if records:
            fields=sorted(set().union(*(r.keys() for r in records)))
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
    print("events",len(records),"csv",path,"summary",result)
    for sector,s in output.items():
        print(sector,"dates",s["n_completed_sessions"],"holdout",s["n_holdout_days"])
        for typ in ("day_one_close","day_two_close","day_breadth","night_one_close","night_two_close","night_breadth"):
            r=s[typ]["later"]
            name="1600" if typ.startswith("day") else "next_open"
            m=r[name]
            print(typ,"issued",r["n"],"dirUP/DN",r["up"],r["down"],"future",m["observed"],
                  "correct",m["correct"],"pct",m["win_pct"],"netprof",m["after_30bp_profitable"],"net%",m["net_win_pct_30bp"],"netmean",m["mean_net_30bp"])
    return output
if __name__=="__main__":run()
