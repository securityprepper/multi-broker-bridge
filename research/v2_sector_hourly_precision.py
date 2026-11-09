"""V2 RESEARCH ONLY: 52-week hourly independent sector/precious-metals holdouts.

Public hourly proxy data, NOT Alpaca SIP/BOATS/NBBO. No orders, APIs to brokers,
or imports from production code. Signals use only the PREVIOUS five completed
regular-session closes and the fully completed 09:30-10:30 ET bar.
"""
from __future__ import annotations
import json, math, sys, time, urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone, date
from pathlib import Path
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
URL="https://query1.finance.yahoo.com/v8/finance/chart/{}?range=1y&interval=60m&includePrePost=false"
SECTORS={
 "gold_miners":("GLD","GDX",("GDXJ","NEM","AEM","KGC"),.25,.50),
 "energy":("XLE","XOP",("OIH","USO"),.60,.80),
 "financials":("XLF","KRE",("JPM","BAC"),.60,.80),
 "industrials":("XLI","ITA",("CAT","DE"),.60,.80),
 "healthcare":("XLV","XBI",("UNH","LLY"),.60,.80),
 "software":("XLK","IGV",("MSFT","CRM"),.60,.80),
}
CUTOFF=date(2026,11,6)
LATER=date(2026,9,1)

def fetch(symbol, cache):
    p=cache/(symbol+".json")
    if p.exists(): return json.loads(p.read_text())
    req=urllib.request.Request(URL.format(symbol),
         headers={"User-Agent":"Mozilla/5.0 V2research/1.0"})
    with urllib.request.urlopen(req,timeout=12) as response:
        data=json.loads(response.read())
    result=data["chart"]["result"][0]
    if len(result.get("timestamp",[]))<600: raise RuntimeError("insufficient 52-week hourly proxy "+symbol)
    p.write_text(json.dumps(result,separators=(",",":")))
    time.sleep(.2)
    return result

def prepare(raw):
    """Date -> {HH:MM: (open, high, low, close)}. Exclude uncompleted future sessions."""
    out={}
    quotes=raw["indicators"]["quote"][0]
    for i,ts in enumerate(raw["timestamp"]):
        loc=datetime.fromtimestamp(ts,timezone.utc).astimezone(ET)
        if loc.date()>CUTOFF or loc.weekday()>=5: continue
        hm=loc.strftime("%H:%M")
        if hm not in ("09:30","10:30","11:30","12:30","13:30","14:30","15:30"):
            continue
        o,h,l,c=(quotes[k][i] for k in ("open","high","low","close"))
        if any(x is None or x<=0 or not math.isfinite(x) for x in (o,h,l,c)): continue
        out.setdefault(loc.date().isoformat(),{})[hm]=(o,h,l,c)
    return out

def prev_closes(data,day,n=1):
    dates=[d for d in sorted(data) if d<day and "15:30" in data[d]]
    if len(dates)<n: return None
    return [data[d]["15:30"][3] for d in dates[-n:]]

def current_delta(data,day):
    pc=prev_closes(data,day)
    if not pc or day not in data or "09:30" not in data[day]: return None
    return 100*(data[day]["09:30"][3]/pc[-1]-1)

def prior5_delta(data,day):
    cs=prev_closes(data,day,6)
    if cs is None: return None
    return 100*(cs[-1]/cs[0]-1)

def candidate(data,day,anchor,target,peers,at,tt,kind):
    # No future observation, same-day close or next opening influences signal.
    a=current_delta(data[anchor],day)
    t=current_delta(data[target],day)
    if a is None or t is None: return None
    if kind=="anchor_only": return a>=at
    if kind=="target_only": return t>=tt
    if kind in ("dual","dual_breadth","dual_prior5"):
        if a<at or t<tt: return False
        if kind=="dual": return True
        if kind=="dual_prior5":
            trend=prior5_delta(data[target],day)
            return trend is not None and trend>=0
        observed=[current_delta(data[s],day) for s in peers]
        complete=[x for x in observed if x is not None]
        return len(complete)==len(peers) and sum(x>=.25 for x in complete)>=max(2,math.ceil(.5*len(peers)))
    raise ValueError(kind)

def outcome(data,day,target):
    bars=data[target].get(day,{})
    if "10:30" not in bars or "15:30" not in bars: return None
    entry=bars["10:30"][0]      # Next completed bar opening mark, NOT executable ask
    exit=bars["15:30"][3]
    future=[d for d in sorted(data[target]) if d>day and "09:30" in data[target][d]]
    next_open=data[target][future[0]]["09:30"][0] if future else None
    return {"entry":entry,"close":exit,
            "gross_pct":100*(exit/entry-1),
            "net_30bp_pct":100*(exit/entry-1)-.30,
            "net_60bp_pct":100*(exit/entry-1)-.60,
            "next_open_net_30bp_pct":100*(next_open/entry-1)-.30 if next_open else None}

def summarize(rows):
    n=len(rows)
    if not n:return {"n":0,"profitable":0,"precision":None,"mean_net":None,"mean_net_60bp":None}
    vals=[r["outcome"]["net_30bp_pct"] for r in rows]
    w=sum(x>0 for x in vals)
    vals60=[r["outcome"]["net_60bp_pct"] for r in rows]
    z=1.96;p=w/n;z2=z*z
    low=(p+z2/(2*n)-z*math.sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)
    return {"n":n,"profitable":w,"precision":round(w/n,4),
        "wilson_95_lower":round(low,4),
        "mean_net":round(sum(vals)/n,4),
        "mean_net_60bp":round(sum(vals60)/n,4),
        "worst_net":round(min(vals),4),
        "independent_days":len({r["day"] for r in rows})}

def study(data):
    result={}
    for name,(anchor,target,peers,at,tt) in SECTORS.items():
        if any(s not in data for s in (anchor,target,*peers)):
            result[name]={"error":"missing a required proxy series"};continue
        days=sorted(set(data[anchor]) & set(data[target]))
        events={}
        labels={"positive":0,"negative":0,"mixed":0}
        allout=[]
        for day in days:
            out=outcome(data,day,target)
            pc=prev_closes(data[target],day)
            if out is None or pc is None:continue
            sameclose=data[target][day]["15:30"][3]
            cc=100*(sameclose/pc[-1]-1)
            labels["positive" if cc>=.75 else "negative" if cc<=-.75 else "mixed"]+=1
            if "09:30" not in data[target][day] or "09:30" not in data[anchor][day]:continue
            allout.append({"day":day,"outcome":out})
            for kind in ("anchor_only","target_only","dual","dual_breadth","dual_prior5"):
                q=candidate(data,day,anchor,target,peers,at,tt,kind)
                if q is True:
                    events.setdefault(kind,[]).append({"day":day,"outcome":out,"signal_at":"10:30 ET"})
        r={"source":"Yahoo Finance public hourly ETF/equity chart proxy, 1y 60m, NOT SIP or BOATS",
          "target":target,"anchor":anchor,"peers":list(peers),"thresholds_pct":[at,tt],
          "sector_session_labels_75bp":labels,
          "daily_baseline":summarize(allout),
          "rules":{}}
        for kind in ("anchor_only","target_only","dual","dual_breadth","dual_prior5"):
            rows=events.get(kind,[])
            r["rules"][kind]={"all":summarize(rows),
                "earlier":summarize([x for x in rows if x["day"]<LATER.isoformat()]),
                "later":summarize([x for x in rows if x["day"]>=LATER.isoformat()]),
                "last_8_dates":[{"day":x["day"],"net_pct":round(x["outcome"]["net_30bp_pct"],3)}
                                for x in rows[-8:]]}
        result[name]=r
    return {"asof_max":CUTOFF.isoformat(),
            "constraints":"09:30 hourly bar is observed only at 10:30 ET; outcome uses following 10:30 hourly OPEN mark. 30bp/60bp roundtrip model, not fills. Yahoo data not Alpaca SIP/BOATS. No news timestamps, no 1m, no stop execution.",
            "sectors":result}

def main():
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("/tmp/v2-run15-sector-precision")
    root.mkdir(parents=True,exist_ok=True)
    cache=root/"hourly_data";cache.mkdir(exist_ok=True)
    symbols=sorted({s for a,t,pp,_,_ in SECTORS.values() for s in (a,t,*pp)})
    data={};failed={}
    for s in symbols:
        try:data[s]=prepare(fetch(s,cache))
        except Exception as exc:failed[s]=f"{type(exc).__name__}:{exc}"
    r=study(data);r["download_failures"]=failed
    (root/"sector_hourly_research_results.json").write_text(json.dumps(r,indent=2,sort_keys=True))
    print(json.dumps({"source_data_symbol_days":{k:len(v) for k,v in data.items()},
                      "failed":failed,
                      "sectors":{k:{"labels":v.get("sector_session_labels_75bp"),"dual":v.get("rules",{}).get("dual",{}),
                                      "dual_breadth":v.get("rules",{}).get("dual_breadth",{}),
                                      "dual_prior5":v.get("rules",{}).get("dual_prior5",{})} for k,v in r["sectors"].items()}},indent=2))
if __name__=="__main__":
    main()
