"""V2-only paired studies: regular-open weakness blind spots; causal sector entry caps.

No broker connections or order execution. Five-minute SIP OHLC is never a fill.
All rules are observed at COMPLETED 5-minute candles. Future data score only.
Fixed threshold sensitivity is reported, not tuned on the later holdout.
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean

from research.v2_stock_risk_dayphase import ET, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_rth_open_momentum import first_signal as first_up
from research.v2_locked_exit_policy_walkforward import policy_outcome, LATER
from research.v2_downside_early_sell_opportunity_cost import price_scenario

T5 = timedelta(minutes=5)
OPEN = time(9, 30)
THRESHOLDS = ((1.0, False), (1.5, False), (2.5, False),
              (1.0, True), (1.5, True))

def at_open_relative_move(bars, day, symbol, observed_at, *, sector=False):
    """Only prices observable by observed_at; no session close or future bar."""
    if observed_at.tzinfo is None:
        raise ValueError("timezone required")
    at = observed_at.astimezone(ET)
    if at.date() != day or not (time(9, 35) <= at.time() <= time(10, 30)):
        return None
    if at.minute % 5 or at.second or at.microsecond:
        return None
    start = at - T5
    openrow = bars.get(symbol, {}).get(datetime.combine(day, OPEN, ET))
    row = bars.get(symbol, {}).get(start)
    if not openrow or not row or min(openrow[0], row[3]) <= 0:
        return None
    own = 100 * (row[3]/openrow[0] - 1)
    soxx = None
    if sector:
        op = bars.get("SOXX", {}).get(datetime.combine(day, OPEN, ET))
        cur = bars.get("SOXX", {}).get(start)
        if not op or not cur or min(op[0], cur[3]) <= 0:
            return None
        soxx = 100 * (cur[3]/op[0] - 1)
    return own, soxx, row[3]

def first_open_decline(bars, day, symbol, threshold, sector=False):
    """First eligible completed-bar decline vs 9:30 OPEN (not prior CLOSE).

    The optional SOXX filter requires a decline from SOXX's open >=0.25%.
    """
    if threshold <= 0 or threshold > 10:
        raise ValueError("unreasonable threshold")
    for minute in range(9*60+35, 10*60+31, 5):
        at = datetime.combine(day, time(minute//60, minute%60), ET)
        observed = at_open_relative_move(bars, day, symbol, at, sector=sector)
        if observed is None:
            continue
        own, soxx, price = observed
        if own > -threshold or (sector and soxx > -0.25):
            continue
        follow = bars[symbol].get(at)
        return {"asof":at.isoformat(), "source":"rth_open_decline",
                "signal_price":price,
                "own_from_open_pct":round(own, 4),
                "soxx_from_open_pct":round(soxx,4) if soxx is not None else None,
                "next_bar_open":follow[0] if follow else None}
    return None

def earliest(*items):
    return min((x for x in items if x), key=lambda x:x["asof"], default=None)

def decline_study(bars, daily, baseline_audit):
    universe, calendar = all_days(bars, daily)
    baseline = {(r["day"],r["sym"]):r for r in baseline_audit}
    if {(r["day"],r["sym"]) for r in universe} != set(baseline):
        raise ValueError("daily baseline audit / source universe mismatch")
    sessions = [date.fromisoformat(x) for x in calendar]
    nextday = dict(zip(sessions[:-1], sessions[1:]))
    results={}
    missed_details=[]
    baseline_hits=[r for r in baseline_audit if r["major_down"] and r["all_union"]]
    for threshold,sector in THRESHOLDS:
        label=f"open_{str(threshold).replace('.','p')}" + ("_soxx" if sector else "")
        events=[]
        for row in universe:
            d=date.fromisoformat(row["day"])
            sym=row["sym"]
            key=(row["day"], sym)
            base=baseline[key]["all_union"]
            new=first_open_decline(bars,d,sym,threshold,sector=sector)
            combined=earliest(base,new)
            if not new and not combined:continue
            next_d=nextday.get(d)
            next_open_bar=(bars[sym].get(datetime.combine(next_d,OPEN,ET))
                           if next_d else None)
            future_open=next_open_bar[0] if next_open_bar else None
            new_price_scenario=(price_scenario(new,row["previous_close"],future_open)
                                if new else None)
            if new:
                event={"day":row["day"],"sym":sym,"major_down":row["big_down"],
                       "major_up":row["big_up"],"change_pct":row["change_pct"],
                       "new":new, "base":base, "combined":combined,
                       "before_minus5":100*(new["signal_price"]/row["previous_close"]-1)>-5,
                       "sell_vs_next_open":new_price_scenario}
                events.append(event)
        major=[r for r in events if r["major_down"]]
        added=[r for r in events if r["major_down"] and not r["base"]]
        false=[r for r in events if not r["major_down"]]
        one=[]
        for period in ("earlier","later"):
            selected=[r for r in events if (date.fromisoformat(r["day"])<LATER)==(period=="earlier")]
            priced=[r["sell_vs_next_open"]["advantage_to_next_open_pp"] for r in selected
                    if r["sell_vs_next_open"] is not None]
            major_priced=[r["sell_vs_next_open"]["advantage_to_next_open_pp"]
                          for r in selected if r["major_down"] and r["sell_vs_next_open"] is not None]
            other_priced=[r["sell_vs_next_open"]["advantage_to_next_open_pp"]
                          for r in selected if not r["major_down"] and r["sell_vs_next_open"] is not None]
            one.append((period,{"warnings":len(selected),
                "major_mean_sale_benefit_pp":round(mean(major_priced),4) if major_priced else None,
                "nonmajor_mean_sale_benefit_pp":round(mean(other_priced),4) if other_priced else None,
                "major_hits":sum(r["major_down"] for r in selected),
                "nonmajor":sum(not r["major_down"] for r in selected),
                "mean_sell_vs_nextopen_pp":round(mean(priced),4) if priced else None,
                "price_scorable":len(priced),
                "price_eligible_proxy":sum(r["sell_vs_next_open"]["eligible_price_proxy"]
                           for r in selected if r["sell_vs_next_open"] is not None)}))
        incremental_nonmajor=sum(not r["major_down"] and not r["base"] for r in events)
        severe_earlier=sum(r["major_down"] and (r["base"] is None or
                        r["new"]["asof"] < r["base"]["asof"]) for r in events)
        results[label]={"new_warnings":len(events),"new_major_hits":len(major),
           "new_nonmajor":len(false),"new_on_major_winner":sum(r["major_up"] for r in events),
           "incremental_nonmajor_to_union":incremental_nonmajor,
           "union_nonmajor":sum(bool(r["all_union"]) and not r["major_down"] for r in baseline_audit)+incremental_nonmajor,
           "new_earlier_than_union_for_major":severe_earlier,
           "new_before_already_down5":sum(r["before_minus5"] for r in major),
           "previous_union_miss_newly_detected":len(added),
           "previous_union_miss_before_down5":sum(r["before_minus5"] for r in added),
           "union_major_hits":len(baseline_hits)+len(added),
           "union_major_misses":sum(r["big_down"] for r in universe)-len(baseline_hits)-len(added),
           "new_earliest_major_warning":min((r["new"]["asof"] for r in major),default=None),
           "periods":dict(one),
           "added_misses":[{"day":r["day"],"symbol":r["sym"],"close_pct":r["change_pct"],
                           "at":r["new"]["asof"],
                           "own_from_open_pct":r["new"]["own_from_open_pct"],
                           "before_already_minus5":r["before_minus5"]}
                          for r in added]}
        if (threshold,sector)==(1.5,False):
            missed_details=results[label]["added_misses"]
    return {"stockdays":len(universe),"major_down":sum(r["big_down"] for r in universe),
            "major_up":sum(r["big_up"] for r in universe),
            "baseline_union_major_hits":len(baseline_hits),
            "baseline_union_nonmajor":sum(bool(r["all_union"]) and not r["major_down"]
                                           for r in baseline_audit),
            "alternatives":results,"missed_details_1p5":missed_details,
            "baseline_major_misses":[{"day":r["day"],"symbol":r["sym"],
                                     "close_pct":r["close_pct"]} for r in baseline_audit
                                     if r["major_down"] and not r["all_union"]]}

def cap_admissions(events, cap):
    """Choose only earliest cap first-hour alerts, tie-break by observed strength.
    Sorting/scoring never references later bar prices or day-close labels.
    """
    if cap is not None and cap < 1:
        raise ValueError("invalid cap")
    ordered=sorted(events,key=lambda r:(r["at"],-r["own_open_pct"],r["sym"]))
    return ordered[:cap] if cap is not None else ordered

def admission_study(bars,daily):
    universe,_=all_days(bars,daily)
    records=defaultdict(list)
    for r in universe:
        sym=r["sym"]; day=date.fromisoformat(r["day"])
        sig=first_up(bars,day,sym,"early_1030")
        if sig is None:
            continue
        records[r["day"]].append({"day":r["day"],"sym":sym,"at":sig["at"],
            "own_open_pct":sig["own_open_pct"],
            "major_up":r["big_up"],"major_down":r["big_down"],
            "result":policy_outcome(bars[sym],sig,r["mark14"],"hold_1400")})
    out={"signal_days":len(records),"signals":sum(map(len,records.values())),"policies":{}}
    for cap in (None,1,2,3):
        label="all" if cap is None else f"first_{cap}"
        drows=[]
        chosen=[]
        for d,day_events in records.items():
            selected=cap_admissions(day_events,cap)
            chosen.extend(selected)
            returns=[e["result"]["net_pct"] if e["result"] else 0.0 for e in selected]
            drows.append({"day":d,"ret":mean(returns) if returns else 0.0})
        summaries={}
        for period in ("earlier","later","all"):
            eligible=[r for r in drows if period=="all" or
                      (date.fromisoformat(r["day"])<LATER)==(period=="earlier")]
            selected=[r for r in chosen if period=="all" or
                      (date.fromisoformat(r["day"])<LATER)==(period=="earlier")]
            summaries[period]={"days":len(eligible),"selected_signals":len(selected),
                "day_equal_pct":round(mean(r["ret"] for r in eligible),4) if eligible else None,
                "winning_days":sum(r["ret"]>0 for r in eligible),
                "losing_days":sum(r["ret"]<0 for r in eligible),
                "major_up_signals_retained":sum(r["major_up"] for r in selected),
                "major_down_signals_retained":sum(r["major_down"] for r in selected),
                "eligible_price_proxy":sum(e["result"] is not None and
                    e["result"]["eligible_entry"] for e in selected)}
        out["policies"][label]=summaries
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--audit",default="/tmp/v2-run10-daily-audit.json")
    args=p.parse_args()
    bars=ingest(("/tmp/semis_52wk_5min_sip_adjusted.json",
                 "/tmp/semis_peers_52wk_5min_adjusted.json"))
    daily=json.loads(Path("/tmp/semis_52weeks_alpaca_daily.json").read_text())["split"]
    baseline=json.loads(Path(args.audit).read_text())
    results={"downside":decline_study(bars,daily,baseline),
             "opportunities":admission_study(bars,daily),
             "data_limitations":"No actual SIP/BOATS NBBO, futures/news, V1 fills, other-sector sample."}
    Path(args.output).write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print(json.dumps(results,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
