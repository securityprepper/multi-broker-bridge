"""V2 research-only: causal 52-week sector UP/DOWN forecast walk-forward.

Completed split-adjusted Alpaca SIP five-minute TRADE bars; no NBBO/BOATS executable
quotes, one-minute series, synchronized futures/news, or broker operations.
SIP timestamps denote BAR STARTS. A 09:25 forecast sees at most the 09:20 bar.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timedelta, time
from collections import defaultdict
from statistics import mean
from zoneinfo import ZoneInfo
from math import sqrt

ET=ZoneInfo("America/New_York")
TRAIN_END="2026-09-01"
CLOCKS=("PREV_EVENING","08:30","09:25","10:00","11:00","13:00")
RULES=("etf","peer_one","peer_both","peer_both_15m","peer_both_prior5","rth_peer")
THRESHOLDS=(.10,.25,.50,1.0)
SECTORS={
 "semiconductors":("SOXX","AMD","MU"),
 "gold_miners":("GDX","NEM","AEM"),
 "energy":("XLE","XOM","CVX"),
 "financials":("XLF","JPM","BAC"),
 "industrials":("XLI","CAT","GE"),
 "healthcare":("XLV","UNH","LLY"),
 "software":("IGV","MSFT","CRM"),
}
SOURCES={
 "semiconductors":("/tmp/semis_52wk_5min_sip_adjusted.json","/tmp/semis_peers_52wk_5min_adjusted.json"),
 "gold_miners":("/tmp/v2-run15-sector-precision-work/alpaca_sip",),
 "energy":("/tmp/v2-run17-cross-sector-precision/alpaca_sip",),
 "financials":("/tmp/v2-run17-cross-sector-precision/alpaca_sip",),
 "industrials":("/tmp/v2-run17-cross-sector-precision/alpaca_sip",),
 "healthcare":("/tmp/v2-run17-cross-sector-precision/alpaca_sip",),
 "software":("/tmp/v2-run17-cross-sector-precision/alpaca_sip",),
}

def parse_time(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("naive source timestamp")
    return t.astimezone(ET)

def source_bars(sector,syms):
    data={}
    if sector=="semiconductors":
        d={}
        for p in SOURCES[sector]:d.update(json.loads(Path(p).read_text()))
        for sym in syms:
            if sym not in d:raise ValueError("missing semiconductor feed "+sym)
            data[sym]=[(parse_time(k),row) for k,row in d[sym].items()]
    else:
        for sym in syms:
            p=Path(SOURCES[sector][0])/(sym+"_sip.json")
            raw=json.loads(p.read_text())
            if (raw.get("feed"),raw.get("adjustment"),raw.get("timeframe"))!=("sip","split","5Min"):
                raise ValueError("untrusted feed "+str(p))
            data[sym]=[(parse_time(row[0]),row[1:]) for row in raw["bars"]]
    return data

def load_sector(sector):
    syms=SECTORS[sector];raw=source_bars(sector,syms)
    daily=defaultdict(dict)
    for sym,obs in raw.items():
        for t,row in obs:
            if row[0]<=0 or row[3]<=0:continue
            daily[(sym,t.date().isoformat())][t.strftime("%H:%M")]=(float(row[0]),float(row[3]),t)
    # Require a completed regular day; reject half sessions and incomplete/missing opens/closes.
    complete={}
    for key,bars in daily.items():
        if "09:30" not in bars or "15:55" not in bars:continue
        if sum("09:30"<=k<="15:55" for k in bars)<65:continue
        complete[key]={"open":bars["09:30"][0],"close":bars["15:55"][1]}
    prev={};prior5={};next_open={}
    for sym in syms:
        ds=sorted(day for (s,day) in complete if s==sym)
        for i,day in enumerate(ds):
            if i>0:prev[(sym,day)]=complete[(sym,ds[i-1])]["close"]
            if i>=5:prior5[(sym,day)]=[complete[(sym,x)]["close"] for x in ds[i-5:i]]
            if i+1<len(ds):next_open[(sym,day)]=complete[(sym,ds[i+1])]["open"]
    return syms,daily,complete,prev,prior5,next_open

def features(day,checkpoint,syms,daily,complete,prev,prior5):
    # Only historical as-of features. Today's regular close/labels intentionally inaccessible.
    keys=[(sym,day) for sym in syms]
    if not all(k in prev and k in prior5 and k in complete for k in keys):return None
    if checkpoint=="PREV_EVENING":
        # previous trading day, not calendar day, in every symbol.
        days=sorted(d for s,d in complete if s==syms[0] and d<day)
        if not days:return None
        source_day=days[-1];minute="19:55";asof=time(20,0)
    else:
        h,m=map(int,checkpoint.split(":"));source_day=day
        t=datetime.fromisoformat(day).replace(tzinfo=ET,hour=h,minute=m)
        minute=(t-timedelta(minutes=5)).strftime("%H:%M")
        asof=time(h,m)
    features={}
    for sym in syms:
        bars=daily.get((sym,source_day),{})
        current=bars.get(minute)
        if current is None:return None
        bar_end=current[2]+timedelta(minutes=5)
        decision=datetime.fromisoformat(source_day).replace(
            tzinfo=ET,hour=asof.hour,minute=asof.minute)
        if bar_end > decision:raise ValueError("unfinished bar leakage")
        p=prev[(sym,day)]
        if checkpoint=="PREV_EVENING":
            # On preceding evening, 20:00 bar compared to that day's known RTH close.
            p=complete[(sym,source_day)]["close"]
        rth_open=complete[(sym,day)]["open"] if checkpoint not in ("PREV_EVENING","08:30","09:25") else None
        old_time=(current[2]-timedelta(minutes=15)).strftime("%H:%M")
        old=bars.get(old_time)
        history=prior5[(sym,day)]
        features[sym]={"move":100*(current[1]/p-1),
           "recent":100*(current[1]/old[1]-1) if old else None,
           "open_move":100*(current[1]/rth_open-1) if rth_open else None,
           "prior5":100*(history[-1]/history[0]-1),
           "prior_abs":mean(abs(100*(b/a-1)) for a,b in zip(history,history[1:])),
           "asof":bar_end.isoformat(),"last":current[1]}
    return features

def signal(feat,syms,rule,threshold,clock):
    etf,p1,p2=syms
    main=feat[etf]["move"]
    if abs(main)<threshold:return "ABSTAIN"
    sign=1 if main>0 else -1
    peer=[feat[s] for s in (p1,p2)]
    agreeing=sum(sign*x["move"]>.10 for x in peer)
    if rule=="peer_one" and agreeing<1:return "ABSTAIN"
    if rule in ("peer_both","peer_both_15m","peer_both_prior5","rth_peer") and agreeing<2:
        return "ABSTAIN"
    if rule=="peer_both_15m":
        if feat[etf]["recent"] is None or sign*feat[etf]["recent"]<.10:return "ABSTAIN"
    if rule=="peer_both_prior5":
        if sign*feat[etf]["prior5"]<0:return "ABSTAIN"
    if rule=="rth_peer":
        if clock in ("PREV_EVENING","08:30","09:25"):return "ABSTAIN"
        if feat[etf]["open_move"] is None or sign*feat[etf]["open_move"]<.10:return "ABSTAIN"
    return "UP" if sign>0 else "DOWN"

def label(close,reference,band=.15):
    pct=100*(close/reference-1)
    return "UP" if pct>band else "DOWN" if pct< -band else "NEUTRAL"

def wilson(k,n):
    if not n:return 0.0
    z=1.96;p=k/n;a=z*z
    return (p+a/(2*n)-z*sqrt(p*(1-p)/n+a/(4*n*n)))/(1+a/n)

def score(rows):
    """Predictions include ABSTAIN; summarize precision AND emitted coverage."""
    n=len(rows)
    counts={s:0 for s in ("UP","DOWN","NEUTRAL")}
    confusion={pred:{s:0 for s in ("UP","DOWN","NEUTRAL")}
              for pred in ("UP","DOWN","ABSTAIN")}
    for r in rows:
        counts[r["actual"]]+=1
        confusion[r["prediction"]][r["actual"]]+=1
    emitted=[r for r in rows if r["prediction"]!="ABSTAIN"]
    hit=sum(r["prediction"]==r["actual"] for r in emitted)
    precision={}
    recall={}
    for side in ("UP","DOWN"):
        p=[r for r in emitted if r["prediction"]==side]
        a=[r for r in rows if r["actual"]==side]
        precision[side]=sum(r["actual"]==side for r in p)/len(p) if p else None
        recall[side]=sum(r["prediction"]==side for r in a)/len(a) if a else None
    valid=[v for v in recall.values() if v is not None]
    return {"days":n,"counts":counts,"issued":len(emitted),"abstained":n-len(emitted),
      "coverage":len(emitted)/n if n else 0,
      "correct":hit,"wrong":len(emitted)-hit,
      "accuracy":hit/len(emitted) if emitted else None,
      "wilson95":wilson(hit,len(emitted)),
      "up_precision":precision["UP"],"down_precision":precision["DOWN"],
      "up_recall":recall["UP"],"down_recall":recall["DOWN"],
      "balanced_recall":mean(valid) if valid else None,"confusion":confusion}

def is_eligible(sc):
    return (sc["issued"]>=30 and sc["coverage"]>=.15 and sc["accuracy"] is not None
      and sc["accuracy"]>=.80 and sc["wilson95"]>=.70
      and sc["up_precision"] is not None and sc["up_precision"]>=.75
      and sc["down_precision"] is not None and sc["down_precision"]>=.75
      and sc["confusion"]["UP"]["UP"]>=10 and sc["confusion"]["DOWN"]["DOWN"]>=10)

def all_rows(sector,clock,rule,threshold,cache,neutral_band=.15):
    syms,daily,complete,prev,prior5,next_open=cache
    etf=syms[0]
    days=sorted(d for s,d in complete if s==etf
                and all((sym,d) in complete and (sym,d) in prev and (sym,d) in prior5 for sym in syms))
    rows=[]
    for day in days:
        f=features(day,clock,syms,daily,complete,prev,prior5)
        if f is None:continue
        pred=signal(f,syms,rule,threshold,clock)
        actual=label(complete[(etf,day)]["close"],prev[(etf,day)],neutral_band)
        open_label=label(complete[(etf,day)]["close"],complete[(etf,day)]["open"],neutral_band)
        close_pct=100*(complete[(etf,day)]["close"]/prev[(etf,day)]-1)
        rth_pct=100*(complete[(etf,day)]["close"]/complete[(etf,day)]["open"]-1)
        prior_mean=f[etf]["prior_abs"]
        severe=max(1.,1.5*prior_mean)
        significant_up=max(close_pct,rth_pct)>=severe
        significant_down=min(close_pct,rth_pct)<=-severe
        advance=pred=="UP" and f[etf]["move"]>=.5*severe
        retreat=pred=="DOWN" and f[etf]["move"]<=-.5*severe
        emergency=advance or retreat
        rows.append({"day":day,"sector":sector,"checkpoint":clock,"rule":rule,
          "threshold_pct":threshold,"prediction":pred,"actual":actual,
          "open_to_close_actual":open_label,"close_pct":round(close_pct,5),
          "rth_pct":round(rth_pct,5),"observed_sector_pct":round(f[etf]["move"],4),
          "sector_mark_price":round(f[etf]["last"],6),"previous_regular_close":round(prev[(etf,day)],6),"regular_close_price":round(complete[(etf,day)]["close"],6),
          "sector_recent_15m_pct":round(f[etf]["recent"],4) if f[etf]["recent"] is not None else None,
          "bar_available_at":f[etf]["asof"],
          "severity_threshold_pct":round(severe,4),
          "significant_up":significant_up,"significant_down":significant_down,
          "emergency":bool(emergency),"next_regular_open":next_open.get((etf,day))})
    return rows

def regime_rows(cache):
    syms,_,complete,prev,prior5,_=cache
    etf,*peers=syms
    counts={"positive":0,"negative":0,"mixed":0}
    days=sorted(d for s,d in complete if s==etf and
        all((sym,d) in complete and (sym,d) in prev and (sym,d) in prior5 for sym in syms))
    for d in days:
        moves=[complete[(s,d)]["close"]/prev[(s,d)]-1 for s in syms]
        status="positive" if all(x>0 for x in moves) else "negative" if all(x<0 for x in moves) else "mixed"
        counts[status]+=1
    return counts

def emergency_stats(rows):
    alerts=[r for r in rows if r["emergency"]]
    hits=[r for r in alerts if (r["prediction"]=="UP" and r["significant_up"])
                          or (r["prediction"]=="DOWN" and r["significant_down"])]
    severe=[r for r in rows if r["significant_up"] or r["significant_down"]]
    missed=[r["day"] for r in severe if r not in hits]
    early=[r for r in hits if abs(r["observed_sector_pct"])<r["severity_threshold_pct"]]
    return {"alerts":len(alerts),"true_significant":len(hits),
       "false_alerts":len(alerts)-len(hits),"significant_days":len(severe),
       "missed_severe":len(missed),"first_five_missed":missed[:5],
       "before_reaching_severe":len(early),
       "earliest_true_warning_et":min((r["bar_available_at"] for r in hits),default=None),
       "outcomes_after_warning": "not executable fills; next regular open marks available as separate research comparison"}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",required=True)
    ap.add_argument("--audit",required=True)
    args=ap.parse_args()
    result={"study":"V2 direction-FIRST as-of fixed checkpoint 52-week SIP replay",
       "train_end_exclusive":TRAIN_END,"sectors":{},
       "notes":["Direction 80% means correct sector UP/DOWN at same-day RTH close, NOT trade profitability.",
                "Data uses 5m Alpaca SIP split-adjusted TRADE bars, not full NBBO or 1m; futures/news unavailable.",
                "Bar timestamps are START timestamps; last complete bar finishes by forecast checkpoint.",
                "Prior-five completed RTH days only; training before 2026-09-01; later holdout is not used for selection.",
                "Neutral ±0.15% counted in denominator, ABSTAIN included in coverage; UP/DOWN precision separate.",
                "2026-11-09 is NOT completed and is not scored.",
                "V1 PAPER/LIVE/broker order paths untouched; no strategy deployment GO."]}
    audits=[]
    for sector in SECTORS:
        cache=load_sector(sector);regimes=regime_rows(cache)
        group={"regime_counts":regimes,"checkpoint_results":{},"thresholds_tried":THRESHOLDS}
        for clock in CLOCKS:
            candidates=[]
            for rule in RULES:
                for threshold in THRESHOLDS:
                    rows=all_rows(sector,clock,rule,threshold,cache)
                    tr=[r for r in rows if r["day"]<TRAIN_END]
                    te=[r for r in rows if r["day"]>=TRAIN_END]
                    if not tr or not te:continue
                    a=score(tr);b=score(te)
                    candidates.append((rule,threshold,a,b,te))
            if not candidates:
                group["checkpoint_results"][clock]={"available":False};continue
            # Freeze selection using TRAINING ONLY, preferring valid adequate two-sided skill.
            qualifying=[c for c in candidates if is_eligible(c[2])]
            selected=sorted(qualifying,key=lambda c:(-c[2]["balanced_recall"],
               -c[2]["coverage"],-c[2]["accuracy"],c[0],c[1]))[0] if qualifying else None
            shadow=max(candidates,key=lambda c:(
                 (c[2]["balanced_recall"] or 0),
                 c[2]["coverage"],c[2]["accuracy"] or 0)) # illustrative, not approved
            reference=selected or shadow
            rule,threshold,trsc,tesc,te=reference
            e=emergency_stats(te)
            group["checkpoint_results"][clock]={
                "training_qualified_count":len(qualifying),
                "policy":"QUALIFIED" if selected else "SHADOW_ONLY_NO_GO",
                "rule":rule,"threshold_pct":threshold,
                "earlier":trsc,"later":tesc,"later_emergency":e,
                "holdout_evaluation_only":True}
            audits.extend(te)
        result["sectors"][sector]=group
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    Path(args.audit).write_text(json.dumps(audits,indent=0))
    compact={}
    for s,d in result["sectors"].items():
        compact[s]={"regimes":d["regime_counts"],
           "checkpoints":{k:{"policy":v.get("policy"),"rule":v.get("rule"),
           "threshold":v.get("threshold_pct"),
           "training_accuracy":round(v["earlier"]["accuracy"],3) if v.get("earlier") and v["earlier"]["accuracy"] is not None else None,
           "later_accuracy":round(v["later"]["accuracy"],3) if v.get("later") and v["later"]["accuracy"] is not None else None,
           "later_coverage":round(v["later"]["coverage"],3) if v.get("later") else None,
           "later_up_precision":v["later"]["up_precision"] if v.get("later") else None,
           "later_down_precision":v["later"]["down_precision"] if v.get("later") else None,
           "emergencies":v.get("later_emergency")} for k,v in d["checkpoint_results"].items()}}
    print(json.dumps(compact,indent=2))
if __name__=="__main__":main()