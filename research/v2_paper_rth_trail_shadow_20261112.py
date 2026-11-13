"""Research only: broker-filled entry + causal completed SIP 1m RTH exit-policy replay.
NO BROKER/DATA API REQUESTS; never implies an observed quote, limit fill or profit.
Only RTH MBB entrants are comparable. Historical NEWS_UNKNOWN is outcome-only.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
ENTRY_CUTOFF = time(13, 15)
RTH_OPEN_CT = time(8, 30)
FLAT_CT = time(13, 40)
PROXY_FRICTION = (0.003, 0.006)

@dataclass(frozen=True)
class Rule:
    name: str
    profit: float | None
    arm: float | None
    retrace: float | None
    loss: float = .01

RULES = (
    Rule("RTH_CURRENT_PROFIT1_TRAIL05", .01, .005, .005),
    Rule("PROFIT1_ARM1_TRAIL1", .01, .01, .01),
    Rule("PROFIT1_ARM1_TRAIL15", .01, .01, .015),
    Rule("PROFIT1_NO_TRAIL", .01, None, None),
    Rule("PROFIT15_ARM1_TRAIL1", .015, .01, .01),
    Rule("PROFIT15_ARM1_TRAIL15", .015, .01, .015),
    Rule("PROFIT15_NO_TRAIL", .015, None, None),
    Rule("NO_IMMEDIATE_PROFIT_ARM1_TRAIL1", None, .01, .01),
    Rule("NO_IMMEDIATE_PROFIT_ARM1_TRAIL15", None, .01, .015),
)

def loc(s: str) -> datetime:
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None: raise ValueError("Unaware timestamp")
    return d.astimezone(CT)

def ceil_minute(d: datetime) -> datetime:
    a=d.replace(second=0,microsecond=0)
    return a if d==a else a+timedelta(minutes=1)

def clean_input(fills_path: str, quotes_path: str):
    a=json.loads(Path(fills_path).read_text())
    b=json.loads(Path(quotes_path).read_text())
    if a.get("research_only") is not True or a.get("broker_orders_submitted")!=0:
        raise ValueError("Input must be GET-only research archive")
    if not isinstance(a.get("trades"),list) or not isinstance(a.get("bars"),dict) or not isinstance(b.get("quotes"),dict):
        raise ValueError("Invalid private archive")
    return a,b["quotes"]

def rth_entry(tr: dict) -> bool:
    t=loc(tr["entry_at"])
    return tr["source"]=="MBB" and RTH_OPEN_CT<=t.time()<ENTRY_CUTOFF

def full_path(tr: dict, series: list[dict]):
    buy=loc(tr["entry_at"])
    start=ceil_minute(buy)
    flat=buy.replace(hour=FLAT_CT.hour,minute=FLAT_CT.minute,second=0,microsecond=0)
    if start>=flat:return None,"AFTER_FLAT"
    bars={}
    for b in series:
        ts=loc(b["t"])
        if not (start<=ts and ts+timedelta(minutes=1)<=flat):continue
        if ts in bars:raise ValueError("duplicate timestamp")
        v=tuple(float(b[k]) for k in ("o","h","l","c"))
        if not (min(v)>0 and v[2]<=v[0]<=v[1] and v[2]<=v[3]<=v[1]):
            raise ValueError("corrupt OHLC")
        bars[ts]=b
    n=int((flat-start).total_seconds()//60)
    result=[]
    for i in range(n):
        ts=start+timedelta(minutes=i)
        if ts not in bars:return None,"MISSING_COMPLETE_1M_PATH"
        result.append((ts,bars[ts]))
    return result,"FULL"

def quote_at_flat(q: dict, qty: float):
    if q.get("status")!="FRESH_TIGHT_INDICATIVE_QUOTE":return None
    try:
        bid=float(q["bid"]);ask=float(q["ask"]);size=float(q["bid_size"])
    except (ValueError,KeyError,TypeError):return None
    if bid<=0 or ask<bid or (ask-bid)/ask>0.01 or size<qty:return None
    return bid

def decide(entry: float,bar: dict,peak: float, rule: Rule) -> str | None:
    close=float(bar["c"])
    change=close/entry-1
    if change<=-rule.loss:return "LOSS_CLOSE"
    if rule.profit is not None and change>=rule.profit:return "PROFIT_CLOSE"
    if (rule.arm is not None and rule.retrace is not None
        and peak>=entry*(1+rule.arm)
        and close/peak-1<=-rule.retrace):
        return "PEAK_REVERSAL"
    return None

def simulate(tr: dict,path,flatquote:float|None,rule:Rule):
    entry=float(tr["entry"]);qty=float(tr["qty"])
    peak=entry
    for i,(ts,b) in enumerate(path):
        peak=max(peak,float(b["h"]))
        reason=decide(entry,b,peak,rule)
        if reason is None:continue
        # The bar is known only at ts+1m; next minute OPEN is a hypothetical
        # immediately available trade mark, not a bid or proven limit fill.
        if i+1<len(path):
            next_ts,nextbar=path[i+1]
            if next_ts!=ts+timedelta(minutes=1):
                return {"status":"MISSING_NEXT_MINUTE_EXECUTION_MARK"}
            px=float(nextbar["o"])
            executed_at=next_ts
            source="NEXT_MINUTE_OPEN_MARK_NOT_EXECUTABLE"
        else:
            px=flatquote
            executed_at=ts+timedelta(minutes=1)
            source="FLAT_BID_PROXY" if px is not None else "UNVERIFIED_FLAT_QUOTE"
        if px is None:return {"status":"UNVERIFIED_EXECUTABLE_MARK"}
        # Excursions must stop AT the causal decision, never include bars
        # after a hypothetical completed exit. Next-open is an execution
        # mark, not a later intra-minute high/low.
        visible=[v for _,v in path[:i+1]]
        mae=min(float(v["l"]) for v in visible)/entry-1
        mfe=max(float(v["h"]) for v in visible)/entry-1
        return {"status":"PRICE_MARK_PROXY","reason":reason,"exit_ct":executed_at.isoformat(),
           "price_basis":source,"minutes":round((executed_at-loc(tr["entry_at"])).total_seconds()/60,3),
           "gross_proxy":(px-entry)*qty,
           "returns_proxy":[(px-entry)*qty-rt*entry*qty for rt in PROXY_FRICTION],
           "mae_pct":mae*100,"mfe_pct":mfe*100}
    if flatquote is None:return {"status":"NO_VERIFIED_1340_BID"}
    mae=min(float(v["l"]) for _,v in path)/entry-1
    mfe=max(float(v["h"]) for _,v in path)/entry-1
    exit_at=path[-1][0]+timedelta(minutes=1)
    return {"status":"PRICE_MARK_PROXY","reason":"MANDATORY_FLAT","exit_ct":exit_at.isoformat(),
      "price_basis":"FLAT_BID_PROXY_NOT_PROVEN_EXECUTION",
      "minutes":round((exit_at-loc(tr["entry_at"])).total_seconds()/60,3),
      "gross_proxy":(flatquote-entry)*qty,
      "returns_proxy":[(flatquote-entry)*qty-rt*entry*qty for rt in PROXY_FRICTION],
      "mae_pct":mae*100,"mfe_pct":mfe*100}

def evaluate(caches):
    records=[];accounts=set();bars={};flat={};seen=set()
    for p,q in caches:
        obj,marks=clean_input(p,q)
        accounts.add(obj.get("scope","UNSPECIFIED_VERIFIED_ACCOUNT"))
        for tr in obj["trades"]:
            # A pair of filled orders is ONE round trip, not one per FILL activity.
            k=(tr["source"],tr["day"],tr["symbol"],tr["entry_order_id"],tr["exit_order_id"])
            if k in seen:raise ValueError("duplicate broker round trip in source data")
            seen.add(k)
            records.append(tr)
        for key,v in obj["bars"].items():
            if key in bars:raise ValueError("overlapping SIP day-symbol cache")
            bars[key]=v
        for key,v in marks.items():
            if key in flat:raise ValueError("overlapping quoted flat cache")
            flat[key]=v
    selected=[r for r in records if rth_entry(r)]
    results=[]
    for tr in selected:
        key=tr["day"]+"|"+tr["symbol"]
        path,status=full_path(tr,bars.get(key,[]))
        quote=quote_at_flat(flat.get(key,{}),float(tr["qty"]))
        if status!="FULL":
            results.append({"source":tr["source"],"day":tr["day"],"symbol":tr["symbol"],
                "status":status})
            continue
        observed={rule.name:simulate(tr,path,quote,rule) for rule in RULES}
        eligible_all=all(v.get("status")=="PRICE_MARK_PROXY" for v in observed.values())
        results.append({"source":tr["source"],"day":tr["day"],"symbol":tr["symbol"],
          "status":"ALL_MODELS_ELIGIBLE" if eligible_all else "INCOMPLETE_MODEL_COVERAGE",
          "actual_gross":(float(tr["exit"])-float(tr["entry"]))*float(tr["qty"]),
          "actual_hold_minutes":round((loc(tr["exit_at"])-loc(tr["entry_at"])).total_seconds()/60,3),
          "observed":observed})
    full=[r for r in results if r["status"]=="ALL_MODELS_ELIGIBLE"]
    aggregate={"audit_kind":"NO_TRADE_RESEARCH","historical_news_eligibility":"NEWS_UNKNOWN",
      "observed_sessions":sorted({tr["day"] for tr in selected}),
      "all_broker_paired_round_trips":len(records),
      "rth_mbb_entries":len(selected),
      "rth_eligible_all_models":len(full),
      "rth_incomplete":dict(Counter(x["status"] for x in results if x["status"]!="ALL_MODELS_ELIGIBLE")),
      "other_premarket_or_source_excluded":len(records)-len(selected),
      "source_account_scopes":sorted(accounts),
      "original_gross_realized_on_equal_sample":round(sum(r["actual_gross"] for r in full),2),
      "model":{},"per_day":{}}
    for rule in RULES:
        vals=[r["observed"][rule.name] for r in full]
        original=[r["actual_gross"] for r in full]
        meanmin=sum(v["minutes"] for v in vals)/len(vals) if vals else None
        net_records=sorted(((loc(v["exit_ct"]),v["returns_proxy"][0])
            for v in vals),key=lambda z:z[0])
        equity=0.0;peak_equity=0.0;max_drawdown=0.0
        for _,ret in net_records:
            equity+=ret
            peak_equity=max(peak_equity,equity)
            max_drawdown=max(max_drawdown,peak_equity-equity)
        stats={"denominator":len(vals),
         "modeled_max_realized_drawdown_30bp_usd":round(max_drawdown,2),
         "worst_modeled_trade_30bp_usd":round(min((v["returns_proxy"][0] for v in vals),default=0),2),
         "modeled_wins_after_30bp":sum(v["returns_proxy"][0]>0 for v in vals),
         "gross_mark_pnl":round(sum(v["gross_proxy"] for v in vals),2),
         "net_30bp_proxy_pnl":round(sum(v["returns_proxy"][0] for v in vals),2),
         "net_60bp_proxy_pnl":round(sum(v["returns_proxy"][1] for v in vals),2),
         "mean_hold_minutes":round(meanmin,2) if meanmin is not None else None,
         "worse_than_actual_gross_fill":sum(v["gross_proxy"]<o for v,o in zip(vals,original)),
         "reason_counts":dict(Counter(v["reason"] for v in vals)),
         "mean_MAE_pct":round(sum(v["mae_pct"] for v in vals)/len(vals),3) if vals else None,
         "mean_MFE_pct":round(sum(v["mfe_pct"] for v in vals)/len(vals),3) if vals else None}
        # No independent liquidity proof from bars; drawdown is gross mark-to-mark.
        aggregate["model"][rule.name]=stats
        aggregate["per_day"][rule.name]={day:{
           "n":len([r for r in full if r["day"]==day]),
           "net_30bp_proxy":round(sum(r["observed"][rule.name]["returns_proxy"][0] for r in full if r["day"]==day),2)}
           for day in aggregate["observed_sessions"]}
    return aggregate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--cache",nargs=2,action="append",required=True,metavar=("PAIRED_FILLED_TRADES_AND_SIP","FLAT_QUOTES"))
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    out=Path(args.output)
    if out.exists():raise SystemExit("Refusing to overwrite outcome")
    a=evaluate(args.cache)
    out.write_text(json.dumps(a,indent=2,sort_keys=True))
    print(json.dumps(a,sort_keys=True))

if __name__=="__main__":main()
