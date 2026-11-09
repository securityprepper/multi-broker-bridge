"""V2-only six-sector 52-week SIP 5m 09:35 causal entry and exit stress.
Uses the separate semiconductor simulator as a broker-free exit policy primitive.
The 10:05 close-to-close classification is NOT used for the earlier signal.
"""
import json,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict,Counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v2_52week_delayed_anti_churn import replay,sample_metrics,RULES
ET=ZoneInfo("America/New_York")
CROSS=Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
GOLD=Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
SECTORS={
 "energy":("XLE",("XOM","CVX"),None),
 "financials":("XLF",("JPM","BAC"),None),
 "industrials":("XLI",("CAT","GE"),None),
 "healthcare":("XLV",("UNH","LLY"),None),
 "software":("IGV",("MSFT","CRM"),None),
 "gold_miners":("GDX",("NEM","AEM","KGC"),"GLD")
}
def load_sector(sector):
    etf,peers,spot=SECTORS[sector];symbols=(etf,)+peers+((spot,) if spot else ())
    bars=defaultdict(dict)
    for s in symbols:
        folder=GOLD if sector=="gold_miners" else CROSS
        data=json.loads((folder/(s+"_sip.json")).read_text())
        if not(data["feed"]=="sip" and data["adjustment"]=="split" and data["timeframe"]=="5Min"):
            raise ValueError("unknown data feed")
        for iso,*v in data["bars"]:
            dt=datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(ET)
            tm=dt.strftime("%H:%M")
            if "09:30"<=tm<="15:55" and v[0]>0 and v[3]>0:
                bars[s,dt.date().isoformat()][tm]=list(map(float,v[:4]))
    # Use reserved SOXX alias ONLY in exit simulator, never as actual trade symbol
    for (s,d),v in list(bars.items()):
        if s==etf:bars["SOXX",d]=v
    return bars
def context(bars,symbols):
    hist={}
    for s in symbols:
        dates=sorted((day,x["15:55"][3]) for (key,day),x in bars.items()
                     if key==s and len(x)>=65 and "15:55" in x and "09:30" in x)
        for i in range(5,len(dates)):hist[s,dates[i][0]]=[z[1] for z in dates[i-5:i]]
    return hist
def sector_signal(day,bars,h,etf,peers,spot):
    syms=(etf,)+peers+((spot,) if spot else ())
    ch={s:100*(bars[s,day]["09:30"][3]/h[s,day][-1]-1) for s in syms}
    sides=[v for v in (1,-1) if v*ch[etf]>=.2 and
           sum(v*ch[p]>=.2 for p in peers)>=2 and (not spot or v*ch[spot]>=.1)]
    sign=sides[0] if len(sides)==1 else 0
    return sign,[s for s in peers if sign*ch[s]>=.2] if sign else [],ch
def run():
    res={};dailyall=[];eventsall=[]
    for sector,(etf,peers,spot) in SECTORS.items():
        bars=load_sector(sector);syms=(etf,)+peers+((spot,) if spot else ())
        h=context(bars,syms)
        days=sorted(d for (s,d) in bars if s==etf and (s,d) in h)
        daily=[];events=[];skipped=0
        for d in days:
            if not all((s,d) in h and all(tm in bars[s,d] for tm in ("09:30","09:35","09:40","14:40","15:55")) for s in syms):
                skipped+=1;continue
            side,picks,obs=sector_signal(d,bars,h,etf,peers,spot)
            closes={s:round(100*(bars[s,d]["15:55"][3]/h[s,d][-1]-1),4) for s in syms}
            state="UP" if all(closes[s]>0 for s in (etf,)+peers) else "DOWN" if all(closes[s]<0 for s in (etf,)+peers) else "MIXED"
            daily.append({"sector":sector,"day":d,"state":state,
                          "signal":"UP" if side==1 else "DOWN" if side==-1 else "ABSTAIN",
                          "chosen":picks,"asof_0935_pct":obs,"close_pct":closes})
            for s in picks:
                for policy in RULES:
                    trade=replay(bars,d,s,side,policy)
                    if trade is not None:
                        trade["sector"]=sector;events.append(trade)
        dates=sorted(x["day"] for x in daily);breakpoint=int(.7*len(dates))
        early=set(dates[:breakpoint]);late=set(dates[breakpoint:])
        dmeta={"market_days":len(dates),"skipped_days":skipped,"first":dates[0],"last":dates[-1],
               "later_start":dates[breakpoint],"forecast_days":sum(x["signal"]!="ABSTAIN" for x in daily),
               "sector_state":dict(Counter(x["state"] for x in daily)),
               "major_up_stock_days":sum(x["close_pct"][p]>=5 for x in daily for p in peers),
               "major_down_stock_days":sum(x["close_pct"][p]<=-5 for x in daily for p in peers),
               "major_up_detected":sum(x["signal"]=="UP" and p in x["chosen"] and x["close_pct"][p]>=5 for x in daily for p in peers),
               "major_down_detected":sum(x["signal"]=="DOWN" and p in x["chosen"] and x["close_pct"][p]<=-5 for x in daily for p in peers),
               "policy":{}}
        for policy in RULES:
            v=[x for x in events if x["policy"]==policy]
            dmeta["policy"][policy]={"full":sample_metrics(v),
                    "earlier70":sample_metrics([x for x in v if x["day"] in early]),
                    "later30":sample_metrics([x for x in v if x["day"] in late]),
                    "up":sample_metrics([x for x in v if x["side"]=="UP"]),
                    "down":sample_metrics([x for x in v if x["side"]=="DOWN"])}
        res[sector]=dmeta;dailyall+=daily;eventsall+=events
    return res,dailyall,eventsall
if __name__=="__main__":
    out,daily,events=run()
    base=Path("/tmp/v2-run23-full-year-anti-churn")
    (base/"cross-results.json").write_text(json.dumps(out,indent=2))
    (base/"cross-daily.json").write_text(json.dumps(daily,indent=2))
    (base/"cross-events.json").write_text(json.dumps(events,indent=2))
    print(json.dumps(out,indent=2))
