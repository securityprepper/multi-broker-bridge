"""Distinct research-only volume-absorption hypothesis; fixed before outcomes.
A rising but nonextended 30-minute bar, upper-quartile close and 2.5x prior-five
same-clock trading volume; one per sector/day. No network or order submission.
"""
import argparse
import json
import csv
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import median
from importlib.machinery import SourceFileLoader

base=SourceFileLoader("novel", str(Path(__file__).with_name("v2_sector_neutral_dislocation_20261111.py"))).load_module()
RULE={"decision_et":"10:00","next_entry_et":"10:05","prior_complete_sessions":5,
      "volume_multiple_min":2.5,"price_change_min_pct":0.10,
      "price_change_max_pct":0.75,"morning_close_location_min":0.75,
      "min_price":20,"min_volume_30m_shares":5000,"one_stock_per_sector_day":True}
SLOTS=("09:30","09:35","09:40","09:45","09:50","09:55")

def morning_metrics(bars):
    if not all(t in bars for t in SLOTS): return None
    v=sum(bars[t][4] for t in SLOTS)
    h=max(bars[t][1] for t in SLOTS)
    l=min(bars[t][2] for t in SLOTS)
    c=bars["09:55"][3]
    op=bars["09:30"][0]
    return {"volume":v,"pct":base.pct(op,c),"close_location":(c-l)/(h-l) if h>l else 0.5,"price":c}

def signal_on_day(sym, d, all_days, prior_five):
    m=morning_metrics(all_days.get(d,{}))
    if m is None or m["price"] < RULE["min_price"] or m["volume"] < RULE["min_volume_30m_shares"]:
        return None
    if not RULE["price_change_min_pct"]<=m["pct"]<=RULE["price_change_max_pct"]: return None
    if m["close_location"]<RULE["morning_close_location_min"]: return None
    dates=[dt for dt in sorted(all_days) if dt<d and morning_metrics(all_days[dt]) is not None]
    p=dates[-prior_five:]
    if len(p)<prior_five: return None
    prior=[morning_metrics(all_days[dt])["volume"] for dt in p]
    med=median(prior)
    if med<=0:return None
    ratio=m["volume"]/med
    if ratio<RULE["volume_multiple_min"]: return None
    return {"symbol":sym,"volume_ratio":round(ratio,5),"early_price_pct":round(m["pct"],5),
            "close_location":round(m["close_location"],5),"prior5_end_date":p[-1],
            "source_bar_complete_et":f"{d}T10:00:00"}

def trade_returns(day, sym, etf, names):
    bars=day[sym]
    out={}
    entry=bars.get("10:05")
    for key,t in (("60m","11:05"),("flat","14:40")):
        exit=bars.get(t)
        out[f"after30bp_{key}"]=round(base.pct(entry[0],exit[0])-.30,6) if entry and exit else None
        out[f"after60bp_{key}"]=round(base.pct(entry[0],exit[0])-.60,6) if entry and exit else None
        controls=[]
        for s in (etf,*[name for name in names if name!=sym]):
            b=day[s]
            if "10:05" in b and t in b:
                controls.append(base.pct(b["10:05"][0],b[t][0]))
        out[f"control_after30bp_{key}"]=round(sum(controls)/len(controls)-.30,6) if len(controls)==len(names) else None
    return out

def run(data):
    events=[]
    for sector,(etf,names) in base.SECTORS.items():
        dates=sorted(set(data[etf]).intersection(*(set(data[s]) for s in names)))
        for d in dates:
            day={s:data[s][d] for s in (etf,*names)}
            candidates=[]
            for s in names:
                c=signal_on_day(s,d,data[s],RULE["prior_complete_sessions"])
                if c:candidates.append(c)
            if not candidates:continue
            chosen=sorted(candidates,key=lambda x:(-x["volume_ratio"],x["symbol"]))[0]
            chosen.update({"sector":sector,"date":d,
                           "source_bar_complete_et":f"{d}T10:00:00",
                           "earliest_entry_et":f"{d}T10:05:00"})
            chosen.update(trade_returns(day,chosen["symbol"],etf,names))
            events.append(chosen)
    return events

def summarize(events, cutoff):
    uniq=sorted({e["date"] for e in events});cut=cutoff
    result={"research_only":True,"rule_precommitted":True,"prior_sessions_same_clock_only":True,
            "historical_last_30_pct_repeatedly_exposed_not_blind":True,
            "rule":RULE,"cohort_cutoff_date":cut,"total_signal_events":len(events),
            "unique_dates":len(uniq),"cohorts":{}}
    for stage,subset in (("earlier_70",[e for e in events if e["date"]<cut]),
                         ("later_30",[e for e in events if e["date"]>=cut]),("full",events)):
        result["cohorts"][stage]={}
        for sector in ("ALL",*base.SECTORS):
            rows=subset if sector=="ALL" else [e for e in subset if e["sector"]==sector]
            result["cohorts"][stage][sector]={"signals":len(rows),
                "after30bp_flat":base.stats(rows,"after30bp_flat"),
                "after30bp_60m":base.stats(rows,"after30bp_60m"),
                "after60bp_flat":base.stats(rows,"after60bp_flat"),
                "matched_controls_flat":base.stats(rows,"control_after30bp_flat")}
    return result

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",default="/tmp/v2-novel-20261111");arg=a.parse_args()
    out=Path(arg.out);out.mkdir(parents=True,exist_ok=True)
    data=base.load_bars()
    events=run(data);summary=summarize(events, base.chronological_cutoff(data))
    (out/"prior5_volume_absorption_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    with (out/"prior5_volume_absorption_events.csv").open("w",newline="") as f:
        if events:
            w=csv.DictWriter(f,fieldnames=sorted(set().union(*(set(x) for x in events))));w.writeheader();w.writerows(events)
    print(json.dumps({"total":len(events),"cutoff":summary["cohort_cutoff_date"],
                      "cohorts":{k:{"ALL":v["ALL"]} for k,v in summary["cohorts"].items()},
                      "later_sectors":{k:{"signals":v["signals"],"flat":v["after30bp_flat"]}
                          for k,v in summary["cohorts"]["later_30"].items() if k!="ALL"}},indent=2))
if __name__=="__main__":main()