"""V2 research: frozen 09:35 ET sector-constituent signals, 52-week 5m SIP.
All decisions from completed past bars, next-next-bar entry/exit (5m latency).
Final 14:40 ET OPEN (13:40 CT) prior to approved 2pm CT latest-flat.
No broker access, no modifications to active V1 or broker orders.
"""
import json,statistics
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from collections import defaultdict,Counter
ET=ZoneInfo("America/New_York")
SYMS=("SOXX","AMD","MU","SNDK"); PEERS=SYMS[1:]
RULES=("hold","tight_5m","target_stop_1","hard_stop_1p5","hard_stop_2p5","hard_stop_4","trail_2p5_after_1")
SRC=Path("/tmp/semis_52wk_5min_sip_adjusted.json")
def load(path=SRC):
    j=json.loads(path.read_text()); bars=defaultdict(dict)
    for s in SYMS:
        for iso,v in j[s].items():
            dt=datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(ET)
            tm=dt.strftime("%H:%M")
            if "09:30"<=tm<="15:55":
                bars[s,dt.date().isoformat()][tm]=list(map(float,v[:4]))
    return bars
def prior5(bars):
    hist={}
    for s in SYMS:
        d=sorted((day,v["15:55"][3]) for (sym,day),v in bars.items() if sym==s and
                 len(v)>=65 and "15:55" in v and "09:30" in v)
        for i in range(5,len(d)):hist[s,d[i][0]]=[x[1] for x in d[i-5:i]]
    return hist
def forecast(day,bars,h):
    prev={s:h[s,day][-1] for s in SYMS}
    ch={s:100*(bars[s,day]["09:30"][3]/prev[s]-1) for s in SYMS}
    choices=[sign for sign in (-1,1) if sign*ch["SOXX"]>=.2 and sum(sign*ch[s]>=.2 for s in PEERS)>=2]
    side=choices[0] if len(choices)==1 else 0
    return side,[s for s in PEERS if side*ch[s]>=.2] if side else [],ch
def at_next_open(bars,s,day,time):
    v=bars[s,day].get(time)
    return v[0] if v else None
def replay(bars,day,s,side,policy,initial="09:40"):
    b=bars[s,day];sector=bars["SOXX",day]
    clocks=[t for t in sorted(b) if initial<=t<="14:40"]
    def minutes(t):
        a,z=map(int,t.split(":"));return a*60+z
    if not clocks or clocks[0]!=initial or clocks[-1]!="14:40" or any(minutes(clocks[i+1])-minutes(clocks[i])!=5 for i in range(len(clocks)-1)):return None
    if policy=="tight_5m" and not all(t in sector for t in clocks):return None
    entry=b[initial][0];peak=0;out=len(clocks)-1;trigger=False
    for i in range(len(clocks)-2):
        clock=clocks[i]
        val=side*100*(b[clock][3]/entry-1)
        peak=max(peak,val);hit=False
        if policy=="tight_5m" and i>0:
            prev=clocks[i-1]
            a=side*100*(b[clock][3]/b[prev][3]-1)
            q=side*100*(sector[clock][3]/sector[prev][3]-1)
            hit=a<=-.15 and q<=-.1
        elif policy=="target_stop_1": hit=val>=1 or val<=-1
        elif policy.startswith("hard_stop"):
            th={"hard_stop_1p5":1.5,"hard_stop_2p5":2.5,"hard_stop_4":4.}[policy]
            hit=val<=-th
        elif policy=="trail_2p5_after_1":hit=peak>=1 and peak-val>=2.5
        if hit:out=i+2;trigger=True;break
    exitprice=b[clocks[out]][0]
    gross=side*100*(exitprice/entry-1)
    mae=min(side*100*(b[t][3]/entry-1) for t in clocks[:out+1])
    return {"day":day,"symbol":s,"side":"UP" if side==1 else "DOWN","policy":policy,
      "entry_time":initial,"exit_time":clocks[out],"entry_price":entry,"exit_price":exitprice,
      "gross":round(gross,5),"net30":round(gross-.30,5),"net60":round(gross-.60,5),
      "mae":round(mae,4),"hold_minutes":minutes(clocks[out])-minutes(initial),"triggered":trigger}
def sample_metrics(rows):
    if not rows:return {"trades":0}
    days=defaultdict(list)
    for r in rows:days[r["day"]].append(r["net30"])
    v=[r["net30"] for r in rows]
    return {"trades":len(rows),"signal_days":len(days),
      "up_trades":sum(r["side"]=="UP" for r in rows),"down_trades":sum(r["side"]=="DOWN" for r in rows),
      "winning_trades":sum(x>0 for x in v),"win_rate_after30":round(100*sum(x>0 for x in v)/len(v),2),
      "avg_after30":round(statistics.mean(v),4),
      "day_equal_avg_after30":round(statistics.mean(statistics.mean(x) for x in days.values()),4),
      "avg_after60":round(statistics.mean(r["net60"] for r in rows),4),
      "worst_net30":round(min(v),4),"losses_below_minus2":sum(x<=-2 for x in v),
      "losses_below_minus4":sum(x<=-4 for x in v),
      "avg_mae":round(statistics.mean(r["mae"] for r in rows),4),
      "stop_events":sum(r["triggered"] for r in rows),
      "avg_hold_minutes":round(statistics.mean(r["hold_minutes"] for r in rows),2)}
def run(bars,h):
    all_days=sorted({d for s,d in bars if s=="SOXX" and (s,d) in h})
    daily=[];rows=[];invalid=0
    for day in all_days:
        if not all((s,day) in h and all(t in bars[s,day] for t in ("09:30","09:35","09:40","14:40","15:55")) for s in SYMS):
            invalid+=1;continue
        side,chosen,changes=forecast(day,bars,h)
        outcomes={s:round(100*(bars[s,day]["15:55"][3]/h[s,day][-1]-1),4) for s in SYMS}
        cls="UP" if all(v>0 for v in outcomes.values()) else "DOWN" if all(v<0 for v in outcomes.values()) else "MIXED"
        daily.append({"day":day,"state":cls,"signal":"UP" if side==1 else "DOWN" if side==-1 else "ABSTAIN",
            "chosen":chosen,"asof_0935_pct":changes,"close_pct":outcomes})
        for s in chosen:
            for policy in RULES:
                r=replay(bars,day,s,side,policy)
                if r:rows.append(r)
    dates=sorted(x["day"] for x in daily);cut=int(len(dates)*.7);early=set(dates[:cut]);late=set(dates[cut:])
    report={"market_days":len(dates),"skipped_days":invalid,"first_day":dates[0],"last_day":dates[-1],
            "late_start":dates[cut],"late_days":len(late),"signal_days":sum(d["signal"]!="ABSTAIN" for d in daily),
            "up_down_mixed":dict(Counter(d["state"] for d in daily)),
            "serious_stock_winners":sum(v>=5 for d in daily for s,v in d["close_pct"].items() if s!="SOXX"),
            "serious_stock_losers":sum(v<=-5 for d in daily for s,v in d["close_pct"].items() if s!="SOXX"),
            "caught_winners":sum(d["signal"]=="UP" and s in d["chosen"] and v>=5 for d in daily for s,v in d["close_pct"].items() if s!="SOXX"),
            "caught_losers":sum(d["signal"]=="DOWN" and s in d["chosen"] and v<=-5 for d in daily for s,v in d["close_pct"].items() if s!="SOXX"),
            "policies":{}}
    for policy in RULES:
        r=[x for x in rows if x["policy"]==policy]
        report["policies"][policy]={"all":sample_metrics(r),
                                   "earlier70":sample_metrics([x for x in r if x["day"] in early]),
                                   "later30":sample_metrics([x for x in r if x["day"] in late]),
                                   "long":sample_metrics([x for x in r if x["side"]=="UP"]),
                                   "short":sample_metrics([x for x in r if x["side"]=="DOWN"])}
    return report,daily,rows
if __name__=="__main__":
    bars=load();h=prior5(bars)
    res,daily,events=run(bars,h)
    directory=Path("/tmp/v2-run23-full-year-anti-churn")
    (directory/"results.json").write_text(json.dumps(res,indent=2))
    (directory/"daily.json").write_text(json.dumps(daily,indent=2))
    (directory/"events.json").write_text(json.dumps(events,indent=2))
    print(json.dumps(res,indent=2))
