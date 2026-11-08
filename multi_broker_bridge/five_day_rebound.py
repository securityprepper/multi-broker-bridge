"""Causal five-completed-session semiconductor rebound signal.

Pure historical/live decision helper. Never submits orders. All input OHLC bars
must be completed and adjusted to the same share/split basis.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Mapping, Sequence

ANCHORS = ("AMD", "MU", "SNDK")
BENCHMARK = "SOXX"
SYMBOLS = (*ANCHORS, BENCHMARK)


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    high: Decimal
    close: Decimal


@dataclass(frozen=True)
class SectorDecision:
    prior_five: str
    prior_five_changes: dict[str, Decimal]
    last_close_changes: dict[str, Decimal]
    momentum_15m: dict[str, Decimal]
    qualifies: bool
    reason: str
    asof: datetime


def five_day_regime(completed_daily_closes: Mapping[str, Sequence[Decimal]]) -> tuple[str, dict[str, Decimal]]:
    """Exactly six consecutive completed daily closes for each symbol.

    Close[0] is the regular close six trading sessions before target date;
    close[5] is the most recent *completed* regular close. The current
    evaluation day's price is never included.
    """
    if any(s not in completed_daily_closes or len(completed_daily_closes[s]) != 6 for s in SYMBOLS):
        raise ValueError("exactly six consecutive completed regular closes required")
    results: dict[str, Decimal] = {}
    for symbol in SYMBOLS:
        oldest, newest = (Decimal(str(completed_daily_closes[symbol][i])) for i in (0, 5))
        if oldest <= 0 or newest <= 0:
            raise ValueError("nonpositive close")
        results[symbol] = newest / oldest - 1
    leaders_up = sum(results[s] > 0 for s in ANCHORS)
    leaders_down = sum(results[s] < 0 for s in ANCHORS)
    regime = (
        "down" if leaders_down >= 2 and results[BENCHMARK] < 0 else
        "up" if leaders_up >= 2 and results[BENCHMARK] > 0 else
        "mixed"
    )
    return regime, results


def evaluate(
    completed_daily_closes: Mapping[str, Sequence[Decimal]],
    previous_regular_close: Mapping[str, Decimal],
    completed_five_minute: Mapping[str, Sequence[Candle]],
) -> SectorDecision:
    """Detect the tested sector rule from *completed* bars only.

    2-of-3 anchors up >=1.5% vs prior regular close, SOXX >=0.75%;
    2-of-3 anchor 15-minute momentum >=0.7%, SOXX nonnegative;
    2-of-3 anchor most recent close strictly above preceding 5m high.
    A next-bar buy limit may be considered only after this signal.
    """
    regime, five_day_changes = five_day_regime(completed_daily_closes)
    if any(s not in completed_five_minute or len(completed_five_minute[s]) < 4
           or s not in previous_regular_close for s in SYMBOLS):
        raise ValueError("missing completed 15-minute bars or prior close")
    cur = {s: completed_five_minute[s][-1] for s in SYMBOLS}
    latest = cur[BENCHMARK].timestamp
    for symbol in SYMBOLS:
        bars = completed_five_minute[symbol][-4:]
        if bars[-1].timestamp != latest:
            raise ValueError("misaligned five-minute candles")
        if any(b.timestamp != latest - timedelta(minutes=5 * (3-i)) for i,b in enumerate(bars)):
            raise ValueError("stale or missing five-minute intervals")
        if Decimal(str(previous_regular_close[symbol])) <= 0:
            raise ValueError("invalid prior close")
    gain = {s: cur[s].close / Decimal(str(previous_regular_close[s])) - 1 for s in SYMBOLS}
    momentum = {
        s: cur[s].close / completed_five_minute[s][-4].close - 1 for s in SYMBOLS
    }
    breadth = sum(gain[s] >= Decimal(".015") for s in ANCHORS) >= 2
    benchmark = gain[BENCHMARK] >= Decimal(".0075")
    trend = (sum(momentum[s] >= Decimal(".007") for s in ANCHORS) >= 2
             and momentum[BENCHMARK] >= 0)
    breakout = sum(
        cur[s].close > completed_five_minute[s][-2].high
        for s in ANCHORS
    ) >= 2
    qualifies = regime == "down" and breadth and benchmark and trend and breakout
    failed = [
        name for name,ok in (
            ("prior_five_down",regime=="down"),("breadth",breadth),
            ("SOXX",benchmark),("15min_momentum",trend),("breakout",breakout))
        if not ok
    ]
    return SectorDecision(regime, five_day_changes, gain, momentum,
                          qualifies,"BUY_WATCH" if qualifies else "WAIT:" + ",".join(failed),latest)
