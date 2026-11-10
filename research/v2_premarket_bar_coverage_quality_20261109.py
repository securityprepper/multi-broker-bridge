"""Read-only, no-lookahead Alpaca SIP 1m premarket bar-coverage audit.
Does not infer trading signals, future moves, quoted liquidity, or executable fills.
Input is the prior seven-session JSON cache, no credentials or network.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SYMBOLS = ("SOXX", "AMD", "MU", "SNDK")
PEERS = ("AMD", "MU", "SNDK")
START, END = time(4), time(9, 30)
FULL_MINUTES = 330
PUBLISH_DELAY = timedelta(seconds=15)

def iso_minute_utc(ts):
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("unqualified timestamp")
    return dt.astimezone(ET)

def _valid_price_bar(bar):
    # Never infer missing bars from adjacent trades; if present, require positive
    # finite OHLC fields where the source supplies such data.
    import math
    if isinstance(bar, (list, tuple)):
        vals = bar[:4]
    elif isinstance(bar, dict):
        vals = [bar[k] for k in ("o", "h", "l", "c")] if all(k in bar for k in ("o", "h", "l", "c")) else [bar.get("c")]
    else:
        return False
    try:
        vals = [float(x) for x in vals]
        return len(vals) > 0 and all(math.isfinite(x) and x > 0 for x in vals)
    except (TypeError, ValueError):
        return False

def minute_sets(day: str, symbols: dict):
    target = date.fromisoformat(day)
    present = {}
    for sym in SYMBOLS:
        source = symbols.get(sym, {})
        if not isinstance(source, dict):
            raise ValueError("invalid per-symbol bar mapping")
        valid = set()
        for raw_ts, bar in source.items():
            dt = iso_minute_utc(raw_ts)
            if dt.date() != target or not (START <= dt.time() < END):
                continue
            if dt.second != 0 or dt.microsecond != 0:
                raise ValueError("nonaligned 1-minute bar")
            if _valid_price_bar(bar):
                valid.add(dt.strftime("%H:%M"))
        present[sym] = valid
    return present

def audit_day(day, source):
    present = minute_sets(day, source)
    peer_joint = set.intersection(*(present[s] for s in PEERS))
    full_joint = peer_joint.intersection(present["SOXX"])
    def bounds(times):
        a = sorted(times)
        return {"first_bar_start_et": a[0] if a else None, "last_bar_start_et": a[-1] if a else None}
    return {"day": day, "session": "04:00-09:30 America/New_York",
            "required_exact_simultaneous_1m_bars": list(SYMBOLS),
            "minutes_possible": FULL_MINUTES,
            "per_symbol_present": {s: len(present[s]) for s in SYMBOLS},
            "amd_mu_sndk_3of3_present": len(peer_joint),
            "soxx_and_all_three_peers_present": len(full_joint),
            "soxx_allpeers_exact_minute_coverage_pct": round(100*len(full_joint)/FULL_MINUTES, 2),
            "all_four_bounds": bounds(full_joint),
            "imputed_missing_bars": 0,
            "executable_nbbo_or_fill_verified": False}

def bar_available_at(day, hhmm):
    # The OHLC row is keyed by its START minute. Do not treat 04:18's row
    # as known at 04:18; earliest prudent decision is 04:19:15 ET.
    h, m = map(int, hhmm.split(":"))
    return datetime.combine(date.fromisoformat(day), time(h, m), ET) + timedelta(minutes=1) + PUBLISH_DELAY

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    a = parser.parse_args()
    data = json.loads(Path(a.input).read_text())
    if not isinstance(data, dict) or not data:
        raise ValueError("expected nonempty day-to-symbol cache")
    rows = [audit_day(day, bars) for day, bars in sorted(data.items())]
    results = {"scope":"7-session historical coverage, NOT an independent performance holdout",
               "source":"Alpaca historical SIP 1Min trade bars in existing read-only host cache",
               "decisions_only_after_bar_completion_plus_15s": True,
               "coverage_proxy_not_trade_precision": True,
               "days": len(rows),
               "total_full_joint_minute_bars": sum(x["soxx_and_all_three_peers_present"] for x in rows),
               "total_possible_minutes": len(rows)*FULL_MINUTES,
               "mean_joint_coverage_pct":round(sum(x["soxx_and_all_three_peers_present"] for x in rows)/(len(rows)*FULL_MINUTES)*100,2),
               "rows":rows}
    Path(a.output).write_text(json.dumps(results, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in results.items() if k!="rows"}, sort_keys=True))
if __name__ == "__main__":
    main()
