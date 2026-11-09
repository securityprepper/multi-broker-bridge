"""Two-sided 52-week SIP five-minute outcome audit (research ONLY; never places orders).

Every decision uses completed five-minute bars. Intraday target close and 14:00
mark are labels/exit observations, NEVER strategy inputs. SIP OHLC proxy fills
are NOT broker fills or contemporaneous NBBO. BOATS overnight is not present.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
import csv
import json
from pathlib import Path
from statistics import mean, median

from research.v2_stock_risk_dayphase import ANCHORS, ETF, ET, T5, T15, ingest, phase

FEE_BUFFER = 0.0015
EARLY_CUTOFF = "2026-08-31"
BULL = {"up_25_10": (0.025, 0.010), "up_15_05": (0.015, 0.005)}
BEAR = {"down_25_10": (0.025, 0.010), "down_20_05": (0.020, 0.005)}
ALL_WINDOWS = {"evening", "premarket", "rth_open_hour"}


def signal(side, base, prior15, current, total, velocity):
    """Overlapping conditions: recent momentum is INCLUDED in total."""
    if min(base, prior15, current) <= 0:
        return False
    if side == "up":
        return current / base >= 1 + total and current / prior15 >= 1 + velocity
    if side == "down":
        return current / base <= 1 - total and current / prior15 <= 1 - velocity
    raise ValueError(side)


def first_observable(bars, target, preceding, base, side, total, velocity, allowed=ALL_WINDOWS):
    """Return FIRST finished-bar decision, with next-bar open only for scoring."""
    for start in sorted(bars):
        kind = phase(start, target, preceding)
        if kind not in allowed:
            continue
        old = bars.get(start - T15)
        if old is None:
            continue
        close = bars[start][3]
        if signal(side, base, old[3], close, total, velocity):
            decision = start + T5
            next_bar = bars.get(decision)
            return dict(asof=decision.isoformat(), phase=kind, signal_close=close,
                        drawdown_pct=round((close / base - 1) * 100, 4),
                        prior15_pct=round((close / old[3] - 1) * 100, 4),
                        # Future first available five-minute observation; outcome ONLY.
                        next_open=next_bar[0] if next_bar else None)
    return None


def pct(value):
    return round(value * 100, 3)


def score_profit(entry, exit_price, side="long", buffer=FEE_BUFFER):
    if entry is None or exit_price is None:
        return None
    if side == "long":
        return 100 * (exit_price * (1 - buffer) / (entry * (1 + buffer)) - 1)
    raise ValueError(side)


def audited_days(symbols, daily):
    calendar = sorted(set.intersection(*(set(row[0][:10] for row in daily[s])
                                           for s in (*ANCHORS, ETF))))
    all_dates = [date.fromisoformat(d) for d in calendar]
    by_sym_date = {}
    regular = {}
    for sym, bars in symbols.items():
        bucket = defaultdict(dict)
        for dt, row in bars.items():
            bucket[dt.date()][dt] = row
            if dt.time() == time(15, 55):
                regular[sym, dt.date()] = row[3]
        by_sym_date[sym] = bucket
    records = []
    for i in range(1, len(all_dates)):
        target, preceding = all_dates[i], all_dates[i - 1]
        for sym in sorted(symbols):
            base = regular.get((sym, preceding))
            close = regular.get((sym, target))
            if not base or not close:
                continue
            bars = {**by_sym_date[sym].get(preceding, {}),
                    **by_sym_date[sym].get(target, {})}
            at = lambda h, m: datetime.combine(target, time(h, m), ET)
            opening = bars.get(at(9, 30))
            mark14 = bars.get(at(14, 0))
            rth = [b for t, b in by_sym_date[sym].get(target, {}).items()
                   if time(9, 30) <= t.time() <= time(15, 55)]
            change = close / base - 1
            record = dict(day=target.isoformat(), sym=sym, base=base, close=close,
                          change_pct=pct(change), major_up=change >= .05,
                          major_down=change <= -.05, later=target.isoformat() > EARLY_CUTOFF,
                          rth_open=opening[0] if opening else None,
                          rth_high_pct=pct(max(x[1] for x in rth) / base - 1) if rth else None,
                          rth_low_pct=pct(min(x[2] for x in rth) / base - 1) if rth else None,
                          exit14=mark14[0] if mark14 else None)
            for name, (total, velocity) in {**BULL, **BEAR}.items():
                side = "up" if name.startswith("up_") else "down"
                record[name] = first_observable(bars, target, preceding, base,
                                                 side, total, velocity)
                event = record[name]
                if event:
                    event["pnl_to14_pct"] = (round(score_profit(event["next_open"], record["exit14"]), 4)
                                              if side == "up" and event["next_open"]
                                              and record["exit14"] else None)
                    event["vs_hold14_pp"] = (round(100 * ((event["next_open"] - record["exit14"])
                                                               * (1 - FEE_BUFFER) / base), 4)
                                             if side == "down" and event["next_open"]
                                             and record["exit14"] else None)
            if opening and mark14:
                bar935 = bars.get(at(9, 35))
                record["blind935_to14_pct"] = (round(score_profit(bar935[0], mark14[0]), 4)
                                             if bar935 else None)
            records.append(record)
    return records, calendar


def subset_metrics(records, key, side):
    relevant = [x for x in records if x[key]]
    is_maj = lambda x: x["major_up"] if side == "up" else x["major_down"]
    severe = sum(is_maj(x) for x in records)
    hit = sum(is_maj(x) for x in relevant)
    early = sum(is_maj(x) and ((x[key]["drawdown_pct"] < 5) if side == "up"
                            else (x[key]["drawdown_pct"] > -5)) for x in relevant)
    field = "pnl_to14_pct" if side == "up" else "vs_hold14_pp"
    scored = [x[key][field] for x in relevant if x[key][field] is not None]
    return dict(signals=len(relevant), hits=hit, missed=severe-hit,
                precision_pct=pct(hit/len(relevant)) if relevant else None,
                recall_pct=pct(hit/severe) if severe else None,
                pre_move_5pct_hits=early, false_alarms=len(relevant)-hit,
                valid_proxy_executions=len(scored),
                avg_proxy_trade_or_avoided_pp=round(mean(scored), 4) if scored else None,
                median_proxy_trade_or_avoided_pp=round(median(scored), 4) if scored else None,
                favorable_proxy_outcomes=sum(v > 0 for v in scored),
                unfavorable_proxy_outcomes=sum(v < 0 for v in scored))


def sector_audit(symbols, calendar, daily):
    daily_close = {sym: {row[0][:10]: row[4] for row in rows} for sym, rows in daily.items()}
    by_sym = {}
    for sym in (*ANCHORS, ETF):
        by_sym[sym] = symbols[sym]
    out = []
    for i in range(1, len(calendar)):
        day, prev = calendar[i], calendar[i - 1]
        if any(day not in daily_close[s] or prev not in daily_close[s] for s in (*ANCHORS,ETF)):
            continue
        returns = {s: daily_close[s][day] / daily_close[s][prev] - 1
                   for s in (*ANCHORS, ETF)}
        pos = sum(returns[s] > 0 for s in ANCHORS)
        neg = sum(returns[s] < 0 for s in ANCHORS)
        label = ("positive" if pos >= 2 and returns[ETF] > 0 else
                 "negative" if neg >= 2 and returns[ETF] < 0 else "mixed")
        dt = date.fromisoformat(day)
        first = None
        for minute in range(9*60+50, 10*60+31, 5):
            asof = datetime.combine(dt, time(minute // 60, minute % 60), ET)
            current_start = asof - T5
            older_start = asof - timedelta(minutes=20)
            b = {sym: by_sym[sym].get(current_start) for sym in (*ANCHORS,ETF)}
            old_soxx = by_sym[ETF].get(older_start)
            if any(row is None for row in b.values()) or old_soxx is None:
                continue
            gains = {sym: b[sym][3] / daily_close[sym][prev] - 1
                     for sym in (*ANCHORS,ETF)}
            advancing = sum(gains[s] >= 0.01 for s in ANCHORS)
            latest_vel = b[ETF][3] / old_soxx[3] - 1
            if advancing >= 2 and gains[ETF] >= 0.005 and latest_vel >= 0.003:
                next_bar = by_sym[ETF].get(asof)
                end_bar = by_sym[ETF].get(datetime.combine(dt,time(14),ET))
                first = dict(asof=asof.isoformat(), soxx_move_pct=pct(gains[ETF]),
                             breadth=advancing, soxx_15min_pct=pct(latest_vel),
                             pnl_to14_pct=(round(score_profit(next_bar[0],end_bar[0]),4)
                                           if next_bar and end_bar else None))
                break
        out.append(dict(day=day, label=label, soxx_return_pct=pct(returns[ETF]),
                        strong_soxx_up=returns[ETF] >= .02, signal=first))
    return out


def missed_examples(records, direction, limit=12):
    major = "major_up" if direction == "up" else "major_down"
    default = "up_25_10" if direction == "up" else "down_25_10"
    missed = [r for r in records if r[major] and not r[default]]
    missed.sort(key=lambda r: r["change_pct"], reverse=direction=="up")
    return [dict(day=r["day"],symbol=r["sym"],close_change_pct=r["change_pct"],
                 rth_high_pct=r["rth_high_pct"],rth_low_pct=r["rth_low_pct"],
                 relaxed_rule_alert=r["up_15_05"]["asof"] if direction=="up" and r["up_15_05"]
                       else (r["down_20_05"]["asof"] if direction=="down" and r["down_20_05"] else None))
            for r in missed[:limit]]


def report(records, sectors):
    overall = dict(stock_days=len(records), major_up_days=sum(r["major_up"] for r in records),
                   major_down_days=sum(r["major_down"] for r in records),
                   first_day=min(r["day"] for r in records),
                   last_day=max(r["day"] for r in records),
                   sectors=dict(Counter(r["label"] for r in sectors)))
    stock = {}
    for key in BULL:
        stock[key] = {p: subset_metrics([r for r in records if r["later"] == later],key,"up")
                      for p,later in (("earlier",False),("later",True))}
        stock[key]["all"] = subset_metrics(records,key,"up")
    for key in BEAR:
        stock[key] = {p: subset_metrics([r for r in records if r["later"] == later],key,"down")
                      for p,later in (("earlier",False),("later",True))}
        stock[key]["all"] = subset_metrics(records,key,"down")
    b = [r["blind935_to14_pct"] for r in records if r.get("blind935_to14_pct") is not None]
    sig = [r for r in sectors if r["signal"]]
    good = [r for r in sig if r["signal"]["pnl_to14_pct"] is not None]
    s = dict(days=len(sectors), strong_soxx_up_days=sum(r["strong_soxx_up"] for r in sectors),
             triggers=len(sig), positive_hit=sum(r["label"]=="positive" for r in sig),
             false_or_nonpositive=sum(r["label"]!="positive" for r in sig),
             positive_days_missed=sum(r["label"]=="positive" and not r["signal"] for r in sectors),
             strong_up_days_hit=sum(r["strong_soxx_up"] for r in sig),
             strong_up_days_missed=sum(r["strong_soxx_up"] and not r["signal"] for r in sectors),
             proxy_trade_count=len(good),
             proxy_avg_to14_pct=round(mean(r["signal"]["pnl_to14_pct"] for r in good),4) if good else None,
             proxy_win_count=sum(r["signal"]["pnl_to14_pct"]>0 for r in good),
             earliest_examples=[dict(day=r["day"],asof=r["signal"]["asof"],
                       signal_soxx_move_pct=r["signal"]["soxx_move_pct"],
                       close_soxx_pct=r["soxx_return_pct"])
                       for r in sig[:8]])
    earliest = {}
    for direction, name, major in (("up", "up_25_10", "major_up"),
                                   ("down", "down_25_10", "major_down")):
        seen = sorted((r for r in records if r[name] and r[major]),
                      key=lambda r:r[name]["asof"])
        earliest[direction] = [dict(day=r["day"], symbol=r["sym"],
                                    asof=r[name]["asof"],
                                    signal_pct=r[name]["drawdown_pct"],
                                    close_change_pct=r["change_pct"])
                               for r in seen[:8]]
    return dict(summary=overall, stock_signals=stock,
                all_stock_days_blind_935_to14=dict(count=len(b),avg_pct=round(mean(b),4)),
                sector_signal=s, earliest_major_event_alerts=earliest,
                missed_major_gainers=missed_examples(records,"up"),
                missed_major_decliners=missed_examples(records,"down"))


def to_csv(records, path):
    """One row per stock/day, including realized outcomes of EVERY triggered rule."""
    fields = ("day", "sym", "change_pct", "major_up", "major_down",
              "rth_open", "rth_high_pct", "rth_low_pct", "exit14")
    event_names = (*BULL, *BEAR)
    ev_suffixes = ("asof", "phase", "signal_pct", "last15_pct", "remaining_close_pct",
                   "next_bar_open", "pnl_to14_pct", "vs_hold14_pp")
    columns = (*fields, *(f"{name}_{suffix}" for name in event_names for suffix in ev_suffixes))
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for r in records:
            item = {k: r.get(k) for k in fields}
            for name in event_names:
                ev = r[name]
                if not ev:
                    continue
                vals = dict(asof=ev["asof"], phase=ev["phase"],
                            signal_pct=ev["drawdown_pct"], last15_pct=ev["prior15_pct"],
                            remaining_close_pct=round(100*(r["close"]/ev["signal_close"]-1),4),
                            next_bar_open=ev["next_open"],
                            pnl_to14_pct=ev.get("pnl_to14_pct"),
                            vs_hold14_pp=ev.get("vs_hold14_pp"))
                item.update({f"{name}_{suffix}":value for suffix,value in vals.items()})
            writer.writerow(item)


def to_sector_csv(records, path):
    columns = ("day","label","soxx_return_pct","strong_soxx_up",
               "signal_asof","signal_soxx_move_pct","signal_pnl_to14_pct")
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        for r in records:
            sig = r["signal"]
            writer.writerow({**{k:r.get(k) for k in columns},
                    "signal_asof":sig["asof"] if sig else None,
                    "signal_soxx_move_pct":sig["soxx_move_pct"] if sig else None,
                    "signal_pnl_to14_pct":sig["pnl_to14_pct"] if sig else None})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    parser.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    parser.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    parser.add_argument("--daily-csv",default=None)
    parser.add_argument("--sector-csv",default=None)
    args=parser.parse_args()
    data=json.loads(Path(args.daily).read_text())["split"]
    symbols=ingest([args.primary,args.peers])
    records,calendar=audited_days(symbols,data)
    sectors=sector_audit(symbols,calendar,data)
    if args.daily_csv:
        to_csv(records,args.daily_csv)
    if args.sector_csv:
        to_sector_csv(sectors,args.sector_csv)
    print(json.dumps(report(records,sectors),sort_keys=True,indent=2))


if __name__=="__main__":
    main()
