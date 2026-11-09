"""Isolated V2-only two-sided research: late-session crash blind spots and prior-five entry caps.

All decisions rely on completed 5m candles and previous regular-session closes.
Next-bar and next-session opens enter only retrospective scoring. No broker IO.
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
from research.v2_rth_open_momentum import first_signal
from research.v2_locked_exit_policy_walkforward import policy_outcome, LATER
from research.v2_downside_early_sell_opportunity_cost import price_scenario
from research.v2_open_relative_blindspots_and_admission_caps import first_open_decline

T5 = timedelta(minutes=5)
T15 = timedelta(minutes=15)
OPEN = time(9, 30)
CLOSE_END = time(15, 55)
FIRST_LATE = time(10, 35)
RULES = ("late_strict", "late_open_1p5", "late_sector_breadth")
CAPS = ("first_only", "first_no_weak_soxx_p5", "first_no_weak_stock_p5",
        "first_stock_positive_p5", "first_both_positive_p5")


def complete_close(bars, symbol, at):
    """Only access the bar whose END is at; rejects missing/incomplete marks."""
    row = bars.get(symbol, {}).get(at - T5)
    return row[3] if row and row[3] > 0 else None


def late_context(bars, day, symbol, at, prev_closes):
    """A single point-in-time snapshot; no current-day final close."""
    if at.tzinfo is None:
        raise ValueError("timezone required")
    at = at.astimezone(ET)
    if at.date() != day or not FIRST_LATE <= at.time() <= CLOSE_END:
        return None
    if at.second or at.microsecond or at.minute % 5:
        return None
    prev = prev_closes.get(symbol)
    prev_soxx = prev_closes.get("SOXX")
    opening = bars.get(symbol, {}).get(datetime.combine(day, OPEN, ET))
    mark = complete_close(bars, symbol, at)
    older = complete_close(bars, symbol, at - T15)
    soxx = complete_close(bars, "SOXX", at)
    if not all(x is not None and x > 0 for x in (prev, prev_soxx, mark, soxx)):
        return None
    peers = [s for s in sorted(prev_closes) if s not in (symbol, "SOXX")]
    breadth = sum(complete_close(bars, peer, at) is not None and
                  100 * (complete_close(bars, peer, at) / prev_closes[peer] - 1) <= -1
                  for peer in peers)
    # Open is observable since 09:30; older completed mark may be absent.
    return {
        "at": at.isoformat(), "signal_price": mark,
        "total_pct": 100 * (mark / prev - 1),
        "open_pct": 100 * (mark / opening[0] - 1) if opening and opening[0] > 0 else None,
        "last15_pp": 100 * (mark - older) / prev if older else None,
        "soxx_pct": 100 * (soxx / prev_soxx - 1),
        "negative_peers": breadth, "peer_count": len(peers)
    }


def qualifies(rule, ctx):
    if rule not in RULES:
        raise ValueError("unknown rule")
    if ctx is None:
        return False
    if rule == "late_strict":
        return ctx["total_pct"] <= -2.5 and ctx["last15_pp"] is not None and ctx["last15_pp"] <= -1.0
    if rule == "late_open_1p5":
        return ctx["open_pct"] is not None and ctx["open_pct"] <= -1.5
    return (ctx["total_pct"] <= -3 and ctx["soxx_pct"] <= -1 and
            ctx["negative_peers"] >= 4)


def late_first(bars, day, symbol, prev_closes, rule):
    if rule not in RULES:
        raise ValueError("invalid rule")
    for m in range(10 * 60 + 35, 15 * 60 + 56, 5):
        at = datetime.combine(day, time(m // 60, m % 60), ET)
        ctx = late_context(bars, day, symbol, at, prev_closes)
        if not qualifies(rule, ctx):
            continue
        nextbar = bars.get(symbol, {}).get(at)
        return {
            "asof": at.isoformat(), "source": rule,
            "signal_price": ctx["signal_price"], "total_pct": ctx["total_pct"],
            "next_bar_open": nextbar[0] if nextbar else None,
            "context": ctx
        }
    return None


def first_of(*hits):
    return min((h for h in hits if h), key=lambda h: (h["asof"], h["source"]), default=None)


def period(rows, rule):
    sub = [r for r in rows if r["rule"] == rule]
    major = [r for r in sub if r["major_down"]]
    nonmajor = [r for r in sub if not r["major_down"]]
    prices = [r["score"]["advantage_to_next_open_pp"] for r in sub if r["score"] is not None]
    return {
        "new_warnings": len(sub),
        "new_major_hits": len(major), "new_nonmajor": len(nonmajor),
        "new_major_winners_exposed": sum(r["major_up"] for r in sub),
        "new_major_hits_before_already_down5": sum(r["event"]["total_pct"] > -5 for r in major),
        "new_earliest_major": min((r["event"]["asof"] for r in major), default=None),
        "price_scorable": len(prices),
        "nextbar_price_eligible_proxies": sum(r["score"]["eligible_price_proxy"] for r in sub
                                                if r["score"] is not None),
        "sell_advantage_next_open_mean_pp": round(mean(prices), 4) if prices else None,
        "beneficial_early_exit_count": sum(v > 0 for v in prices),
        "harmful_early_exit_count": sum(v < 0 for v in prices),
    }


def late_study(bars, daily, audit):
    universe, sessions = all_days(bars, daily)
    refs = {(r["day"], r["sym"]): r for r in universe}
    bindex = {(r["day"], r["sym"]): r for r in audit}
    if set(refs) != set(bindex) or len(bindex) != len(audit):
        raise ValueError("baseline audit and universe mismatch")
    stock_dates = sorted(date.fromisoformat(x) for x in sessions)
    following = dict(zip(stock_dates[:-1], stock_dates[1:]))
    out = []
    byday=defaultdict(dict)
    for r in universe:
        byday[r["day"]][r["sym"]]=r
    bykey=defaultdict(dict)
    severe_total = sum(r["big_down"] for r in universe)
    base_hits = sum(r["major_down"] and r["all_union"] is not None for r in audit)
    base_other = sum(not r["major_down"] and r["all_union"] is not None for r in audit)
    for r in universe:
        d = date.fromisoformat(r["day"])
        sym = r["sym"]
        base = bindex[r["day"], sym]["all_union"]
        # Every prior close is strictly from the previous completed RTH session.
        prevs = {q:old["previous_close"] for q,old in byday[r["day"]].items()}
        nxt_day = following.get(d)
        nextrow = bars[sym].get(datetime.combine(nxt_day, OPEN, ET)) if nxt_day else None
        following_open = nextrow[0] if nextrow else None
        for rule in RULES:
            ev = late_first(bars, d, sym, prevs, rule)
            if ev is None:
                continue
            sc = price_scenario(ev, r["previous_close"], following_open)
            event = {
                "day": r["day"], "sym": sym, "rule": rule,
                "major_down": r["big_down"], "major_up": r["big_up"],
                "close_pct": r["change_pct"], "base": base, "event": ev, "score": sc,
                "rth_low_outcome_only":bindex[r["day"],sym].get("rth_low_outcome_only"),
                "rth_high_outcome_only":bindex[r["day"],sym].get("rth_high_outcome_only"),
                "morning_gap_pct":bindex[r["day"],sym].get("morning_gap_pct")
            }
            out.append(event)
            bykey[(r["day"],sym)][rule]=ev
    union = {}
    early_union = {}
    for key in refs:
        original=bindex[key]["all_union"]
        d=date.fromisoformat(key[0])
        opening=first_open_decline(bars,d,key[1],1.5,sector=False)
        early_union[key]=first_of(original,opening)
        union[key] = first_of(early_union[key], *bykey[key].values())
    result = {"stockdays": len(refs), "major_down": severe_total,
              "major_up": sum(r["big_up"] for r in universe),
              "baseline_major_hits": base_hits, "baseline_other_warnings": base_other,
              "rules": {}, "remaining_misses": []}
    for rule in RULES:
        rows = [r for r in out if r["rule"] == rule]
        detail = period(out, rule)
        newly = [r for r in rows if r["major_down"] and not r["base"]]
        detail["newly_found_from_baseline_misses"] = [
            {"day":r["day"],"sym":r["sym"],"time":r["event"]["asof"],
             "close_pct":r["close_pct"],"signal_total_pct":round(r["event"]["total_pct"],4),
             "before_minus5":r["event"]["total_pct"] > -5}
            for r in newly]
        detail["new_incremental_nonmajor"] = sum(not r["major_down"] and not r["base"] for r in rows)
        detail["periods"] = {tag:period(sub, rule) for tag,sub in (
            ("earlier",[x for x in out if x["day"] < LATER.isoformat()]),
            ("later",[x for x in out if x["day"] >= LATER.isoformat()]))}
        result["rules"][rule] = detail
    for key, hit in union.items():
        base_row=bindex[key]
        if base_row["major_down"] and hit is None:
            result["remaining_misses"].append({
                "day":key[0], "sym":key[1], "close_pct":base_row["close_pct"]})
    result["prior_early_union"]={
        "major_hits":sum(bindex[k]["major_down"] and v is not None for k,v in early_union.items()),
        "nonmajor_warnings":sum(not bindex[k]["major_down"] and v is not None for k,v in early_union.items())
    }
    result["late_added_to_prior_early_union"]=[
        {"day":k[0],"sym":k[1],"close_pct":bindex[k]["close_pct"],
         "first_late_at":v["asof"],
         "first_late_total_pct":round(100*(v["signal_price"]/refs[k]["previous_close"]-1),4)}
        for k,v in union.items() if bindex[k]["major_down"] and early_union[k] is None and v is not None]
    result["union_all_late"] = {
        "major_hits": severe_total - len(result["remaining_misses"]),
        "major_misses": len(result["remaining_misses"]),
        "nonmajor_warnings": sum(not bindex[k]["major_down"] and h is not None
                                 for k,h in union.items()),
        "major_before_already_down5":sum(bindex[k]["major_down"] and h is not None and
            100*(h["signal_price"]/refs[k]["previous_close"]-1)>-5
                                         for k,h in union.items()),
        "new_early_or_missed_major":sum(
            bindex[k]["major_down"] and h is not None and
            (bindex[k]["all_union"] is None or h["asof"] < bindex[k]["all_union"]["asof"])
            for k,h in union.items())
    }
    return result, out


def prior_five_return(closes, sessions, index, sym):
    """Exactly five complete prior sessions [i-6, i-1]; no current day."""
    if index < 6:
        return None
    window=[closes.get(sym, {}).get(d) for d in sessions[index-6:index]]
    if len(window) != 6 or any(v is None or v <= 0 for v in window):
        return None
    return 100*(window[-1] / window[0] - 1)


def cap_allowed(which, p_stock, p_sector):
    if which not in CAPS:
        raise ValueError("unknown entry cap rule")
    if which == "first_only":
        return True
    if which == "first_no_weak_soxx_p5":
        return p_sector is not None and p_sector > -5
    if which == "first_no_weak_stock_p5":
        return p_stock is not None and p_stock > -5
    if which == "first_stock_positive_p5":
        return p_stock is not None and p_stock >= 0
    return p_stock is not None and p_sector is not None and p_stock >= 0 and p_sector >= 0


def cap_study(bars, daily):
    universe, sessions_s = all_days(bars, daily)
    sessions = [date.fromisoformat(x) for x in sessions_s]
    indexes = {x:i for i,x in enumerate(sessions)}
    # Load historical closes; the live feature strictly indexes dates < target.
    closes=defaultdict(dict)
    for row in universe:
        d=date.fromisoformat(row["day"])
        closebar=bars[row["sym"]].get(datetime.combine(d,time(15,55),ET))
        if closebar and closebar[3]>0:
            closes[row["sym"]][d]=closebar[3]
    grouped=defaultdict(list)
    for row in universe:
        d=date.fromisoformat(row["day"])
        e=first_signal(bars,d,row["sym"],"early_1030")
        if not e:
            continue
        score=policy_outcome(bars[row["sym"]],e,row["mark14"],"hold_1400")
        if score is None:
            continue
        grouped[row["day"]].append({
            "at":e["at"],"day":row["day"],"sym":row["sym"],
            "strength":e["own_open_pct"],"return":score["net_pct"],
            "major_up":row["big_up"],"major_down":row["big_down"],
            "p_stock":prior_five_return(closes,sessions,indexes[d],row["sym"]),
            "p_sector":prior_five_return(closes,sessions,indexes[d],"SOXX"),
            "price_eligible":score["eligible_entry"]
        })
    selected={name:[] for name in CAPS}
    signal_days=sorted(grouped)
    for day in signal_days:
        candidates=grouped[day]
        first = min(candidates, key=lambda x:(x["at"],-x["strength"],x["sym"]))
        for name in CAPS:
            selected[name].append(first if cap_allowed(name,first["p_stock"],first["p_sector"]) else None)
    result = {"signal_days":len(grouped),"original_signals":sum(map(len,grouped.values())),
              "policies":{}}
    for name, rows in selected.items():
        res = {}
        for key in ("all","earlier","later"):
            subset=[r for day,r in zip(signal_days,rows)
                    if key=="all" or (day<LATER.isoformat())==(key=="earlier")]
            vals=[r["return"] if r is not None else 0.0 for r in subset]
            picked=[r for r in subset if r is not None]
            res[key]={
                "baseline_days":len(subset),"admitted":len(picked),
                "zero_if_no_trade_day_equal_pct":round(mean(vals),4) if vals else None,
                "winners":sum(v>0 for v in vals),"losers":sum(v<0 for v in vals),
                "major_up_stockdays_retained":sum(r["major_up"] for r in picked),
                "major_down_stockdays_retained":sum(r["major_down"] for r in picked),
                "price_eligible_proxy":sum(r["price_eligible"] for r in picked),
                "skipped_due_filter":len(subset)-len(picked)
            }
        result["policies"][name]=res
    return result


def analyze(bars, daily, audit):
    downside,events=late_study(bars,daily,audit)
    return {"downside":downside,
            "upside":cap_study(bars,daily),
            "limits":"SIP split-adjusted 5m OHLC only. Next-bar and next open are scoring proxies, not executable NBBO/BOATS quotes or filled orders. Missing V1 trades and news/futures."},events


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--audit",default="/tmp/v2-run10-daily-audit.json")
    a.add_argument("--output",required=True)
    a.add_argument("--events-output")
    args=a.parse_args()
    bars=ingest(("/tmp/semis_52wk_5min_sip_adjusted.json",
                 "/tmp/semis_peers_52wk_5min_adjusted.json"))
    daily=json.loads(Path("/tmp/semis_52weeks_alpaca_daily.json").read_text())["split"]
    audit=json.loads(Path(args.audit).read_text())
    result,events=analyze(bars,daily,audit)
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    if args.events_output:
        Path(args.events_output).write_text(json.dumps(events,indent=1,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()