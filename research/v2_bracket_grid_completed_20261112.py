"""Research-only Alpaca PAPER 1m completed-close bracket counterfactual.
No network, no broker/order API, no V1 mutation. All price results are MARK PROXIES.
"""
from __future__ import annotations
import collections
import datetime as dt
import json
import math
import statistics
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

CHI=ZoneInfo("America/Chicago")
UTC=dt.timezone.utc
TARGETS=(0.5,1.0,1.5,2.0)
STOPS=(0.5,1.0,1.5,2.0,2.5)
HOLDS=(0,5,10,15,30)
FRICTION_PCT=0.30

def parse(s):
    x=dt.datetime.fromisoformat(s.replace("Z","+00:00"))
    if x.tzinfo is None: raise ValueError("timezone missing")
    return x.astimezone(UTC)

def ceil_minute(t):
    floor=t.replace(second=0,microsecond=0)
    return floor if t==floor else floor+dt.timedelta(minutes=1)

def prepare(trades, bars):
    seen=set()
    for t in trades:
        key=(t["entry_order_id"],t["exit_order_id"])
        if not all(key) or key in seen or key[0]==key[1]:
            raise ValueError("duplicate/crossed filled order ID")
        seen.add(key)
        start=parse(t["entry_at"]); end=parse(t["exit_at"])
        if end <= start or t["day"]!=start.astimezone(CHI).date().isoformat():
            raise ValueError("bad historical filled timestamps")
        if t["source"] not in ("MBB","FDR"):raise ValueError("unknown source")
        key=t["day"]+"|"+t["symbol"]
        seq=bars.get(key,[])
        mapped={}
        for row in seq:
            stamp=parse(row["t"])
            if stamp in mapped: raise ValueError("duplicate bar")
            v={k:float(row[k]) for k in ("o","h","l","c")}
            if not all(math.isfinite(x) and x>0 for x in v.values()):
                raise ValueError("malformed OHLC")
            if not v["l"]<=min(v["o"],v["c"])<=max(v["o"],v["c"])<=v["h"]:
                raise ValueError("inconsistent OHLC")
            mapped[stamp]=v
        yield t,start,mapped

def simulate_one(t,start,bars,target,stop,hold):
    if target<=0 or stop<=0 or hold<0:raise ValueError("bad thresholds")
    ep=float(t["entry"]); q=float(t["qty"])
    if ep<=0 or q<=0:raise ValueError("invalid filled basis")
    floor=start.astimezone(CHI).replace(hour=13,minute=40,second=0,microsecond=0).astimezone(UTC)
    if start>=floor:return {"status":"PAST_FLAT"}
    first=ceil_minute(start)
    tcur=first
    high=-float("inf");low=float("inf");ambiguous=0; n=0
    target_px=ep*(1+target/100)
    stop_px=ep*(1-stop/100)
    emergency_px=ep*(1-2.5/100)
    while tcur < floor:
        b=bars.get(tcur)
        if b is None:return {"status":"MISSING_1M","minutes_checked":n}
        n+=1
        high=max(high,b["h"]);low=min(low,b["l"])
        if b["h"]>=target_px and b["l"]<=stop_px:ambiguous+=1
        finished=tcur+dt.timedelta(minutes=1)
        elapsed=(finished-start).total_seconds()/60
        reason=None
        # Continuous emergency risk is never suppressed by a minimum hold,
        # but this completed-close proxy cannot guarantee an intraminute stop.
        if b["c"]<=emergency_px: reason="EMERGENCY_CLOSE"
        elif elapsed>=hold and b["c"]<=stop_px: reason="STOP_CLOSE"
        elif elapsed>=hold and b["c"]>=target_px: reason="TARGET_CLOSE"
        if reason is not None:
            # The decision cannot execute before the observed minute completes.
            if finished>floor:return {"status":"PAST_FLAT"}
            nxt=bars.get(finished)
            if nxt is None:return {"status":"NO_NEXT_MINUTE_OPEN","minutes_checked":n}
            return modeled(t,start,finished,nxt["o"],reason,high,low,ambiguous,n)
        tcur=finished
    last=bars.get(floor)
    if last is None:return {"status":"NO_FLAT_BAR"}
    return modeled(t,start,floor,last["o"],"FLAT_1340_MARK",high,low,ambiguous,n)

def modeled(t,start,end,px,reason,high,low,ambiguous,n):
    entry=float(t["entry"]); qty=float(t["qty"])
    raw=(px-entry)*qty
    cost=entry*qty*FRICTION_PCT/100
    profit=raw-cost
    return {
      "status":"MARK_PROXY_ONLY","reason":reason,
      "gross_proxy_usd":raw,"after_assumed_friction_usd":profit,
      "return_after_assumed_friction_pct":100*(px/entry-1)-FRICTION_PCT,
      "mae_pct":100*(low/entry-1) if n else None,
      "mfe_pct":100*(high/entry-1) if n else None,
      "ambiguous_intrabar_target_stop_bars":ambiguous,
      "minutes_in_market":(end-start).total_seconds()/60,
      "bars_checked":n
    }

def summarize(results):
    ok=[x for x in results if x["status"]=="MARK_PROXY_ONLY"]
    reasons=collections.Counter(x["reason"] for x in ok)
    unknown=collections.Counter(x["status"] for x in results if x["status"]!="MARK_PROXY_ONLY")
    values=[x["after_assumed_friction_usd"] for x in ok]
    if not values:return {"n":len(results),"scorable_mark_proxy":0,"unknown":dict(unknown)}
    return {
      "n":len(results),"scorable_mark_proxy":len(ok),"unknown":dict(unknown),
      "winning_mark_proxies_after30bp":sum(v>0 for v in values),
      "gross_mark_proxy_usd":round(sum(x["gross_proxy_usd"] for x in ok),2),
      "after30bp_mark_proxy_usd":round(sum(values),2),
      "mean_after30bp_mark_return_pct":round(statistics.mean(x["return_after_assumed_friction_pct"] for x in ok),5),
      "min_after30bp_mark_return_pct":round(min(x["return_after_assumed_friction_pct"] for x in ok),5),
      "max_adverse_bar_pct":round(min(x["mae_pct"] for x in ok if x["mae_pct"] is not None),5),
      "max_favorable_bar_pct":round(max(x["mfe_pct"] for x in ok if x["mfe_pct"] is not None),5),
      "median_mark_minutes":round(statistics.median(x["minutes_in_market"] for x in ok),2),
      "reasons":dict(reasons),
      "paths_with_same_bar_target_stop_ambiguity":sum(x["ambiguous_intrabar_target_stop_bars"]>0 for x in ok),
      "verified_executable_alternative_exits":0,
    }

def analyze(data):
    if not data.get("research_only") or data.get("broker_orders_submitted")!=0:raise ValueError("wrong cohort")
    rows=list(prepare(data["trades"],data["bars"]))
    result={}
    for src in ("ALL","MBB","FDR"):
        filt=[r for r in rows if src=="ALL" or r[0]["source"]==src]
        for hold in HOLDS:
            for target in TARGETS:
                for stop in STOPS:
                    label=f"hold{hold}_target{target}_stop{stop}"
                    result[(src,label)]=summarize([simulate_one(t,start,b,target,stop,hold) for t,start,b in filt])
    # Cohort precommitted comparisons, not best-of-grid cherry picking.
    anchors={label:result[("ALL",label)] for label in (
      "hold0_target1.0_stop1.0","hold5_target1.0_stop1.0",
      "hold10_target1.0_stop1.0","hold15_target1.0_stop1.0",
      "hold30_target1.0_stop1.0","hold0_target2.0_stop2.5",
      "hold30_target2.0_stop2.5")}
    perhold={}
    for hold in HOLDS:
        candidates=[result[("ALL",f"hold{hold}_target{target}_stop{stop}")]
                    for target in TARGETS for stop in STOPS]
        perhold[str(hold)]={
          "grid_size":len(candidates),
          "minimum_scorable_marks":min(x.get("scorable_mark_proxy",0) for x in candidates),
          "maximum_scorable_marks":max(x.get("scorable_mark_proxy",0) for x in candidates),
          "scenario_counts_with_any_unknown":sum(x.get("unknown")!={} for x in candidates),
          "scenario_counts_zero_verifiable_alternative_exits":len(candidates),
          "illustrative_sums_range_usd":[min(x.get("after30bp_mark_proxy_usd",0) for x in candidates),
                                         max(x.get("after30bp_mark_proxy_usd",0) for x in candidates)],
        }
    return {
      "historical_distinct_days":len({t["day"] for t,_,_ in rows}),
      "broker_verified_roundtrips":len(rows),
      "grid_scenarios_all":len(TARGETS)*len(STOPS)*len(HOLDS),
      "grid_scenarios_per_source":len(TARGETS)*len(STOPS)*len(HOLDS),
      "causal_method":"entry-fill -> first entirely post-entry completed 1m close -> next minute OPEN mark -> mandatory 13:40 Chicago flat; emergency 2.5% close overrides minimum hold",
      "no_quotes_or_executable_alternatives_proven":True,
      "historical_bars_not_intrabar_executable_ordering":True,
      "actual_exit_reasons_not_assigned":True,
      "precommitted_anchors":anchors,
      "hold_group_coverage":perhold,
      "source_anchor":{src:result[(src,"hold10_target1.0_stop1.0")] for src in ("MBB","FDR")},
      "paper_live_orders":0,"new_policy_go":False
    }

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:raise SystemExit("Private prior verified research ledger argument required")
    data=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(analyze(data),sort_keys=True,indent=2))