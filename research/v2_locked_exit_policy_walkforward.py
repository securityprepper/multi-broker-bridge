"""V2 OFFLINE ONLY: causal sell-timing stress for first-hour rising-sector signals.

All orders are hypothetical. 5m SIP OHLC OPEN is a retrospective price proxy,
not a fill. Never reads credentials, submits orders, modifies V1 or uses future
bar outcomes to make decisions. Later samples must not tune thresholds.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean
from research.v2_stock_risk_dayphase import ET, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_rth_open_momentum import first_signal, OPEN

F=0.0015
ENVELOPE=0.003
CHECKS=("hold_1400","fixed_1100","fixed_1200","fixed_1300",
        "tp05_sl075","tp10_sl150","sl075_only","tp05_only")
LATER=date(2026,9,1)
T5=timedelta(minutes=5)

def nextbar_sell(outcome_bar_close, nextbar_open):
    """A bounded-limit eligibility proxy; never infer fill from high/low."""
    if min(outcome_bar_close,nextbar_open)<=0:
        return None
    proceeds=nextbar_open*(1-F)
    return proceeds if proceeds>=outcome_bar_close*(1-ENVELOPE) else None

def policy_outcome(daybars, entry_event, mark14, policy):
    """Signal, entry and every exit decision use completed bars only.

    If bounded exit is price-ineligible, treat as pending/held through 14:00;
    do NOT claim it was later filled or silently reprice it.
    """
    if policy not in CHECKS:
        raise ValueError("unapproved policy")
    ref=entry_event["price"]
    entry=entry_event["next_bar_open"]
    if not entry or not mark14 or min(entry,ref,mark14)<=0:
        return None
    buy=entry*(1+F)
    entered=buy<=ref*(1+ENVELOPE)
    if not entered:
        return {"eligible_entry":False,"net_pct":0.0,
                "exit_kind":"NO_ENTRY","exit_at":None,"exit_eligible":False}
    entry_at=datetime.fromisoformat(entry_event["at"]).astimezone(ET)
    if policy=="hold_1400":
        return {"eligible_entry":True,
                "net_pct":100*(mark14*(1-F)/buy-1),
                "exit_kind":"HOLD_TO_1400","exit_at":None,
                "exit_eligible":True}
    for minute in range(entry_at.hour*60+entry_at.minute+5,14*60+1,5):
        at=datetime.combine(entry_at.date(),time(minute//60,minute%60),ET)
        last=daybars.get(at-T5)
        if last is None:
            continue
        closing=last[3]
        if closing<=0:
            continue
        ret_pct=100*(closing/buy-1)
        if policy.startswith("fixed_"):
            due=minute >= int(policy[-4:-2])*60+int(policy[-2:])
        elif policy=="tp05_sl075":
            due=ret_pct>=.5 or ret_pct<=-.75
        elif policy=="tp10_sl150":
            due=ret_pct>=1 or ret_pct<=-1.5
        elif policy=="sl075_only":
            due=ret_pct<=-.75
        else:
            due=ret_pct>=.5
        if not due:
            continue
        nxt=daybars.get(at)
        proceeds=nextbar_sell(closing,nxt[0]) if nxt else None
        if proceeds is None:
            return {"eligible_entry":True,
                    "net_pct":100*(mark14*(1-F)/buy-1),
                    "exit_kind":"UNFILLED_THEN_MARK_1400",
                    "exit_at":at.isoformat(),"exit_eligible":False}
        return {"eligible_entry":True,"net_pct":100*(proceeds/buy-1),
                "exit_kind":"BOUNDED_EXIT_PRICE_ELIGIBLE",
                "exit_at":at.isoformat(),"exit_eligible":True}
    return {"eligible_entry":True,
            "net_pct":100*(mark14*(1-F)/buy-1),
            "exit_kind":"NO_TRIGGER_MARK_1400","exit_at":None,
            "exit_eligible":False}

def day_mean(rows,policy):
    grouped=defaultdict(list)
    for r in rows:
        grouped[r["day"]].append(r["scores"][policy]["net_pct"])
    return mean(map(mean,grouped.values())) if grouped else None

def aggregate(rows,policy):
    scores=[r["scores"][policy] for r in rows]
    returns=[x["net_pct"] for x in scores]
    realized=[x["net_pct"] for x in scores if x["eligible_entry"]]
    return {"signals":len(rows),
            "eligible_entries":sum(x["eligible_entry"] for x in scores),
            "price_eligible_early_exits":sum(x["exit_kind"]=="BOUNDED_EXIT_PRICE_ELIGIBLE" for x in scores),
            "unfilled_exit_proxies":sum(x["exit_kind"]=="UNFILLED_THEN_MARK_1400" for x in scores),
            "mean_per_signal_pct":round(mean(returns),4) if returns else None,
            "mean_per_eligible_entry_pct":round(mean(realized),4) if realized else None,
            "day_equal_mean_pct":round(day_mean(rows,policy),4) if rows else None,
            "profitable_entry_count":sum(x["eligible_entry"] and x["net_pct"]>0 for x in scores),
            "unprofitable_entry_count":sum(x["eligible_entry"] and x["net_pct"]<0 for x in scores),
            "major_up_days_hit":sum(r["major_up"] for r in rows),
            "major_down_days_signaled":sum(r["major_down"] for r in rows)}

def choose_from_previous(rows,eligible_policies,minimum_days=15):
    """All rows supplied must predate the target decision period."""
    distinct=len(set(r["day"] for r in rows))
    if distinct<minimum_days:
        return None
    scored=[(day_mean(rows,p),p) for p in eligible_policies]
    return max(scored,key=lambda x:(x[0],-eligible_policies.index(x[1])))[1]

def walkforward(rows,monthly_first=date(2026,4,1),prior_calendar_days=120):
    """Fixed trailing 120 calendar-day training, prior completed dates ONLY.

    Select one exit policy across ALL correlated tickers per calendar month;
    evaluate that choice on later month without refitting inside that month.
    """
    months=sorted(set(r["day"][:7] for r in rows))
    selected=[]
    for m in months:
        start=date.fromisoformat(m+"-01")
        if start<monthly_first:
            continue
        train_start=start-timedelta(days=prior_calendar_days)
        train=[r for r in rows if train_start<=date.fromisoformat(r["day"])<start]
        test=[r for r in rows if r["day"].startswith(m)]
        policy=choose_from_previous(train,CHECKS)
        if not policy or not test:
            continue
        selected.extend({"month":m,"policy":policy,"day":r["day"],
                         "net_pct":r["scores"][policy]["net_pct"],
                         "baseline_pct":r["scores"]["hold_1400"]["net_pct"],
                         "eligible":r["scores"][policy]["eligible_entry"]}
                         for r in test)
    early=[r for r in selected if r["day"]<LATER.isoformat()]
    late=[r for r in selected if r["day"]>=LATER.isoformat()]
    def summary(rr):
        grouped=defaultdict(list)
        base=defaultdict(list)
        for r in rr:
            grouped[r["day"]].append(r["net_pct"])
            base[r["day"]].append(r["baseline_pct"])
        return {"signals":len(rr),"independent_days":len(grouped),
                "net_mean_pct":round(mean(x["net_pct"] for x in rr),4) if rr else None,
                "baseline_mean_pct":round(mean(x["baseline_pct"] for x in rr),4) if rr else None,
                "day_equal_net_pct":round(mean(map(mean,grouped.values())),4) if rr else None,
                "day_equal_baseline_pct":round(mean(map(mean,base.values())),4) if rr else None}
    return {"all":summary(selected),"earlier":summary(early),
            "later":summary(late),
            "monthly_choices":[{"month":m,
               "policy":next(r["policy"] for r in selected if r["month"]==m),
               "signals":sum(r["month"]==m for r in selected)}
               for m in sorted(set(r["month"] for r in selected))]}

def analyze(bars,daily):
    universe,calendar=all_days(bars,daily)
    records=[]
    coverage=[]
    for row in universe:
        d=date.fromisoformat(row["day"])
        ev=first_signal(bars,d,row["sym"],"early_1030")
        coverage.append({"sym":row["sym"],"day":row["day"],
                         "major_up":row["big_up"],"major_down":row["big_down"],
                         "entry_alert":ev is not None})
        if ev is None:
            continue
        scores={p:policy_outcome(bars[row["sym"]],ev,row["mark14"],p) for p in CHECKS}
        if any(s is None for s in scores.values()):
            continue
        records.append({"day":row["day"],"sym":row["sym"],
                        "signal_at":ev["at"],"signal_mark":ev["price"],
                        "major_up":row["big_up"],"major_down":row["big_down"],
                        "close_pct":row["change_pct"],"scores":scores})
    early=[r for r in records if r["day"]<LATER.isoformat()]
    later=[r for r in records if r["day"]>=LATER.isoformat()]
    best=choose_from_previous(early,CHECKS)
    result={"universe_stockdays":len(coverage),
            "major_up":sum(r["major_up"] for r in coverage),
            "major_down":sum(r["major_down"] for r in coverage),
            "major_up_caught":sum(r["major_up"] and r["entry_alert"] for r in coverage),
            "major_down_given_buy":sum(r["major_down"] and r["entry_alert"] for r in coverage),
            "missed_up_examples":sorted(
                [{"symbol":r["sym"],"day":r["day"]}
                 for r in coverage if r["major_up"] and not r["entry_alert"]],
                key=lambda x:(x["day"],x["symbol"]))[:12],
            "scorable_alerts":len(records),"policy_metrics":{},
            "training_only_best_policy":best,"locked_later":{},
            "rolling":walkforward(records)}
    for p in CHECKS:
        result["policy_metrics"][p]={"all":aggregate(records,p),
                                     "earlier":aggregate(early,p),
                                     "later":aggregate(later,p)}
    if best:
        result["locked_later"]={
            "selected_on_prior_period":best,
            "selected_later":aggregate(later,best),
            "baseline_later":aggregate(later,"hold_1400")}
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    ap.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    ap.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    ap.add_argument("--output")
    args=ap.parse_args()
    result=analyze(ingest([args.primary,args.peers]),
                   json.loads(Path(args.daily).read_text())["split"])
    if args.output:
        Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":main()