"""Offline causal 1-minute availability audit for premarket four-candle strategies.

This is an upper bound on *data availability*, not a valid BUY_WATCH,
predicted price direction, broker quote, or order execution. The input
is an existing historical Alpaca SIP trade-bar cache; no credentials/network.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SYMBOLS = ("SOXX", "AMD", "MU", "SNDK")
DECISION_SECONDS = 40
PUBLICATION_LAG_SECONDS = 15
PREMARKET_MINUTES = 330


def good_ohlc(bar):
    if isinstance(bar, dict):
        values = [bar.get(k) for k in ("o", "h", "l", "c")]
    elif isinstance(bar, (list, tuple)):
        values = list(bar[:4])
    else:
        return False
    if len(values) != 4:
        return False
    try:
        return all(not isinstance(x, bool) and math.isfinite(float(x)) and
                   float(x) > 0 for x in values)
    except (ValueError, TypeError, OverflowError):
        return False


def observed_minutes(day, observations):
    """Only include exact, valid local session bars, never forward-fill."""
    parsed_date = datetime.strptime(day, "%Y-%m-%d").date()
    if not isinstance(observations, dict):
        raise ValueError("expected per-symbol dictionary")
    available = {}
    for sym in SYMBOLS:
        rows = observations.get(sym)
        if not isinstance(rows, dict):
            raise ValueError("missing symbol " + sym)
        hits = set()
        for text, bar in rows.items():
            stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone-less bar")
            local = stamp.astimezone(ET)
            if local.date() != parsed_date or not (4 <= local.hour < 10):
                continue
            if (local.hour == 9 and local.minute >= 30) or (
                local.second != 0 or local.microsecond != 0
            ):
                continue
            if good_ohlc(bar):
                hits.add(local.strftime("%H:%M"))
        available[sym] = hits
    return available


def day_audit(day, obs):
    available = observed_minutes(day, obs)
    start = datetime.fromisoformat(day + "T04:00:00").replace(tzinfo=ET)
    counts = {
        "onebar_allfour": 0,
        "onebar_own_three": 0,
        "fourbar_amd": 0,
        "fourbar_amd_and_one_other_peer": 0,
        "fourbar_own_three": 0,
        "fourbar_allfour": 0,
        "fourbar_amd_plus_one_and_soxx_current": 0,
    }
    for offset in range(PREMARKET_MINUTES):
        now = start + timedelta(minutes=offset)
        hhmm = now.strftime("%H:%M")
        one = {s: hhmm in available[s] for s in SYMBOLS}
        counts["onebar_own_three"] += all(one[s] for s in ("AMD", "MU", "SNDK"))
        counts["onebar_allfour"] += all(one.values())
        if offset < 4:  # Cache deliberately begins at 04:00 ET.
            continue
        # At decision HH:MM:40, only preceding bar *starts* HH:MM-1
        # through HH:MM-4 can be completed and published (+15s).
        required = [(now - timedelta(minutes=i)).strftime("%H:%M")
                    for i in range(1, 5)]
        four = {s: all(k in available[s] for k in required) for s in SYMBOLS}
        amd = four["AMD"]
        pair = amd and (four["MU"] or four["SNDK"])
        own = pair and four["MU"] and four["SNDK"]
        counts["fourbar_amd"] += amd
        counts["fourbar_amd_and_one_other_peer"] += pair
        counts["fourbar_own_three"] += own
        counts["fourbar_allfour"] += own and four["SOXX"]
        counts["fourbar_amd_plus_one_and_soxx_current"] += pair and one["SOXX"]
    counts["onebar_denominator"] = PREMARKET_MINUTES
    counts["fourbar_denominator"] = PREMARKET_MINUTES - 4
    return {"date": day, **counts}


def aggregate(source):
    if not isinstance(source, dict) or not source:
        raise ValueError("empty data")
    rows = [day_audit(day, obs) for day, obs in sorted(source.items())]
    one_den = sum(row["onebar_denominator"] for row in rows)
    four_den = sum(row["fourbar_denominator"] for row in rows)
    metrics = [k for k in rows[0] if k.startswith(("onebar_", "fourbar_"))
               and not k.endswith("_denominator")]
    totals = {k: sum(row[k] for row in rows) for k in metrics}
    return {
        "study": "historical premarket four-completed-candle data availability only",
        "independent_forward_holdout": False,
        "executable_quotes_or_fills": False,
        "buy_watch_predicate_verified": False,
        "holiday_or_broker_orders_changed": False,
        "data_source": "existing seven-session split-adjusted Alpaca SIP 1Min trade OHLC cache",
        "source_candle_timestamp": "bar START in America/New_York",
        "decision_timestamp": "minute HH:MM:40 ET",
        "fourbar_lookback": "HH:MM-4 through HH:MM-1 inclusive",
        "minimum_publication_lag_seconds": PUBLICATION_LAG_SECONDS,
        "n_days": len(rows), "onebar_denominator": one_den,
        "fourbar_denominator": four_den, "counts": totals,
        "onebar_allfour_pct": round(100 * totals["onebar_allfour"] / one_den, 2),
        "fourbar_allfour_pct": round(100 * totals["fourbar_allfour"] / four_den, 2),
        "fourbar_amd_plus_one_pct": round(
            100 * totals["fourbar_amd_and_one_other_peer"] / four_den, 2),
        "rows": rows,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = aggregate(json.loads(Path(a.input).read_text()))
    Path(a.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows",)},
                     sort_keys=True))


if __name__ == "__main__":
    main()

