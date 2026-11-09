"""Causal prior-five sector context for PREMARKET V2 weakness warnings.

Research only; no broker orders or network access. Retrospective >=5%-loss
labels and 09:30 open are scoring only, never warning conditions.
"""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
from statistics import mean

from research.v2_stock_risk_dayphase import collect, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_prior5_cohort_stress import five_completed_return, LATER_START

def summary(rows):
    major = [r for r in rows if r["big_loss"]]
    warned = [r for r in rows if r["pre_asof"]]
    major_warn = [r for r in warned if r["big_loss"]]
    scored = [r for r in warned if r["exit_open"] is not None and
              r["open_price"] is not None and r["base"] > 0]
    # A price-mark scenario; no claim a sell could execute at that price.
    diffs = [100*(r["exit_open"]-r["open_price"])*0.9985/r["base"]
             for r in scored]
    return {
        "stock_days": len(rows),
        "major_down_days": len(major),
        "preopen_warnings": len(warned),
        "major_down_detected": len(major_warn),
        "major_down_missed": len(major)-len(major_warn),
        "nonmajor_warnings": len(warned)-len(major_warn),
        "major_detected_before_minus5": sum(r["pre_early"] for r in major_warn),
        "observed_first_after_alert_and_rth_open":len(scored),
        "mean_preopen_price_mark_vs_rth_open_pp":round(mean(diffs),4) if diffs else None,
        "improved_vs_open": sum(v>0 for v in diffs),
        "worse_vs_open": sum(v<0 for v in diffs),
        "earliest_warning":min((r["pre_asof"] for r in warned),default=None),
    }

def analyze(symbols,daily):
    rows,dates=all_days(symbols,daily)
    calendar=[date.fromisoformat(x) for x in dates]
    closes=prior_regular_closes(symbols)
    events=collect(symbols,dates)
    cohorts=[]
    missing=0
    for event in events:
        day=date.fromisoformat(event["day"])
        five=five_completed_return(closes["SOXX"],calendar,day)
        if five is None:
            missing+=1
            continue
        cohorts.append({**event,
            "five_soxx_pct":round(five,4),
            "group":"weak" if five<=-5 else "not_weak",
            "later":day>=LATER_START})
    reports={}
    for period in ("all","earlier","later"):
        subset=[r for r in cohorts if period=="all" or r["later"]==(period=="later")]
        reports[period]={"all":summary(subset)}
        for group in ("weak","not_weak"):
            reports[period][group]=summary([r for r in subset if r["group"]==group])
    return {
      "data":"Split-adjusted 5m SIP OHLC; no full BOATS, NBBO depth or V1 fills",
      "date_start":dates[0],"date_end":dates[-1],
      "full_stock_day_records":len(events),
      "with_completed_prior5_soxx":len(cohorts),
      "excluded_missing_completed_prior5_soxx":missing,
      "reports":reports,
      "interpretation":"Premarket signals use previous regular close, completed 5m bars, and 15-minute "
                       "momentum. Actual next bar and regular open are future evaluations only; "
                       "price marks are not executable sales."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    p.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    p.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    p.add_argument("--output")
    a=p.parse_args()
    data=analyze(ingest([a.primary,a.peers]),
                 json.loads(Path(a.daily).read_text())["split"])
    if a.output:
        Path(a.output).write_text(json.dumps(data,indent=2))
    print(json.dumps(data,indent=2))

if __name__=="__main__":
    main()
