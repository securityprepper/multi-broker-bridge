"""Read-only 2026-11-11 historical RTH target *reachability*, not broker fills.

Every row is an actual broker-paired PAPER lot. A completed minute's traded HIGH is
only a target-touch upper bound. No retrospective limit-order fill is asserted.
No broker HTTP, credentials, positions, or order actions.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago")
TARGETS=(0.005,0.0075,0.01,0.0125,0.015,0.02,0.025,0.03)
FLAT=time(13,40)
CUTOFF=time(13,15)
OPEN=time(8,30)

def local(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("naive timestamp")
    return dt.astimezone(CT)

def first_full_after_entry(entry):
    return entry.replace(second=0,microsecond=0)+timedelta(minutes=1)

def rth_trade(t):
    if t.get("source")!="MBB":return False
    entry=local(t["entry_at"])
    return OPEN<=entry.time().replace(tzinfo=None)<CUTOFF

def assess(t,source_bars,targets=TARGETS):
    entry=local(t["entry_at"])
    flat=entry.replace(hour=13,minute=40,second=0,microsecond=0)
    start=first_full_after_entry(entry)
    buys=float(t["entry"])
    if buys<=0 or int(float(t["qty"]))<=0:raise ValueError("invalid lot")
    bars={}
    for v in source_bars:
        candle=local(v["t"])
        if candle<start or candle+timedelta(minutes=1)>flat:continue
        if candle in bars:raise ValueError("duplicate bar")
        hi,lo,close=(float(v[k]) for k in ("h","l","c"))
        if not(0<lo<=close<=hi):raise ValueError("invalid ohlc")
        bars[candle]={"h":hi,"l":lo,"c":close}
    if not bars:return {x:{"high_touch":False,"close_reach":False,"first_high_before_loss":False,
                           "first_close_before_loss":False,"missing_path":True}
                        for x in targets}
    ordered=sorted(bars.items())
    result={}
    for target in targets:
        limit=buys*(1+target)
        high_any=any(v["h"]>=limit for _,v in ordered)
        close_any=any(v["c"]>=limit for _,v in ordered)
        high_first=close_first=False
        high_state=close_state="UNDECIDED"
        expected=start
        for candle,bar in ordered:
            if candle!=expected:
                break
            expected+=timedelta(minutes=1)
            # Software loss-watch uses completed close; if the same candle
            # shows a target HIGH but closes -1% down, count loss first.
            if bar["c"]<=buys*.99:
                high_state=close_state="LOSS_FIRST"
                break
            if bar["h"]>=limit:
                high_state="TARGET_HIGH_FIRST"
                high_first=True
            if bar["c"]>=limit:
                close_state="TARGET_CLOSE_FIRST"
                close_first=True
            if high_first and close_first:break
        complete_to_flat=(expected>=flat)
        result[target]={"high_touch":high_any,"close_reach":close_any,
                        "first_high_before_loss":high_first,
                        "first_close_before_loss":close_first,
                        "missing_path":(high_state=="UNDECIDED" or close_state=="UNDECIDED")
                           and not complete_to_flat}
    return result

def aggregate(source):
    if not(source.get("research_only") is True and
           source.get("broker_orders_submitted")==0 and
           isinstance(source.get("trades"),list)):
        raise ValueError("not a verified read-only research cache")
    unique=set()
    selected=[]
    for lot in source["trades"]:
        pair=(lot.get("entry_order_id"),lot.get("exit_order_id"))
        if not all(pair) or pair in unique:raise ValueError("duplicate/absent broker order IDs")
        unique.add(pair)
        if rth_trade(lot):selected.append(lot)
    summaries=[]
    for x in selected:
        path=source.get("bars",{}).get(x["day"]+"|"+x["symbol"],[])
        result=assess(x,path)
        summaries.append((x["day"],result))
    report={"study":"MBB real PAPER RTH filled entries, after-entry 1m SIP target upper bounds",
            "research_only":True,"paper_orders_submitted":0,
            "distinct_sessions":len({d for d,_ in summaries}),
            "trades":len(selected),
            "strategy_version_caveat":"Historical mixed versions; no future-policy validation",
            "news_status":"NEWS_UNKNOWN_HISTORICAL_OUTCOME_ONLY",
            "targets":[]}
    for threshold in TARGETS:
        items=[result[threshold] for _,result in summaries]
        report["targets"].append({"target_pct":100*threshold,"trades":len(items),
            "high_touch_upper_bound":sum(x["high_touch"] for x in items),
            "close_reach_trade_mark":sum(x["close_reach"] for x in items),
            "high_before_minus1pct_losswatch_close_upper_bound":
                 sum(x["first_high_before_loss"] for x in items),
            "close_before_minus1pct_losswatch_close_trade_mark":
                 sum(x["first_close_before_loss"] for x in items),
            "missing_or_censored_first_event_paths":
                 sum(x["missing_path"] for x in items)})
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--private-input",required=True)
    p.add_argument("--private-output",required=True)
    args=p.parse_args()
    data=json.load(open(args.private_input,encoding="utf8"))
    report=aggregate(data)
    with open(args.private_output,"x",encoding="utf8") as out:
        json.dump(report,out,sort_keys=True,indent=2)
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()