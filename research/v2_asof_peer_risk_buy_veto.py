"""Read-only V2 study: as-of peer-risk confirmation and risk-first BUY admissions.

Only fully completed SIP 5m bars and contemporaneous previously triggered
warnings enter decisions. Final-day labels, next-bar and next-open marks are
retrospective scoring ONLY. Never imports broker or execution modules.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
from statistics import mean

from research.v2_stock_risk_dayphase import ET, ingest
from research.v2_reversal_and_limit_stress import all_days
from research.v2_late_session_and_prior5_cap import complete_close
from research.v2_rth_open_momentum import first_signal
from research.v2_locked_exit_policy_walkforward import policy_outcome, LATER
from research.v2_downside_early_sell_opportunity_cost import price_scenario

OPEN = time(9, 30)
MODES = ("sticky", "fresh30")
ENTRY_POLICIES = (
    "first_only", "own_risk_clear", "zero_other_risks",
    "fewer_than_two_other_risks", "fewer_than_three_other_risks", "soxx_risk_clear",
)


def when(event):
    return datetime.fromisoformat(event["asof"]) if event else None


def byday_warnings(audit, field):
    """Timestamped warning ledger, without any future outcome labels."""
    out = defaultdict(dict)
    for row in audit:
        ev = row.get(field)
        if ev:
            at = when(ev)
            if at.tzinfo is None:
                raise ValueError("naive warning time")
            out[row["day"]][row["sym"]] = at.astimezone(ET)
    return out


def peer_confirmation(first, signals, sym, session_day, required, mode):
    """Earliest as-of concurrence of first warnings; never peek later.

    Sticky means warnings persist through the RTH open. Fresh30 permits a
    warning for at most 30 minutes and never assumes unobserved re-triggering.
    These are alert-state hypotheses, NOT concurrent current-price breadth.
    """
    if mode not in MODES or required < 0:
        raise ValueError("unknown confirmation policy")
    opening = datetime.combine(session_day, OPEN, ET)
    if first is None:
        return None
    first = first.astimezone(ET)
    if first >= opening:
        return None
    peers = [(s, t.astimezone(ET)) for s, t in signals.items() if s != sym]
    candidates = sorted(set([first] + [t for _, t in peers if first <= t < opening]))
    for at in candidates:
        if at < first or at >= opening:
            continue
        if mode == "fresh30" and at - first > timedelta(minutes=30):
            continue
        active = {s for s, t in peers if t <= at and (
            mode == "sticky" or at - t <= timedelta(minutes=30))}
        if len(active) >= required:
            return at
    return None


def entry_admitted(policy, own, other, soxx):
    if policy not in ENTRY_POLICIES:
        raise ValueError("unknown admission policy")
    return {
        "first_only": True,
        "own_risk_clear": not own,
        "zero_other_risks": other == 0,
        "fewer_than_two_other_risks": other < 2,
        "fewer_than_three_other_risks": other < 3,
        "soxx_risk_clear": not soxx,
    }[policy]


def asof_active(signals, at, symbol):
    """Stocks with a first alarm known at or before the candidate BUY time."""
    assert at.tzinfo is not None
    active = {s for s, t in signals.items() if t <= at}
    return {
        "own_risk": symbol in active,
        "other_risks": len(active - {symbol}),
        "soxx_risk": "SOXX" in active,
    }


def period_tag(day):
    return "earlier" if day < LATER.isoformat() else "later"


def summarize_entry(rows, policy, period):
    sample = [r for r in rows if period == "all" or r["period"] == period]
    admitted = [r for r in sample if r["allow"][policy]]
    skipped = [r for r in sample if not r["allow"][policy]]
    vals = [r["net_pct"] if r["allow"][policy] else 0.0 for r in sample]
    return {
        "baseline_signal_days": len(sample), "admitted": len(admitted),
        "day_equal_net_pct": round(mean(vals), 4) if vals else None,
        "retained_major_winners": sum(r["major_up"] for r in admitted),
        "retained_major_losers": sum(r["major_down"] for r in admitted),
        "skipped_major_winners": sum(r["major_up"] for r in skipped),
        "skipped_major_losers": sum(r["major_down"] for r in skipped),
        "avoided_negative_trade_proxy_pct_points": round(
            sum(-r["net_pct"] for r in skipped if r["net_pct"] < 0), 4),
        "forgone_positive_trade_proxy_pct_points": round(
            sum(r["net_pct"] for r in skipped if r["net_pct"] > 0), 4),
    }


def study(bars, daily, audit):
    universe, sessions = all_days(bars, daily)
    index = {(r["day"], r["sym"]): r for r in universe}
    by_audit = {(r["day"], r["sym"]): r for r in audit}
    if set(index) != set(by_audit) or len(index) != len(audit):
        raise ValueError("full 52-week audit does not match input universe")

    pre = byday_warnings(audit, "preopen_union")
    all_risk = byday_warnings(audit, "all_union")
    session_days = sorted(date.fromisoformat(x) for x in sessions)
    following = dict(zip(session_days, session_days[1:]))
    warning_rows = []
    per_day = {(r["day"], r["sym"]): {
        "day": r["day"], "sym": r["sym"],
        "major_up_outcome_only": bool(r["big_up"]),
        "major_down_outcome_only": bool(r["big_down"]),
        "closing_return_outcome_only": round(r["change_pct"], 4),
        "preopen_confirmed": {}, "buy": None
    } for r in universe}

    for r in universe:
        day = r["day"]
        d = date.fromisoformat(day)
        first = pre.get(day, {}).get(r["sym"])
        if first is None:
            continue
        opening = datetime.combine(following[d], OPEN, ET) if d in following else None
        following_bar = bars[r["sym"]].get(opening) if opening else None
        following_open = following_bar[0] if following_bar else None
        for mode in MODES:
            for needed in (0, 1, 2, 3):
                at = peer_confirmation(first, pre[day], r["sym"], d, needed, mode)
                if at is None:
                    continue
                # As-of bar's START is five minutes earlier. No same-time
                # incomplete/future bar may be consulted as a signal.
                px = complete_close(bars, r["sym"], at)
                nextbar = bars[r["sym"]].get(at)
                score = price_scenario({
                    "signal_price": px,
                    "next_bar_open": nextbar[0] if nextbar else None
                }, r["previous_close"], following_open) if px is not None else None
                row = {
                    "day": day, "sym": r["sym"], "mode": mode, "peers": needed,
                    "confirmed_asof": at.isoformat(),
                    "major_down_outcome_only": bool(r["big_down"]),
                    "major_up_outcome_only": bool(r["big_up"]),
                    "prior_evening": at.date() < d,
                    "before_minus5": bool(px is not None and
                        100 * (px / r["previous_close"] - 1) > -5),
                    "price_scorable": score is not None,
                    "sell_advantage_next_open_pp": score.get("advantage_to_next_open_pp")
                        if score else None,
                }
                warning_rows.append(row)
                per_day[day, r["sym"]]["preopen_confirmed"][f"{mode}_{needed}"] = row["confirmed_asof"]

    grouped = defaultdict(list)
    for r in universe:
        d = date.fromisoformat(r["day"])
        event = first_signal(bars, d, r["sym"], "early_1030")
        if not event:
            continue
        scored = policy_outcome(bars[r["sym"]], event, r["mark14"], "hold_1400")
        if not scored:
            continue
        grouped[r["day"]].append((event["at"], -event["own_open_pct"], r["sym"], scored["net_pct"], r))
    buys = []
    for day, events in sorted(grouped.items()):
        ts, negstrength, sym, net, reference = min(events)
        at = datetime.fromisoformat(ts).astimezone(ET)
        status = asof_active(all_risk.get(day, {}), at, sym)
        allow = {policy: entry_admitted(policy, status["own_risk"],
                status["other_risks"], status["soxx_risk"]) for policy in ENTRY_POLICIES}
        decision = {
            "day": day, "sym": sym, "asof": at.isoformat(),
            "period": period_tag(day), "net_pct": net,
            "major_up": bool(reference["big_up"]),
            "major_down": bool(reference["big_down"]),
            "prior_risk_counts": status, "allow": allow
        }
        buys.append(decision)
        per_day[day, sym]["buy"] = {"asof": decision["asof"], "allow": allow}

    result = {
        "sample": {"stockdays": len(universe), "sessions": len(sessions),
                   "major_up": sum(r["big_up"] for r in universe),
                   "major_down": sum(r["big_down"] for r in universe),
                   "preopen_baseline_warnings": sum(bool(r["preopen_union"]) for r in audit),
                   "first_only_buy_dates": len(buys)},
        "preopen_peer_confirm": {}, "first_only_risk_admission": {}
    }
    for mode in MODES:
        result["preopen_peer_confirm"][mode] = {}
        for needed in (0, 1, 2, 3):
            rows = [r for r in warning_rows if r["mode"] == mode and r["peers"] == needed]
            sc = [r["sell_advantage_next_open_pp"] for r in rows
                  if r["sell_advantage_next_open_pp"] is not None]
            major = [r for r in rows if r["major_down_outcome_only"]]
            result["preopen_peer_confirm"][mode][str(needed)] = {
                "warnings": len(rows),
                "major_down_hits": len(major),
                "major_down_missed": result["sample"]["major_down"] - len(major),
                "nonmajor_warnings": len(rows) - len(major),
                "major_winner_false_warnings": sum(r["major_up_outcome_only"] for r in rows),
                "major_hits_before_minus5": sum(r["before_minus5"] for r in major),
                "major_hits_prior_evening": sum(r["prior_evening"] for r in major),
                "earliest_major_at": min((r["confirmed_asof"] for r in major), default=None),
                "price_scorable": len(sc),
                "modeled_sale_advantage_next_open_mean_pp": round(mean(sc), 4) if sc else None,
            }
    for rule in ENTRY_POLICIES:
        result["first_only_risk_admission"][rule] = {
            period: summarize_entry(buys, rule, period)
            for period in ("earlier", "later", "all")
        }
    return result, list(per_day.values()), warning_rows, buys


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--audit-output")
    p.add_argument("--events-output")
    p.add_argument("--buy-output")
    args = p.parse_args()
    bars = ingest([Path("/tmp/semis_52wk_5min_sip_adjusted.json"),
                   Path("/tmp/semis_peers_52wk_5min_adjusted.json")])
    daily = json.loads(Path("/tmp/semis_52weeks_alpaca_daily.json").read_text())["split"]
    audit = json.loads(Path("/tmp/v2-run10-daily-audit.json").read_text())
    result, everyday, warning_events, buys = study(bars, daily, audit)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    if args.audit_output:
        Path(args.audit_output).write_text(json.dumps(everyday, indent=2)+"\n")
    if args.events_output:
        Path(args.events_output).write_text(json.dumps(warning_events, indent=2)+"\n")
    if args.buy_output:
        Path(args.buy_output).write_text(json.dumps(buys, indent=2)+"\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
