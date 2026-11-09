"""V2 RESEARCH ONLY. Strict as-of sector direction to 13:30 ET.
No broker requests, order paths or production writes.
"""
import json,sys,math
from pathlib import Path
from datetime import datetime,time,timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from statistics import mean
ET=ZoneInfo("America/New_York")
P=Path("/tmp/v2-run17-cross-sector-precision")
sys.path.insert(0,str(P))
from research import v2_gold_miner_preopen_lead as g
from research import v2_cross_sector_confirmed_walkforward as c

GOLD=Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
SEMI_FILES={
"SOXX":("/tmp/semis_52wk_5min_sip_adjusted.json","SOXX"),
"AMD":("/tmp/semis_52wk_5min_sip_adjusted.json","AMD"),
"MU":("/tmp/semis_52wk_5min_sip_adjusted.json","MU"),
"SNDK":("/tmp/semis_52wk_5min_sip_adjusted.json","SNDK"),
**{x:("/tmp/semis_peers_52wk_5min_adjusted.json",x) for x in ("NVDA","AVGO","WDC","TSM","INTC")}
}
def load_semis():
    files={};ss=defaultdict(dict)
    for sym,(path,key) in SEMI_FILES.items():
        if path not in files:files[path]=json.loads(Path(path).read_text())
        for iso,row in files[path][key].items():
            dt=datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(ET)
            if dt.weekday()<5:ss[(sym,dt.date().isoformat())][dt]=tuple(row)
    return ss

def load_gold():
    ss=defaultdict(dict)
    for sym in ("GLD","GDX","NEM","AEM","KGC"):
        j=json.loads((GOLD/(sym+"_sip.json")).read_text())
        assert j["feed"]=="sip" and j["adjustment"]=="split" and j["timeframe"]=="5Min"
        for iso,*row in j["bars"]:
            t=datetime.fromisoformat(iso.replace("Z","+00:00")).astimezone(ET)
            if t.weekday()<5:ss[(sym,t.date().isoformat())][t]=tuple(row)
    return ss

def exact_close(ss,sym,day,start):
    t=datetime.fromisoformat(day).replace(tzinfo=ET,hour=start.hour,minute=start.minute)
    bar=ss.get((sym,day),{}).get(t)
    # 5m candle starting at HH:MM finishes 5 minutes later
    return float(bar[3]) if bar and len(bar)>=5 and float(bar[3])>0 else None

def study(sector,ss,etf,signals,prior,complete,days=None):
    all_days=sorted(d for s,d in complete if s==etf)
    result=[]
    for d in all_days:
        if days is not None and d not in days:continue
        p=prior.get((etf,d))
        dayclose=complete[(etf,d)]["close"]
        p1005=exact_close(ss,etf,d,time(10,0))
        p1330=exact_close(ss,etf,d,time(13,25))
        if not(p and p1005 and p1330 and dayclose):continue
        # determine prediction strictly using input bars with end <= 10:05.
        side=signals(d)
        r=(p1330/p1005-1)*100
        actual="UP" if dayclose>p else ("DOWN" if dayclose<p else "NEUTRAL")
        result.append({"day":d,"sector":sector,"signal_at":"10:05 ET",
                       "side":side,"actual":actual,
                       "mark_1005":round(p1005,4),"mark_1330":round(p1330,4),
                       "etf_change_pct_1005_1330":round(r,5),
                       "directional_return_pct":round((1 if side=="UP" else -1)*r,5) if side!="ABSTAIN" else None,
                       "full_day_pct":round((dayclose/p-1)*100,5)})
    return result

s=load_semis()
sf=g.complete_sessions(s)
sp,sp5,_=g.historical_context(sf)
leaders=("AMD","MU","SNDK","NVDA","AVGO","WDC","TSM","INTC")
def semi_signal(day):
    # 10:00-10:05 observed, not 10:00 instant
    pct={}
    for sym in ("SOXX",)+leaders:
        p=sp.get((sym,day))
        m=exact_close(s,sym,day,time(10,0))
        if not(p and m):return "ABSTAIN"
        pct[sym]=100*(m/p-1)
    out=[sign for sign in (1,-1)
         if sign*pct["SOXX"]>=1 and sum(sign*pct[x]>=0 for x in leaders)>=3]
    return ("UP" if out[0]==1 else "DOWN") if len(out)==1 else "ABSTAIN"
rows=study("semiconductors",s,"SOXX",semi_signal,sp,sf)

gg=load_gold()
gf=g.complete_sessions(gg)
gp,gp5,_=g.historical_context(gf)
def gold_signal(day):
    pct={}
    for sym in ("GLD","GDX","NEM","AEM","KGC"):
        p=gp.get((sym,day));m=exact_close(gg,sym,day,time(10,0))
        if not(p and m):return "ABSTAIN"
        pct[sym]=100*(m/p-1)
    ok=[sign for sign in (1,-1) if sign*pct["GDX"]>=.15 and
        all(sign*pct[x]>=.7 for x in ("NEM","AEM","KGC")) and sign*pct["GLD"]>=.1]
    return ("UP" if ok[0]==1 else "DOWN") if len(ok)==1 else "ABSTAIN"
rows+=study("gold_miners",gg,"GDX",gold_signal,gp,gf)

cc,meta=c.load()
cf=g.complete_sessions(cc)
cp,cp5,_=g.historical_context(cf)
rules={"energy":"prior5_scaled","financials":"strong_breadth","industrials":"strong_breadth",
       "healthcare":"breadth","software":"strong_breadth"}
for sector,rule in rules.items():
    syms=c.SECTORS[sector]
    def side_of(day,rule=rule,syms=syms):
        f={sym:c.feature(day,"10:00",sym,cc,cp,cp5) for sym in syms}
        f={sym:x for sym,x in f.items() if x is not None}
        hits=[sign for sign in (1,-1) if c.signal(f,syms,rule,"10:00",sign)]
        return ("UP" if hits[0]==1 else "DOWN") if len(hits)==1 else "ABSTAIN"
    rows+=study(sector,cc,syms[0],side_of,cp,cf)

def summary(group,subset="all"):
    n=len(group); sel=[x for x in group if x["side"]!="ABSTAIN"]
    signed=[x["directional_return_pct"] for x in sel]
    bulls=[x for x in sel if x["side"]=="UP"]
    bears=[x for x in sel if x["side"]=="DOWN"]
    correct=sum(x["side"]==x["actual"] for x in sel)
    compounded=100*(math.prod(1+x/100 for x in signed)-1) if signed else 0
    # equal-sized independent trades have average return; compounded is artificial sequential reinvestment scenario.
    return {"total_sessions":n,"forecasts":len(sel),"abstain":n-len(sel),
      "bullish_n":len(bulls),"bearish_n":len(bears),
      "bullish_correct":sum(x["actual"]=="UP" for x in bulls),
      "bearish_correct":sum(x["actual"]=="DOWN" for x in bears),
      "direction_correct":correct,
      "direction_accuracy_pct":round(100*correct/len(sel),2) if sel else None,
      "total_signed_percentage_points":round(sum(signed),3),
      "mean_signed_pct_per_forecast":round(mean(signed),3) if signed else None,
      "compounded_signed_pct_illustrative":round(compounded,3),
      "positive_followthrough_n":sum(x>0 for x in signed),
      "above_30bp_after_proxy_n":sum(x>.30 for x in signed),
      "signed_after_30bp_total_pp":round(sum(x-.3 for x in signed),3),
      "bullish_total_pp":round(sum(x["directional_return_pct"] for x in bulls),3),
      "bearish_total_pp":round(sum(x["directional_return_pct"] for x in bears),3),
      "unconditional_etf_1005_1330_total_pp":round(sum(x["etf_change_pct_1005_1330"] for x in group),3),
      "unconditional_etf_1005_1330_mean_pct":round(mean(x["etf_change_pct_1005_1330"] for x in group),3) if group else None}

out={}
for sec in sorted({x["sector"] for x in rows}):
    arr=sorted((x for x in rows if x["sector"]==sec),key=lambda x:x["day"])
    cutoff=int(len(arr)*.70)
    out[sec]={"entire_period":summary(arr),"first70pct":summary(arr[:cutoff]),
              "last30pct":summary(arr[cutoff:]),
              "last30_start":arr[cutoff]["day"],"first_date":arr[0]["day"],"last_date":arr[-1]["day"]}
Pout=Path("/tmp/v2-direction-1005-to-1330-20261109.json")
Pout.write_text(json.dumps({"definition":"10:00-10:05 ET bar CLOSE to 13:25-13:30 ET bar CLOSE; full-day direction previous RTH close to present close",
                            "source":"Alpaca SIP 5Min split-adjusted trade bars (not executable NBBO quotes)",
                            "metrics":out,"observations":rows},indent=2))
print(json.dumps(out,indent=2))
