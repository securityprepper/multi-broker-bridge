"""Research-only completed-minute trade-mark exit replay; NOT broker executable.
Conservative stop-first within an ambiguous candle, decision after candle complete,
then next bar OPEN as a mark. Never reconstructs an original exit reason.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo
import json,statistics
CT=ZoneInfo("America/Chicago")
ROOT=Path("/tmp/v2-rapid-exit-run6-20261111")
FLAT_HOUR=13
FLAT_MINUTE=40
def time(s): return datetime.fromisoformat(s).astimezone(CT)
def from_data():
    z=json.loads((ROOT/"raw_research_private.json").read_text())
    assert z["research_only"] is True and z["broker_orders_submitted"]==0
    return z
def eligible_bars(trade,dat):
    entry=time(trade["entry_at"]); flat=datetime.fromisoformat(trade["day"]+"T13:40:00-06:00")
    bars=dat.get(trade["day"]+"|"+trade["symbol"],[])
    allowed=[]
    for row in bars:
        ts=time(row["t"])
        if ts>=entry and ts+timedelta(minutes=1)<=flat:
            allowed.append((ts,row))
    allowed.sort(key=lambda x:x[0])
    if not allowed:return [],"NO_COMPLETED_POST_ENTRY_BARS"
    # A bar containing the original buy cannot be used; must start strictly after fill.
    expected=entry.replace(second=0,microsecond=0)+timedelta(minutes=1)
    if allowed[0][0]>expected+timedelta(minutes=2):
        return allowed,"FIRST_POST_ENTRY_QUOTE_GAP"
    for (a,_),(b,_) in zip(allowed,allowed[1:]):
        if b-a>timedelta(minutes=1):
            return allowed,"MISSING_INTRA_SESSION_MINUTE"
    if allowed[-1][0] != flat-timedelta(minutes=1):
        return allowed,"NO_1340_COMPLETED_CLOSE"
    return allowed,"SIP_TRADE_BARS_CONTINUOUS"
def outcome(trade,dat,target,stop,minhold,trail=None):
    entry=time(trade["entry_at"])
    bars,quality=eligible_bars(trade,dat)
    if quality!="SIP_TRADE_BARS_CONTINUOUS":
        return {"status":"UNKNOWN_PATH","quality":quality}
    px=trade["entry"];qty=trade["qty"]
    future=[dict(t=t,row=v) for t,v in bars]
    high=px
    stop_first=0
    for idx,o in enumerate(future):
        tm,row=o["t"],o["row"];high=max(high,row["h"])
        duration=(tm-entry).total_seconds()/60
        emergency=row["l"]<=px*.975
        possible=tm>=entry+timedelta(minutes=minhold)
        target_hit=possible and row["h"]>=px*(1+target/100)
        stop_hit=possible and row["l"]<=px*(1-stop/100)
        # Trailing only after first 10 minutes and at least +1% actual favorable
        # completed-minute high. 1/1.5% trail compared with highest seen.
        trailing=trail is not None and duration>=10 and high>=px*1.01 and row["l"]<=high*(1-trail/100)
        if not(emergency or target_hit or stop_hit or trailing):continue
        if idx+1>=len(future):
            return {"status":"UNKNOWN_NO_NEXT_BAR_EXECUTION"}
        next_bar=future[idx+1]
        if next_bar["t"] != tm+timedelta(minutes=1):
            return {"status":"UNKNOWN_NEXT_MINUTE_MISSING"}
        # Intentionally NOT a broker fill: 1m trade-bar next open is only a price mark.
        mark=next_bar["row"]["o"]
        if emergency:why="EMERGENCY_2_5"
        elif stop_hit:why="STOP_FIRST" if target_hit else "STOP"
        elif trailing:why="TRAIL"
        else:why="TARGET"
        return {"status":"PRICE_MARK_PROXY","why":why,"trigger_at_CT":(tm+timedelta(minutes=1)).isoformat(),
                "mark_at_CT":next_bar["t"].isoformat(),"exit_mark":mark,
                "gross_proxy_usd":(mark-px)*qty,
                "minutes_in_market_proxy":(next_bar["t"]-entry).total_seconds()/60,
                "ambiguous_both_intrabar":bool(stop_hit and target_hit)}
    # No threshold condition; fixed 13:40 CT trade-bar CLOSE mark.
    row=future[-1]["row"]
    mark=row["c"]
    return {"status":"PRICE_MARK_PROXY","why":"FORCED_FLAT_MARK",
            "mark_at_CT":(future[-1]["t"]+timedelta(minutes=1)).isoformat(),
            "exit_mark":mark,"gross_proxy_usd":(mark-px)*qty,
            "minutes_in_market_proxy":(future[-1]["t"]+timedelta(minutes=1)-entry).total_seconds()/60,
            "ambiguous_both_intrabar":False}
def summarize(z):
    tr=z["trades"];bars=z["bars"]
    total=len(tr)
    all_scenarios=[]
    for target in (.5,1,1.5,2):
      for stop in (.5,1,1.5,2,2.5):
       for minhold in (0,5,10,15,30):
        output=[outcome(t,bars,target,stop,minhold) for t in tr]
        eligible=[(t,x) for t,x in zip(tr,output) if x["status"]=="PRICE_MARK_PROXY"]
        n=len(eligible)
        res={"target_pct":target,"stop_pct":stop,"min_hold_minutes":minhold,
            "trades_total":total,"price_mark_scored":n,"missing":total-n,
            "distinct_days":len(set(t["day"] for t,x in eligible)),
            "gross_proxy_usd":round(sum(x["gross_proxy_usd"] for t,x in eligible),2),
            "wins_proxy":sum(x["gross_proxy_usd"]>0 for t,x in eligible),
            "losses_proxy":sum(x["gross_proxy_usd"]<0 for t,x in eligible),
            "ambiguous_stop_first":sum(x["ambiguous_both_intrabar"] for t,x in eligible),
            "min_proxy_usd":round(min((x["gross_proxy_usd"] for t,x in eligible),default=0),2),
            "mean_minutes":round(statistics.mean([x["minutes_in_market_proxy"] for t,x in eligible]),2) if eligible else None,
            "reason_counts":dict(__import__("collections").Counter(x["why"] for t,x in eligible))}
        # 30 bp roundtrip modeled friction, not observed actual costs.
        res["after_30bp_proxy_usd"]=round(
            sum(x["gross_proxy_usd"]-0.003*t["entry"]*t["qty"] for t,x in eligible),2)
        res["after_30bp_proxy_win_count"]=sum(
            x["gross_proxy_usd"]-0.003*t["entry"]*t["qty"]>0 for t,x in eligible)
        all_scenarios.append(res)
    # Always compare exit hypotheses on the IDENTICAL source trades. Different
    # trigger patterns may otherwise create spurious winners by dropping a case.
    scenario_matrix=[]
    common=set(range(total))
    for p in all_scenarios:
        yy=[outcome(t,bars,p["target_pct"],p["stop_pct"],p["min_hold_minutes"]) for t in tr]
        scenario_matrix.append(yy)
        common &= {i for i,x in enumerate(yy) if x["status"]=="PRICE_MARK_PROXY"}
    common=sorted(common)
    comparable=[]
    for p,yy in zip(all_scenarios,scenario_matrix):
        chosen=[(tr[i],yy[i]) for i in common]
        comparable.append({"target_pct":p["target_pct"],"stop_pct":p["stop_pct"],
              "min_hold_minutes":p["min_hold_minutes"],"common_n":len(common),
              "common_days":len({t["day"] for t,x in chosen}),
              "after_30bp_mark_usd":round(sum(x["gross_proxy_usd"]-0.003*t["entry"]*t["qty"] for t,x in chosen),2),
              "mark_after30bp_wins":sum(x["gross_proxy_usd"]-0.003*t["entry"]*t["qty"]>0 for t,x in chosen)})
    comparable.sort(key=lambda a:(a["target_pct"],a["stop_pct"],a["min_hold_minutes"]))
    baseline=sorted((t["day"],t["source"],t["symbol"],t["entry"]) for t in tr)
    outcomes={str(k):dict(__import__("collections").Counter(x.get("quality",x["status"]) for x in
                        [outcome(t,bars,1,1,k) for t in tr])) for k in (0,10,30)}
    # no optimization; surface quantiles and ranges only as hypothesis sensitivity
    scored=[x for x in all_scenarios if x["missing"]==all_scenarios[0]["missing"]]
    scored.sort(key=lambda o:o["after_30bp_proxy_usd"])
    baseline_now={"n_trades":len(tr),"n_days":len({t["day"] for t in tr}),
           "actual_gross_usd":round(sum((t["exit"]-t["entry"])*t["qty"] for t in tr),2),
           "model_type":"NEXT_COMPLETED_1MIN_TRADE_BAR_OPEN_NOT_EXECUTABLE_FILL",
           "not_a_trade_policy":True,"news_eligibility_for_historical_buys":"NOT_EVALUATED_NEWS_UNKNOWN"}
    return {"scope":baseline_now,"quality":outcomes,
       "identical_common_sample":{"n":len(common),"all_100_scenarios":comparable,"posthoc_optimization_prohibited":True},
       "scenario_count":len(all_scenarios),
       "sensitivity_only_no_selection":{
          "worst_after_30bp_proxy_usd":scored[0]["after_30bp_proxy_usd"] if scored else None,
          "best_after_30bp_proxy_usd":scored[-1]["after_30bp_proxy_usd"] if scored else None,
          "median_after_30bp_proxy_usd":statistics.median(x["after_30bp_proxy_usd"] for x in scored) if scored else None,
          "warning":"GRIDS ARE POSTHOC; DO NOT SELECT OR RECOMMEND A WINNER"},
       "examples":{str((tg,st,hold)):next(
           (v for v in all_scenarios if (v["target_pct"],v["stop_pct"],v["min_hold_minutes"])==(tg,st,hold)),None)
          for tg,st,hold in ((1,1,0),(1.5,2.5,10),(2,2.5,30),(.5,.5,0))},
       "all_scenarios":all_scenarios}
if __name__=="__main__":
    d=from_data(); res=summarize(d)
    out=ROOT/"grid_stress_common_results_private.json"
    if out.exists():raise RuntimeError("cannot rewrite grid results")
    out.write_text(json.dumps(res,indent=2))
    print("SCENARIO_RUN",json.dumps({k:v for k,v in res.items() if k!="all_scenarios"},sort_keys=True))
