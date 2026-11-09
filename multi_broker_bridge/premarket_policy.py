"""PAPER-only premarket exits and one discounted bullish re-entry per symbol.

Policy intentionally keeps the existing emergency loss exit and the same-day
13:40–14:00 Chicago flat requirement. It does not use LIVE broker endpoints.
Historical bars are not executable quotes. Every re-entry additionally needs
a new actual one-minute qualified BUY_WATCH from sector breadth.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal,InvalidOperation
from zoneinfo import ZoneInfo

CHICAGO=ZoneInfo("America/Chicago")
SUBSTANTIAL_PROFIT=Decimal("0.020")   # 2.0% executable gain needed
MIN_REALIZED_PROFIT=Decimal("0.020") # previous exit fully filled at >=2%
EMERGENCY_LOSS=Decimal("-0.025")      # independent HARD risk exception
REENTRY_DISCOUNT=Decimal("0.0025")    # ask at least 0.25% below sold price
PREMARKET_END=time(8,30)
REENTRY_END=time(10,0)
RTH_EXIT_OVERRIDE=time(13,40)
MAX_REENTRIES_PER_SYMBOL_DAY=1
MIN_REENTRY_DELAY=timedelta(minutes=2)

def is_early_market(now:datetime)->bool:
    local=now.astimezone(CHICAGO)
    clock=local.time().replace(tzinfo=None)
    return clock<PREMARKET_END or clock>=time(19,0)


def quoted_return(entry:Decimal,bid:Decimal)->Decimal:
    if not entry.is_finite() or entry<=0 or not bid.is_finite() or bid<=0:
        raise ValueError("Invalid verified quote / entry")
    return (bid-entry)/entry


def premarket_sell_decision(now:datetime,entry:Decimal,bid:Decimal,reason:str)->str:
    """Only profit-taking on a reversal, or an emergency stop.

    A normal one-minute down-candle, a +1% target, or small fluctuations
    cannot force an early sale. The emergency exception remains essential
    to avoid unlimited loss exposure in leveraged/volatile instruments.
    """
    if not is_early_market(now):
        return "NOT_PREMARKET"
    gain=quoted_return(entry,bid)
    if gain<=EMERGENCY_LOSS:
        return "EMERGENCY_DOWNSIDE_EXIT"
    if (gain>=SUBSTANTIAL_PROFIT
            and reason in ("premarket substantial profit reversal",
                           "premarket confirmed trailing profit reversal")):
        return "SUBSTANTIAL_PROFIT_TAKE"
    return "HOLD_FOR_TREND"


def eligible_discount_reentry(
    now:datetime,*,sell_filled_at:datetime,
    sell_filled_price:Decimal,entry_filled_price:Decimal,
    next_verified_ask:Decimal,fully_filled:bool,
    actual_rising_breadth:bool,positions_absent:bool,
    pending_orders_absent:bool,already_reentered:bool
)->bool:
    """Requires real broker readback, not trade intent/accepted order."""
    if (now.tzinfo is None or sell_filled_at.tzinfo is None
            or not fully_filled or not actual_rising_breadth
            or not positions_absent or not pending_orders_absent
            or already_reentered):
        return False
    local=now.astimezone(CHICAGO)
    t=local.time().replace(tzinfo=None)
    if not (t<REENTRY_END and local.weekday()<5):
        return False
    sold_local=sell_filled_at.astimezone(CHICAGO)
    if not (sold_local.date()==local.date() and
            sold_local.time().replace(tzinfo=None)<PREMARKET_END):
        return False
    if not (MIN_REENTRY_DELAY<=now-sell_filled_at<=timedelta(hours=10)):
        return False
    for x in (sell_filled_price,entry_filled_price,next_verified_ask):
        if not isinstance(x,Decimal) or not x.is_finite() or x<=0:
            return False
    if (sell_filled_price-entry_filled_price)/entry_filled_price<MIN_REALIZED_PROFIT:
        return False
    return next_verified_ask<=sell_filled_price*(Decimal(1)-REENTRY_DISCOUNT)
