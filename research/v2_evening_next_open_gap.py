"""Research-only two-sided evening gap warnings using completed 52-week SIP five-minute bars.

At fixed Eastern 17:00 / 19:00 observations, use only same-day 15:55
regular-session completed close, current completed evening bar, same-time
SOXX/peer observations, and five completed regular-session closes. Never
use next-day opening/closing outcomes to produce a warning. No broker API.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path
from statistics import mean
from random import Random

ET = ZoneInfo("America/New_York")
CLOCKS = (time(17), time(19))
RTH_CLOSE_START = time(15, 55)
OPEN_START = time(9, 30)
BREADTH_PEERS = 4
MIN_BAR_VOLUME = 1
LATER = "2026-09-01"


def parse_bar(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(ET)


def index_bars(data):
    indexed = {}
    for sym, rows in data.items():
        ix = {}
        for timestamp, ohlcv in rows.items():
            at = parse_bar(timestamp)
            if at.tzinfo is None or len(ohlcv) < 5 or ohlcv[3] <= 0:
                raise ValueError("invalid bar")
            ix[(at.date().isoformat(), at.time())] = tuple(ohlcv)
        indexed[sym] = ix
    return indexed


def snapshot_bar(ix, day, clock):
    if clock not in CLOCKS:
        raise ValueError("unsupported as-of clock")
    # A bar stamped 16:55 is not known until 17:00; 18:55 until 19:00.
    start = (datetime.combine(datetime.fromisoformat(day).date(), clock)
             - timedelta(minutes=5)).time()
    bar = ix.get((day, start))
    return bar if bar is not None and bar[4] >= MIN_BAR_VOLUME else None


def previous_five_return(prior_days, closes, day):
    """Last FIVE completed sessions including evening's already-closed day."""
    if day not in prior_days:
        return None
    n = prior_days.index(day)
    if n < 5:
        return None
    old = closes.get(prior_days[n - 5])
    cur = closes.get(day)
    return 100 * (cur / old - 1) if old and cur else None


def warning(stock_pct, sector_pct, peer_pcts):
    """Fixed symmetric hypotheses, no next-day labels, no tuning per date."""
    if stock_pct is None:
        return None
    down_solo = stock_pct <= -2.5
    up_solo = stock_pct >= 2.5
    down_breadth = (sector_pct is not None and sector_pct <= -0.5
                    and sum(p <= -0.75 for p in peer_pcts) >= BREADTH_PEERS
                    and stock_pct <= -1.5)
    up_breadth = (sector_pct is not None and sector_pct >= 0.5
                  and sum(p >= 0.75 for p in peer_pcts) >= BREADTH_PEERS
                  and stock_pct >= 1.5)
    if down_solo or down_breadth:
        return "DOWN"
    if up_solo or up_breadth:
        return "UP"
    return None


def point_available_close(ix, day):
    b = ix.get((day, RTH_CLOSE_START))
    return b[3] if b and b[4] > 0 else None


def strict_overlap_at(ix, day, clock, regular_close):
    """Total -2.5% INCLUDES most recent -1.0 percentage-point 15m fall."""
    now = snapshot_bar(ix, day, clock)
    if now is None or not regular_close:
        return None
    previous_start = (datetime.combine(datetime.fromisoformat(day).date(), clock)
                      - timedelta(minutes=20)).time()
    before = ix.get((day, previous_start))
    if before is None or before[4] < MIN_BAR_VOLUME:
        return None  # Missing observations are not a negative trigger.
    total_pp = 100 * (now[3] / regular_close - 1)
    last15_pp = 100 * ((now[3] - before[3]) / regular_close)
    return {
        "total_pct": round(total_pp, 5),
        "last15_pp": round(last15_pp, 5),
        "trigger": total_pp <= -2.5 and last15_pp <= -1.0,
    }


def compute_rows(indexed, clocks=CLOCKS, baseline=None):
    all_days = sorted({day for ix in indexed.values()
                       for day, tm in ix if tm == OPEN_START})
    closes = {sym: {d: point_available_close(ix, d) for d in all_days}
              for sym, ix in indexed.items()}
    rows = []
    for d_index in range(len(all_days) - 1):
        day, next_day = all_days[d_index:d_index+2]
        for sym, ix in indexed.items():
            if baseline is not None and (next_day, sym) not in baseline:
                continue
            c = closes[sym].get(day)
            nxt_open_bar = ix.get((next_day, OPEN_START))
            nxt_close = closes[sym].get(next_day)
            if not c:
                continue
            past5 = previous_five_return(all_days, closes[sym], day)
            gap = 100*(nxt_open_bar[0]/c-1) if nxt_open_bar else None
            next_close_pct = 100*(nxt_close/c-1) if nxt_close else None
            row = {
                "day": day, "next_session": next_day, "symbol": sym,
                "period": "earlier" if next_day < LATER else "later",
                "prior5_completed_sessions_pct": round(past5, 4) if past5 is not None else None,
                "next_open_gap_outcome_only": round(gap, 4) if gap is not None else None,
                "next_close_outcome_only": round(next_close_pct, 4) if next_close_pct is not None else None,
                "warnings": {}, "observed": {}, "strict_overlap": {},
            }
            for clock in clocks:
                label = clock.strftime("%H:%M")
                bar = snapshot_bar(ix, day, clock)
                if not bar:
                    row["observed"][label] = False
                    continue
                row["observed"][label] = True
                row["strict_overlap"][label] = strict_overlap_at(ix, day, clock, c)
                stock_pct = 100*(bar[3]/c-1)
                sector_ix = indexed.get("SOXX", {})
                sector_bar = snapshot_bar(sector_ix, day, clock)
                sector_close = closes.get("SOXX", {}).get(day)
                sector_pct = (100*(sector_bar[3]/sector_close-1)
                              if sector_bar and sector_close else None)
                peers = []
                for peer, peer_ix in indexed.items():
                    if peer == sym or peer == "SOXX":
                        continue
                    b = snapshot_bar(peer_ix, day, clock)
                    ref = closes[peer].get(day)
                    if b and ref:
                        peers.append(100*(b[3]/ref-1))
                signal = warning(stock_pct, sector_pct, peers) if past5 is not None else None
                if signal:
                    at = datetime.combine(datetime.fromisoformat(day).date(), clock, tzinfo=ET)
                    next_time = (datetime.combine(at.date(), clock, ET)
                                 + timedelta(minutes=0)).time()
                    # At 17:00 or 19:00 the following stamped bar is
                    # only a proxy. No claim of venue eligibility or fills.
                    following = ix.get((day, next_time))
                    quoted_proxy = following[0] if following and following[4] > 0 else None
                    score = None
                    if quoted_proxy and nxt_open_bar:
                        score = (100*(quoted_proxy-nxt_open_bar[0])/c
                                 if signal == "DOWN"
                                 else 100*(nxt_open_bar[0]-quoted_proxy)/c)
                        score -= 0.15  # hypothetical one-way friction; not a spread estimate
                    row["warnings"][label] = {
                        "asof": at.isoformat(), "direction": signal,
                        "completed_bar_close": round(bar[3], 4),
                        "stock_evening_pct": round(stock_pct, 4),
                        "sector_evening_pct": round(sector_pct, 4) if sector_pct is not None else None,
                        "peer_count_observed": len(peers),
                        "peer_down": sum(p <= -0.75 for p in peers),
                        "peer_up": sum(p >= 0.75 for p in peers),
                        "next_bar_open_proxy": quoted_proxy,
                        "estimated_advantage_vs_next_open_pp_outcome_only":
                            round(score, 4) if score is not None else None,
                    }
            rows.append(row)
    return rows


def summarize(rows):
    out = {}
    for tm in ("17:00", "19:00"):
        samples = [r for r in rows if r["next_open_gap_outcome_only"] is not None]
        observed = [r for r in samples if r["observed"].get(tm)]
        stats = {"base_stockdays": len(samples), "evening_bar_observed": len(observed)}
        for direction, outcome_sign in (("DOWN", -1), ("UP", 1)):
            severe = [r for r in samples if r["next_open_gap_outcome_only"]*outcome_sign >= 5]
            hit = [r for r in severe if r["warnings"].get(tm, {}).get("direction") == direction]
            triggered = [r for r in samples if r["warnings"].get(tm, {}).get("direction") == direction]
            false = [r for r in triggered if r["next_open_gap_outcome_only"]*outcome_sign < 5]
            scores = [r["warnings"][tm]["estimated_advantage_vs_next_open_pp_outcome_only"]
                      for r in triggered
                      if r["warnings"][tm]["estimated_advantage_vs_next_open_pp_outcome_only"] is not None]
            warned_before_gap = sum(
                r["warnings"][tm]["stock_evening_pct"]*outcome_sign < 5 for r in hit)
            strict = [r for r in samples if r["strict_overlap"].get(tm, {}) and
                      r["strict_overlap"][tm]["trigger"]] if direction == "DOWN" else []
            strict_hits = [r for r in strict if r["next_open_gap_outcome_only"] <= -5]
            stats[direction.lower()] = {
                "strict_overlap_signals": len(strict),
                "strict_overlap_severe_down_hits": len(strict_hits),
                "strict_overlap_nonmajor_warnings": len(strict)-len(strict_hits),
                "severe_gaps": len(severe), "severe_gaps_with_evening_data":
                    sum(r["observed"].get(tm, False) for r in severe),
                "hit": len(hit), "missed": len(severe)-len(hit),
                "nonsevere_warnings": len(false), "all_warnings": len(triggered),
                "hit_before_already_5pct_evening": warned_before_gap,
                "first_severe_warning":
                    min((r["warnings"][tm]["asof"]+" "+r["symbol"] for r in hit),default=None),
                "mean_selling_or_buying_advantage_vs_next_open_pp_proxy":
                    round(mean(scores), 4) if scores else None,
                "nextbar_proxy_scorable": len(scores),
                "earlier": {}, "later": {},
            }
            for p in ("earlier", "later"):
                sub = [r for r in triggered if r["period"] == p]
                vals = [r["warnings"][tm]["estimated_advantage_vs_next_open_pp_outcome_only"]
                        for r in sub if r["warnings"][tm]["estimated_advantage_vs_next_open_pp_outcome_only"] is not None]
                stats[direction.lower()][p] = {
                    "signals": len(sub), "mean_proxy_pp": round(mean(vals),4) if vals else None,
                    "severe_gap_hits": sum(r["next_open_gap_outcome_only"]*outcome_sign >= 5 for r in sub),
                }
        out[tm] = stats
    # Earliest available evening alarm across fixed 17:00 and 19:00 snapshots.
    union = {}
    for direction, sign in (("DOWN", -1), ("UP", 1)):
        evaluable = [r for r in rows if r["next_open_gap_outcome_only"] is not None]
        signals = [r for r in evaluable if any(
            w.get("direction") == direction for w in r["warnings"].values())]
        severe = [r for r in evaluable
                  if r["next_open_gap_outcome_only"]*sign >= 5]
        hits = [r for r in signals if r["next_open_gap_outcome_only"]*sign >= 5]
        union[direction.lower()] = {
            "severe_gaps": len(severe), "hits": len(hits),
            "missed": len(severe)-len(hits),
            "nonmajor_warnings": len(signals)-len(hits),
            "warnings": len(signals),
            "first_true_warning": min((min(
                v["asof"] for v in r["warnings"].values()
                if v["direction"] == direction)+" "+r["symbol"]
                for r in hits), default=None),
        }
    out["either_17_or_19"] = union
    out["previous_five_available_stockdays"] = sum(
        r["prior5_completed_sessions_pct"] is not None for r in rows)
    return out



def independent_day_diagnostics(rows, n_bootstrap=5000, seed=20261109):
    """Outcome-only resampling of independent next-RTH dates, not instruments.

    Bootstrap assumes independent calendar dates and does NOT address serial
    dependence, price/quote fill uncertainty, or strategy selection.
    """
    output = {}
    for direction, sign in (("DOWN", -1), ("UP", 1)):
        byday = defaultdict(list)
        severe_days = set()
        captured_days = set()
        for r in rows:
            gap = r["next_open_gap_outcome_only"]
            if gap is None:
                continue
            if gap * sign >= 5:
                severe_days.add(r["next_session"])
            alarms = [w for w in r["warnings"].values()
                      if w["direction"] == direction]
            if not alarms:
                continue
            first = min(alarms, key=lambda w: w["asof"])
            if gap * sign >= 5:
                captured_days.add(r["next_session"])
            if first["estimated_advantage_vs_next_open_pp_outcome_only"] is not None:
                byday[r["next_session"]].append(
                    first["estimated_advantage_vs_next_open_pp_outcome_only"])
        day_scores = [mean(vals) for _, vals in sorted(byday.items())]
        if day_scores:
            rng = Random(seed)
            boot = sorted(mean(rng.choices(day_scores, k=len(day_scores)))
                          for _ in range(n_bootstrap))
            ci = [round(boot[int(n_bootstrap*0.025)], 4),
                  round(boot[int(n_bootstrap*0.975)-1], 4)]
        else:
            ci = None
        output[direction.lower()] = {
            "independent_warned_sessions": len(day_scores),
            "independent_severe_gap_sessions": len(severe_days),
            "severe_gap_sessions_caught": len(captured_days),
            "day_equal_mean_proxy_pp": round(mean(day_scores), 4) if day_scores else None,
            "naive_independent_session_bootstrap95_pp": ci,
            "bootstrap_draws": n_bootstrap, "bootstrap_seed": seed,
        }
    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-input",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    ap.add_argument("--peers-input",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    ap.add_argument("--baseline-audit",default="/tmp/v2-run10-daily-audit.json")
    ap.add_argument("--results",required=True)
    ap.add_argument("--audit",required=True)
    a=ap.parse_args()
    bars=json.load(open(a.main_input))
    peers=json.load(open(a.peers_input))
    if set(bars).intersection(peers):
        raise ValueError("duplicate data series")
    bars.update(peers)
    baseline_list = json.load(open(a.baseline_audit))
    baseline = {(r["day"],r["sym"]) for r in baseline_list}
    if len(baseline) != len(baseline_list):
        raise ValueError("duplicate baseline rows")
    rows=compute_rows(index_bars(bars), baseline=baseline)
    if {(r["next_session"],r["symbol"]) for r in rows} != baseline:
        raise ValueError("incomplete baseline intersection")
    summary=summarize(rows)
    summary["independent_session_diagnostics"] = independent_day_diagnostics(rows)
    Path(a.results).write_text(json.dumps(summary,indent=2)+"\n")
    Path(a.audit).write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
