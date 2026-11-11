"""OFFLINE-only receiving-broker quote freshness proof for the inactive
recommendation-to-Alpaca-PAPER router.

The router's passed-in preflight-start `now` predates its account/positions/
open-order/quote API sequence. Fresh timestamps returned by the later
quotes/latest GET can exceed `now` and be falsely rejected as future.

Do NOT import this into a live executor without a separately reviewed release.
This module contains no URLs, credentials, broker calls or order methods.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation

RECEIVING_BROKER_QUOTE_MAX_AGE = timedelta(seconds=45)
RECEIVING_BROKER_MAX_SPREAD = Decimal("0.01")


class InvalidQuote(ValueError):
    """Evidence was not a currently usable receiving-broker quote."""


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidQuote("clock timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def validate_post_get_quote(quote: dict, *, scan_started_at: datetime,
                            received_at: datetime,
                            max_age: timedelta = RECEIVING_BROKER_QUOTE_MAX_AGE,
                            max_spread: Decimal = RECEIVING_BROKER_MAX_SPREAD) -> dict:
    """Pure, fail-closed as-received SIP NBBO validation, NOT order authorization.

    The receipt clock MUST be captured immediately after the GET returns.
    This is distinct from the strategy scan-start, the provider publication
    timestamp, and any hypothetical future order submission timestamp.
    """
    start, receipt = _utc(scan_started_at), _utc(received_at)
    if receipt < start:
        raise InvalidQuote("receipt predates scan start")
    if not timedelta(0) < max_age <= RECEIVING_BROKER_QUOTE_MAX_AGE:
        raise InvalidQuote("unsupported quote age bound")
    if not Decimal("0") <= max_spread <= Decimal("0.01"):
        raise InvalidQuote("spread limit must not weaken receiving broker policy")
    if not isinstance(quote, dict):
        raise InvalidQuote("quote payload missing")
    try:
        text = quote["t"]
        if not isinstance(text, str):
            raise ValueError("timestamp not text")
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        seen = _utc(stamp)
        bid, ask = Decimal(str(quote["bp"])), Decimal(str(quote["ap"]))
    except (KeyError, ValueError, InvalidOperation, TypeError) as exc:
        raise InvalidQuote("malformed quote") from exc
    age = receipt - seen
    if not timedelta(0) <= age <= max_age:
        raise InvalidQuote("quote future or stale at actual GET receipt")
    if not bid.is_finite() or not ask.is_finite() or bid <= 0 or ask <= 0 or bid > ask:
        raise InvalidQuote("invalid or crossed quote")
    if (ask - bid) / ask > max_spread:
        raise InvalidQuote("spread exceeds one-percent policy")
    return {
        "quote_at_utc": seen.isoformat(),
        "scan_started_at_utc": start.isoformat(),
        "quote_received_at_utc": receipt.isoformat(),
        "age_milliseconds": int(age.total_seconds() * 1000),
        "bid": str(bid),
        "ask": str(ask),
        "broker_quote_usable_only": True,
        "order_authorized": False,
    }


def old_rule_would_reject(quote_at: datetime, scan_started_at: datetime,
                          max_age: timedelta = RECEIVING_BROKER_QUOTE_MAX_AGE) -> bool:
    """Diagnostic comparison ONLY; must never supply an entry authorization."""
    delta = _utc(scan_started_at) - _utc(quote_at)
    return not timedelta(0) <= delta <= max_age


# A separate owner-cutoff race exists in the still-DISABLED router:
# process_once checks the entry window once, before database work and multiple
# GETs. It does not re-evaluate immediately before POST /v2/orders. The guard
# below proves how to fail closed if crossing the owner 13:15 Chicago cutoff.
# It is not a substitute for same-broker position/order/cash/holiday checks.
CHICAGO = ZoneInfo("America/Chicago")
NEW_YORK = ZoneInfo("America/New_York")
OWNER_ENTRY_CUTOFF = time(13, 15)


class EntryWindowClosed(ValueError):
    """An order MUST NOT be submitted under stale earlier admission."""


def validate_immediately_before_post(*, initial_scan_at: datetime,
                                     broker_post_at: datetime,
                                     quote_at: datetime,
                                     max_quote_age: timedelta = RECEIVING_BROKER_QUOTE_MAX_AGE) -> dict:
    """Offline release-gate prototype, never submits an order.

    Call at the last possible moment before the first broker POST, AFTER the
    database reservation and its potentially slow roundtrips. A successful
    previous preflight does not authorize POST once the cutoff has passed.
    """
    began, post, qtime = (_utc(t) for t in (initial_scan_at, broker_post_at, quote_at))
    if post < began:
        raise EntryWindowClosed("submission clock predates original scan")
    ct, ny = post.astimezone(CHICAGO), post.astimezone(NEW_YORK)
    if not (ct.weekday() < 5 and time(8, 30) <= ct.time() < OWNER_ENTRY_CUTOFF
            and time(9, 30) <= ny.time() < time(16, 0)):
        raise EntryWindowClosed("receiving-broker entry window closed before POST")
    if not timedelta(0) < max_quote_age <= RECEIVING_BROKER_QUOTE_MAX_AGE:
        raise EntryWindowClosed("quote age bound exceeds receiving-broker policy")
    age = post - qtime
    if not timedelta(0) <= age <= max_quote_age:
        raise EntryWindowClosed("quote no longer fresh at intended broker POST")
    return {"entry_window_open_at_last_check": True,
            "asof_utc": post.isoformat(),
            "broker_post_performed": False, "order_authorized": False}
