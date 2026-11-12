"""Research-only Alpaca PAPER source provenance checks; NO broker connection.

Important: a broker order acceptance is not a fill, a minute-bar high is not
an executable bid, and an entry reservation timestamp is not a filled entry.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

MINUTE = timedelta(minutes=1)
TRAIL_ARM = Decimal("0.005")
TRAIL_RETRACE = Decimal("0.005")

def _time(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("timestamp requires an offset")
    return t

def _decimal(value: str) -> Decimal:
    x = Decimal(value)
    if not x.is_finite() or x <= 0:
        raise ValueError("positive finite price required")
    return x

def prefill_eligible_minute_starts(reservation_at: str, filled_at: str) -> list[str]:
    """Bar starts >= reservation that precede the actual fill.

    They MAY contain prefill prints, not necessarily anomalous highs.
    Returns only possible exposed minute starts, not evidence of realized
    stop activation or a fully prefill candle.
    """
    start, fill = _time(reservation_at), _time(filled_at)
    if fill < start:
        raise ValueError("fill predates reservation")
    minute = start.replace(second=0, microsecond=0) + MINUTE
    out = []
    while minute < fill:
        out.append(minute.isoformat())
        minute += MINUTE
        if len(out) > 1440:
            raise ValueError("unbounded delayed fill")
    return out

def trade_print_peak_boundary(entry_fill: str, trade_bar_high: str,
                              signal_close: Optional[str] = None,
                              verified_peak_bid: Optional[str] = None) -> dict:
    """Classify price arithmetic, NEVER verify an alternative execution.

    A bar high does not prove that its price was available at the bid for
    the position quantity. The exit sell fill is NOT the signal bar close.
    """
    entry, peak = _decimal(entry_fill), _decimal(trade_bar_high)
    if peak < entry:
        raise ValueError("peak below entry")
    boundary = peak * (Decimal("1") - TRAIL_RETRACE)
    armed = peak >= entry * (Decimal("1") + TRAIL_ARM)
    triggered = None
    if signal_close is not None:
        close = _decimal(signal_close)
        triggered = bool(armed and close <= boundary)
    bid_confirmed = False
    if verified_peak_bid is not None:
        bid_peak = _decimal(verified_peak_bid)
        bid_confirmed = bid_peak >= entry * (Decimal("1") + TRAIL_ARM)
    return {
        "trade_high_armed": armed,
        "trade_high_close_boundary": str(boundary),
        "signal_close_condition": triggered,
        "bid_peak_confirmed": bid_confirmed,
        "source": "SIP_TRADE_BAR_HIGH_NOT_AN_EXECUTABLE_BID",
        "fill_inference_permitted": False,
    }


[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]