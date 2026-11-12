"""Research-only causal high-water comparator for Alpaca PAPER entries.

Never substitutes for broker-native protection, existing emergency exit, or
the 13:40 CT flatten. No broker/client methods. Missing fill/bar proof => UNKNOWN.
"""
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation

class UnknownFirstFillEvidence(ValueError):
    pass
def dt(x):
    if not isinstance(x,datetime) or x.tzinfo is None: raise ValueError("aware datetime required")
    return x.astimezone(timezone.utc)
def positive(v):
    try: z=Decimal(str(v))
    except (ValueError,InvalidOperation,TypeError):raise ValueError("invalid price") from None
    if not z.is_finite() or z<=0:raise ValueError("invalid price")
    return z
def complete_bar_peak(entry_price,first_verified_fill_at,bars,asof):
    """Return (peak,status,considered_count). Only whole one-minute bars AFTER first actual fill.

    first_verified_fill_at must come from broker-native FILL execution evidence,
    NOT order submitted_at, acceptance, or final-filled order timestamp when
    earlier partial fills are possible.
    """
    entry=positive(entry_price);now=dt(asof)
    if first_verified_fill_at is None:
        raise UnknownFirstFillEvidence("first actual FILL activity time unavailable")
    first=dt(first_verified_fill_at)
    if first>now: raise ValueError("fill after observation")
    # A candle overlapping the first fill may contain a peak BEFORE shares existed.
    earliest=first.replace(second=0,microsecond=0)
    if first>earliest:earliest+=timedelta(minutes=1)
    completed={}
    for r in bars:
        stamp=dt(r['t'])
        high=positive(r['high'])
        if not(earliest<=stamp and stamp+timedelta(minutes=1)<=now):continue
        if stamp in completed:raise ValueError("duplicate complete one-minute bar")
        completed[stamp]=high
    upper=now.replace(second=0,microsecond=0)
    expected=int((upper-earliest)/timedelta(minutes=1))
    if expected<=0:return entry,'NO_COMPLETE_POSTFILL_BARS',0
    if len(completed)!=expected or any(earliest+timedelta(minutes=i) not in completed for i in range(expected)):
        return None,'MISSING_COMPLETE_POSTFILL_MINUTES',len(completed)
    return max((entry,*completed.values())),'VERIFIED_POSTFILL_FULL_MINUTES',len(completed)
