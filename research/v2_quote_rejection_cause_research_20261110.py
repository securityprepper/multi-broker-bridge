"""Offline-only V2 quote rejection attribution. No credentials, network, or orders.

Mirrors the acceptance bounds of active auto_paper as inspected 2026-11-10,
but separates reasons that production currently collapses into NO_FRESH_BID_ASK.
NOT integrated into V1. All timestamps must be timezone-aware.
"""
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

MAX_AGE = timedelta(seconds=100)
MAX_SPREAD = Decimal("0.01")


def classify_quote(quote, now):
    """Return (reason, age_seconds_or_none) for a single raw quote."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("as-of timestamp must be timezone aware")
    if quote is None:
        return "ABSENT_QUOTE", None
    if not isinstance(quote, dict):
        return "MALFORMED_QUOTE", None
    try:
        t = datetime.fromisoformat(str(quote["t"]).replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError):
        return "INVALID_QUOTE_TIMESTAMP", None
    if t.tzinfo is None or t.utcoffset() is None:
        return "INVALID_QUOTE_TIMESTAMP", None
    age = (now - t).total_seconds()
    if age < 0:
        return "FUTURE_QUOTE", age
    if age > MAX_AGE.total_seconds():
        return "STALE_QUOTE", age
    try:
        bid = Decimal(str(quote["bp"]))
        ask = Decimal(str(quote["ap"]))
    except (KeyError, InvalidOperation, ValueError, TypeError):
        return "INVALID_PRICE", age
    if not bid.is_finite() or not ask.is_finite():
        return "INVALID_PRICE", age
    if bid <= 0 or ask <= 0:
        return "NONPOSITIVE_PRICE", age
    if bid > ask:
        return "CROSSED_QUOTE", age
    if (ask - bid) / ask > MAX_SPREAD:
        return "WIDE_SPREAD", age
    return "ACCEPT", age


def attribute_batch(symbols, payload, now):
    """Audit one already-received GET result, never fetch data.

    Reports only symbol/reason/age. No broker identifiers, balances or secrets.
    A malformed quotes envelope fails closed, never silently becomes success.
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("quotes"), dict):
        raise ValueError("invalid quotes response envelope")
    if not isinstance(symbols, (tuple, list)) or not all(
        isinstance(s, str) and s and s.isascii() and s.isalnum() for s in symbols
    ):
        raise ValueError("invalid symbol input")
    if len(set(symbols)) != len(symbols):
        raise ValueError("duplicate symbols")
    rows = []
    for symbol in symbols:
        reason, age = classify_quote(payload["quotes"].get(symbol), now)
        rows.append({"symbol": symbol, "reason": reason,
                     "age_seconds": None if age is None else round(age, 3)})
    return {"count": len(rows), "reason_counts": dict(Counter(x["reason"] for x in rows)),
            "symbol_reasons": rows, "no_orders": True, "research_only": True}
