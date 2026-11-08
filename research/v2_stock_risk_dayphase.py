"""Offline, causal, bar-level assessment of V2 stock weakness and possible PAPER exits.

Historical SIP 5-minute OHLC is NOT a quote or executable fill. Orders are never sent.
Thresholds are fixed in advance: decline >=2.5% since previous completed regular
close INCLUDING >=1% decline in the last 15 completed minutes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
ANCHORS = ("AMD", "MU", "SNDK")
ETF = "SOXX"
T15 = timedelta(minutes=15)
T5 = timedelta(minutes=5)


def alert(base, old, current):
    """Two OVERLAPPING price-drop conditions, not 2.5% + 1%."""
    return base > 0 and old > 0 and current > 0 and (
        current / base <= 0.975 and current / old <= 0.99
    )


def phase(start, target, preceding):
    """A 5m bar's START time; its close is observable five minutes later."""
    d = start.date()
    if d == target and time(4) <= start.time() <= time(9, 15):
        return "premarket"
    # Yesterday evening only. Friday is not 'the preceding evening' of Monday.
    if d == preceding and preceding == target - timedelta(days=1) and (
        time(16) <= start.time() < time(20)
    ):
        return "evening"
    if d == target and time(9, 30) <= start.time() <= time(10, 25):
        return "rth_open_hour"
    return None


def first_signal(bars, base, target, preceding, allowed):
    """Use timestamped closes of completed, aligned 5m bars, no future values."""
    options = []
    for start in sorted(bars):
        kind = phase(start, target, preceding)
        if kind not in allowed:
            continue
        old = bars.get(start - T15)
        if old is None:
            continue
        current = bars[start][3]
        if alert(base, old[3], current):
            options.append((start + T5, kind, start, current / base - 1))
    return min(options, key=lambda item: item[0]) if options else None


def ingest(paths):
    symbols = {}
    for path in paths:
        rows = json.loads(Path(path).read_text())
        for name, records in rows.items():
            if name in symbols:
                raise ValueError("duplicate symbol: " + name)
            symbols[name] = {
                datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET):
                bar for ts, bar in records.items()
            }
    return symbols


def pct(numer, denom):
    return round(100 * numer / denom, 3)


def collect(symbols, calendar, *, cutoff="2026-08-31"):
    """One stock/day record; no tuning or labeling prior to the timestamp."""
    entries = []
    cal = sorted(date.fromisoformat(x) for x in calendar)
    for symbol, bars in sorted(symbols.items()):
        by_date = defaultdict(dict)
        for dt, bar in bars.items():
            by_date[dt.date()][dt] = bar
        regular = {d.isoformat(): bar[3] for dt, bar in bars.items()
                   if (d := dt.date()) and dt.time() == time(15, 55)}
        for idx in range(1, len(cal)):
            target, preceding = cal[idx], cal[idx - 1]
            day, prev = target.isoformat(), preceding.isoformat()
            if day not in regular or prev not in regular:
                continue
            base = regular[prev]
            close = regular[day]
            big_loss = close <= 0.95 * base
            window = {**by_date.get(preceding, {}), **by_date.get(target, {})}
            pre = first_signal(window, base, target, preceding, {"evening", "premarket"})
            rth = first_signal(window, base, target, preceding, {"rth_open_hour"})
            first = min((x for x in (pre, rth) if x), default=None,
                        key=lambda x: x[0])
            open_bar = bars.get(datetime.combine(target, time(9, 30), ET))
            open_price = open_bar[0] if open_bar else None
            exit_open = None
            if pre:
                # A possible first POST-ALERT observation, NOT an assumed fill.
                next_start = pre[2] + T5
                next_bar = bars.get(next_start)
                if next_bar:
                    exit_open = next_bar[0]
            entries.append(dict(day=day, symbol=symbol, phase=pre[1] if pre else None,
                                pre_asof=pre[0].isoformat() if pre else None,
                                pre_drop_pct=round(pre[3]*100, 3) if pre else None,
                                rth_asof=rth[0].isoformat() if rth else None,
                                any_asof=first[0].isoformat() if first else None,
                                first_drop_pct=round(first[3]*100, 3) if first else None,
                                early=bool(first and first[3] > -0.05),
                                pre_early=bool(pre and pre[3] > -0.05),
                                big_loss=big_loss, base=base, close_price=close,
                                open_price=open_price, exit_open=exit_open,
                                validation=day > cutoff))
    return entries


def evaluate(entries, daily, calendar):
    n, severe = len(entries), [x for x in entries if x["big_loss"]]
    pre = [x for x in entries if x["pre_asof"]]
    combined = [x for x in entries if x["any_asof"]]
    def scores(rows):
        hits=[x for x in rows if x["big_loss"]]
        early=[x for x in hits if x["early"]]
        return dict(warnings=len(rows), hits=len(hits),
                    recall_pct=pct(len(hits), len(severe)),
                    precision_pct=pct(len(hits), len(rows)) if rows else 0,
                    warning_without_major_loss=len(rows)-len(hits),
                    caught_before_minus5=len(early),
                    caught_only_after_minus5=len(hits)-len(early))
    pre_scores=scores(pre)
    pre_scores["caught_before_minus5"]=sum(x["big_loss"] and x["pre_early"] for x in pre)
    pre_scores["caught_only_after_minus5"]=pre_scores["hits"]-pre_scores["caught_before_minus5"]
    pre_scores["evening_hits"]=sum(x["big_loss"] and x["phase"]=="evening" for x in pre)
    pre_scores["premarket_hits"]=sum(x["big_loss"] and x["phase"]=="premarket" for x in pre)
    pre_scores["missed_major"]=len(severe)-pre_scores["hits"]
    pre_scores["missed_examples"]=[(x["day"],x["symbol"]) for x in severe if not x["pre_asof"]][:15]
    both=scores(combined)
    both["early_before_minus5"]=sum(x["big_loss"] and x["early"] for x in combined)
    both["first_hour_additional_early_hits"]=sum(x["big_loss"] and
            not x["pre_asof"] and bool(x["rth_asof"]) and x["early"] for x in combined)
    both["first_hour_additional_hits"]=sum(x["big_loss"] and
                                          not x["pre_asof"] and bool(x["rth_asof"]) for x in combined)
    both["first_hour_additional_false_alarms"]=sum(not x["big_loss"] and
                                                   not x["pre_asof"] and bool(x["rth_asof"]) for x in combined)
    # RTH-open counterfactual: entirely hypothetical next-bar-open sale, not a fill.
    valid = [x for x in pre if x["exit_open"] is not None and x["open_price"] is not None]
    missed_price = len(pre)-len(valid)
    stress={}
    for bps in (0, 15, 30, 50):
        buffer=bps/10000
        rec=[]
        close_rec=[]
        for x in valid:
            # Position entered at prior close, 1 prior-close-notional share.
            # Sale at next bar open - buffer, compared to holding to 9:30 RTH open.
            avoided=(x["exit_open"]*(1-buffer)-x["open_price"])/x["base"]*100
            rec.append((x,avoided))
            close_rec.append((x, (x["exit_open"]*(1-buffer)-x["close_price"])/x["base"]*100))
        stress[str(bps)+"bps"]={
            "sample":len(rec),
            "all_stock_day_avg_pp":round(sum(v for _,v in rec)/len(rec),3) if rec else None,
            "large_loss_avg_pp":round(sum(v for x,v in rec if x["big_loss"]) /
                                        sum(x["big_loss"] for x,_ in rec),3)
                                  if any(x["big_loss"] for x,_ in rec) else None,
            "nonmajor_avg_pp":round(sum(v for x,v in rec if not x["big_loss"]) /
                                      sum(not x["big_loss"] for x,_ in rec),3)
                                if any(not x["big_loss"] for x,_ in rec) else None,
            "vs_same_day_close_all_avg_pp":round(sum(v for _,v in close_rec)/len(close_rec),3) if close_rec else None,
            "vs_same_day_close_major_avg_pp":round(sum(v for x,v in close_rec if x["big_loss"]) /
               sum(x["big_loss"] for x,_ in close_rec),3) if any(x["big_loss"] for x,_ in close_rec) else None,
            "avoided_negative_gap_count":sum(v>0 for _,v in rec),
            "hurts_holding_count":sum(v<0 for _,v in rec),
        }
    # Retrospective classification of broad days, NEVER used for a live decision.
    close_by_symbol={}
    for x in entries:
        close_by_symbol.setdefault(x["day"],{})[x["symbol"]]=x["base"]
    daily_lookup={s:{t[:10]:v[3] for t,*v in arr} for s,arr in daily.items()}
    sector=Counter()
    labels={}
    with_alert=Counter()
    for i in range(1,len(calendar)):
        day,prev=calendar[i],calendar[i-1]
        try:
            direction={s:daily_lookup[s][day]/daily_lookup[s][prev]-1 for s in (*ANCHORS,ETF)}
        except KeyError:
            continue
        adv=sum(direction[s]>0 for s in ANCHORS)
        dec=sum(direction[s]<0 for s in ANCHORS)
        group="positive" if adv>=2 and direction[ETF]>0 else (
            "negative" if dec>=2 and direction[ETF]<0 else "mixed")
        sector[group]+=1
        labels[day]=group
        if any(x["day"]==day and x["symbol"] in ANCHORS and x["pre_asof"] for x in entries):
            with_alert[group]+=1
    prior5=Counter();next_positive=Counter()
    for i in range(6,len(calendar)):
        day=calendar[i]
        history=[labels.get(x) for x in calendar[i-5:i]]
        if any(x is None for x in history) or day not in labels:continue
        downs=history.count("negative");ups=history.count("positive")
        group=("5_down" if downs==5 else
               "3plus_down" if downs>=3 else
               "3plus_up" if ups>=3 else "other")
        prior5[group]+=1
        next_positive[group]+=labels[day]=="positive"
    return {
        "prior_five_completed_sector_sessions":{
            group:{"next_days":count,"next_broad_positive_days":next_positive[group]}
            for group,count in sorted(prior5.items())},
        "data":dict(evaluable_stock_days=n,severe_stock_days=len(severe),
                    universe=sorted({x["symbol"] for x in entries}),
                    first_day=min(x["day"] for x in entries),
                    last_day=max(x["day"] for x in entries)),
        "preopen":pre_scores,
        "preopen_or_first_regular_hour":both,
        "proposed_exit_counterfactual":dict(
            flags_with_missing_next_bar_or_rth_open=missed_price,
            executable_fills_verified=0,stress=stress),
        "sector_broad_direction":dict(total=dict(sector),
             positive_days_with_urgent_leader_warning=with_alert["positive"],
             negative_days_with_urgent_leader_warning=with_alert["negative"]),
        "split":{p:dict(total=sum(x["validation"]==is_val for x in entries),
            severe=sum(x["validation"]==is_val and x["big_loss"] for x in entries),
            pre_hits=sum(x["validation"]==is_val and x["big_loss"] and
                         x["pre_asof"] is not None for x in entries))
                 for p,is_val in (("through_aug31",False),("sep_to_nov6",True))},
        "earliest_examples":[{"day":x["day"],"symbol":x["symbol"],
                             "asof_et":x["pre_asof"],"drawdown_at_alert_pct":x["pre_drop_pct"]}
                             for x in sorted((x for x in pre if x["big_loss"]),
                                             key=lambda q:q["pre_asof"])[:8]]
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    parser.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    parser.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    args=parser.parse_args()
    daily=json.loads(Path(args.daily).read_text())["split"]
    calendar=sorted(set.intersection(*(set(x[0][:10] for x in daily[s])
                                       for s in (*ANCHORS,ETF))))
    entries=collect(ingest([args.primary,args.peers]), calendar)
    print(json.dumps(evaluate(entries,daily,calendar),sort_keys=True,indent=2))


if __name__=="__main__":
    main()
