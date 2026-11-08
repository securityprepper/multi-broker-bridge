"""V2-only conditional premarket exit decision, NOT imported by live V1 runner.

Pure research helper. NO broker calls, orders, notifications, or timer changes.
The simulation does not establish actual premarket fills, stop prices or gap risk.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
OBSERVED_MARK_TIME = time(8, 30)
PROPOSED_DEFERRED_EXIT = time(10, 30)
PROPOSED_RTH_STOP_FRACTION = Decimal(".025")


@dataclass(frozen=True)
class ExitDecision:
    action: str
    estimated_net_per_share: Decimal
    observed_at: datetime
    reference_price: Decimal


def decide_from_completed_premarket_bar(
    observed_at: datetime,
    observed_bar_end: datetime,
    observed_bar_close: Decimal,
    entry_price: Decimal,
    per_side_sell_allowance: Decimal = Decimal(".0015"),
) -> ExitDecision:
    """At 08:30 ET use only the completed 08:25-08:30 ET bar.

    observed_bar_end is the end of the last completed candle, not the start.
    A real executable quote or limit fill can differ from this mark.
    """
    if observed_at.tzinfo is None or observed_bar_end.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    local = observed_at.astimezone(ET)
    if local.time() < OBSERVED_MARK_TIME:
        raise ValueError("cannot use unfinished premarket bar")
    end = observed_bar_end.astimezone(ET)
    if end.time() != OBSERVED_MARK_TIME or end.date() != local.date():
        raise ValueError("wrong reference bar for exit decision")
    if observed_at < observed_bar_end or observed_at - observed_bar_end > timedelta(minutes=2):
        raise ValueError("reference bar unavailable or stale")
    if (entry_price <= 0 or observed_bar_close <= 0 or
            not Decimal("0") <= per_side_sell_allowance < Decimal(".02")):
        raise ValueError("invalid prices or sell allowance")
    sale = observed_bar_close * (1 - per_side_sell_allowance)
    net = sale - entry_price
    return ExitDecision(
        action="EXIT_PREMARKET" if net > 0 else "RESEARCH_HOLD_FOR_RTH",
        estimated_net_per_share=net,
        observed_at=observed_at,
        reference_price=sale,
    )
