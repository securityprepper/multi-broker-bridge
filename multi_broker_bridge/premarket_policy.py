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
# Paper-only, broker-independent software limits; only extended-hours LIMIT
# orders are eligible on Alpaca. Neither is a native overnight stop.
STEADY_PEAK_TRAIL=Decimal("0.025")
DEFAULT_PEAK_TRAIL=Decimal("0.020")
SPIKE_MIN_PROFIT=Decimal("0.020")
SPIKE_RETRACE=Decimal("0.005")
SPIKE_ONE_MINUTE_JUMP=Decimal("0.012")
SUSTAINED_LOOKBACK=timedelta(minutes=45)
SUSTAINED_MIN_BARS=25
SUSTAINED_MIN_GAIN=Decimal("0.008")
SUSTAINED_GREEN_FRACTION=Decimal("0.53")
SUSTAINED_MAX_CLOSE_DRAWDOWN=Decimal("0.020")


def sustained_trend_shape(bars, now:datetime)->bool:
    """Recognize a distributed overnight rise, not a single jump.

    Input is a sequence of valid Alpaca completed one-minute OHLC bars. Do
    not use prospective highs or a bar whose minute has not yet completed.
    This is a heuristic requiring additional out-of-sample validation.
    """
    if now.tzinfo is None:
        return False
    recent=sorted((b for b in bars
                   if b.timestamp.tzinfo is not None
                   and timedelta(0)<=now-b.timestamp-timedelta(minutes=1)
                   <=SUSTAINED_LOOKBACK),
                  key=lambda b:b.timestamp)
    if len(recent)<SUSTAINED_MIN_BARS:
        return False
    if recent[-1].timestamp-recent[0].timestamp<timedelta(minutes=25):
        return False
    if now-(recent[-1].timestamp+timedelta(minutes=1))>timedelta(minutes=3):
        return False
    if any(recent[i].timestamp<=recent[i-1].timestamp
           or recent[i].timestamp-recent[i-1].timestamp>timedelta(minutes=3)
           for i in range(1,len(recent))):
        return False
    first,last=recent[0].close,recent[-1].close
    if first<=0 or (last/first-1)<SUSTAINED_MIN_GAIN:
        return False
    green=0
    peak=first
    deepest=Decimal(0)
    for prev,cur in zip(recent,recent[1:]):
        change=cur.close/prev.close-1
        if change>SPIKE_ONE_MINUTE_JUMP:
            return False
        if change>0:green+=1
        peak=max(peak,cur.close)
        deepest=min(deepest,cur.close/peak-1)
    if deepest < -SUSTAINED_MAX_CLOSE_DRAWDOWN:
        return False
    return Decimal(green)/Decimal(len(recent)-1)>=SUSTAINED_GREEN_FRACTION


def recent_price_spike(bars,now:datetime)->bool:
    """Detect a recent one-minute discontinuity, not ordinary smooth gains."""
    recent=sorted((b for b in bars
                   if b.timestamp.tzinfo is not None
                   and timedelta(0)<=now-b.timestamp-timedelta(minutes=1)
                   <=timedelta(minutes=12)),key=lambda b:b.timestamp)
    if len(recent)<2:
        return False
    return any((cur.close/prev.close-1)>=SPIKE_ONE_MINUTE_JUMP
               for prev,cur in zip(recent,recent[1:])
               if 0<=(cur.timestamp-prev.timestamp).total_seconds()<=90)


def trading_session_day(now:datetime):
    """Map Sunday 19:00 CT and following Monday morning to Monday session."""
    local=now.astimezone(CHICAGO)
    if local.time().replace(tzinfo=None)>=time(19,0):
        return (local+timedelta(days=1)).date()
    return local.date()


def peak_trail_percent(*,steady_confirmed:bool)->Decimal:
    return STEADY_PEAK_TRAIL if steady_confirmed else DEFAULT_PEAK_TRAIL


def is_early_market(now:datetime)->bool:
    local=now.astimezone(CHICAGO)
    clock=local.time().replace(tzinfo=None)
    return clock<PREMARKET_END or clock>=time(19,0)


def quoted_return(entry:Decimal,bid:Decimal)->Decimal:
    if not entry.is_finite() or entry<=0 or not bid.is_finite() or bid<=0:
        raise ValueError("Invalid verified quote / entry")
    return (bid-entry)/entry


def premarket_sell_decision(
    now:datetime,entry:Decimal,bid:Decimal,reason:str,
    *,peak:Decimal|None=None,steady_confirmed:bool=False
)->str:
    """Validate an actual fresh broker bid against software PAPER exits.

    The one-minute monitor may propose a sell using completed traded bars.
    Never treat its close or minute-low alone as an executable stop price.
    Broker-native trailing orders do not work in extended hours. Here a
    verified bid may trigger an eligible DAY limit sell; no fill guaranteed.
    """
    if not is_early_market(now):
        return "NOT_PREMARKET"
    gain=quoted_return(entry,bid)
    if gain<=EMERGENCY_LOSS:
        return "EMERGENCY_DOWNSIDE_EXIT"
    if peak is None or not isinstance(peak,Decimal) or not peak.is_finite() or peak<entry:
        return "PEAK_NOT_VERIFIED"
    if reason=="premarket steady peak trailing stop":
        if steady_confirmed and (bid/peak-1)<=-STEADY_PEAK_TRAIL:
            return "TRAILING_STOP_SOFTWARE"
        return "HOLD_FOR_TREND"
    if reason=="premarket standard peak trailing stop":
        if not steady_confirmed and (bid/peak-1)<=-DEFAULT_PEAK_TRAIL:
            return "TRAILING_STOP_SOFTWARE"
        return "HOLD_FOR_TREND"
    if (gain>=SUBSTANTIAL_PROFIT and not steady_confirmed and
            reason in ("premarket substantial profit reversal",
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
