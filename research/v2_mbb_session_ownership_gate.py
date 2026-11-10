"""Research-only MBB ownership/session admission model. NEVER submits orders.

Inputs must originate from independent, complete broker readbacks, not from
SQLite tracked rows. The exclusive ownership lease is a separate independent
attestation, NOT something this module can infer from account-level positions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
VALID_SIDES = {"buy": 1, "sell": -1}


def trading_session_key(now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    local = now.astimezone(CHICAGO)
    day = local.date() + (timedelta(days=1) if local.time() >= time(19, 0) else timedelta())
    return day.isoformat()


@dataclass(frozen=True)
class Activity:
    activity_id: str
    order_id: str
    writer: str
    symbol: str
    side: str
    shares: str


@dataclass(frozen=True)
class Evidence:
    symbol: str
    broker_shares: str
    asof: datetime
    positions_complete: bool
    orders_complete: bool
    orders_history_complete: bool
    activities_complete_from_flat_anchor: bool
    writer_registry_complete: bool
    unknown_submissions: bool
    any_open_orders: bool
    # True ONLY if an independently verified, exclusive symbol ownership lease
    # covered the entire interval of the MBB holding, not just the current tick.
    exclusive_mbb_lease_proven: bool
    activities: tuple[Activity, ...] = ()
    # All MBB entry attempts on the normalized session, including UNKNOWN.
    current_session_attempts: int = 0
    tracked_origin_session: str | None = None


@dataclass(frozen=True)
class Decision:
    result: str
    session_key: str
    mbb_shares: str | None = None
    other_shares: str | None = None


def _quantity(q: str) -> Decimal:
    try:
        v = Decimal(q)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid broker quantity") from exc
    if not v.is_finite() or v < 0 or v != v.to_integral_value():
        raise ValueError("only finite whole long shares supported")
    return v


def classify(now: datetime, proof: Evidence, *, purpose: str,
             holiday_unpaused: bool) -> Decision:
    """Return a non-executable classification, never an order instruction.

    purpose is 'entry' or 'flatten'. For ambiguous holdings, BLOCK_AND_ESCALATE
    deliberately preserves the need for an independent mandatory-exit procedure.
    """
    session = trading_session_key(now)
    if purpose not in ("entry", "flatten"):
        raise ValueError("invalid purpose")
    if not holiday_unpaused:
        return Decision("BLOCK_HOLIDAY_GATE", session)
    if proof.asof.tzinfo is None or proof.asof.utcoffset() is None:
        return Decision("BLOCK_UNTRUSTED_SNAPSHOT", session)
    age = (now - proof.asof).total_seconds()
    if age < 0 or age > 60 or not all((
            proof.positions_complete, proof.orders_complete,
            proof.orders_history_complete, proof.activities_complete_from_flat_anchor,
            proof.writer_registry_complete)):
        return Decision("BLOCK_INCOMPLETE_OR_STALE_READBACK", session)
    if proof.unknown_submissions or proof.any_open_orders:
        return Decision("BLOCK_PENDING_OR_UNKNOWN_ORDERS", session)
    if purpose == "entry" and now.astimezone(CHICAGO).time() >= time(13, 15):
        return Decision("BLOCK_1315_ENTRY_CUTOFF", session)
    if proof.current_session_attempts < 0:
        return Decision("BLOCK_INVALID_ATTEMPT_HISTORY", session)

    try:
        broker = _quantity(proof.broker_shares)
        mbb = Decimal(0)
        others = Decimal(0)
        seen: set[str] = set()
        for f in proof.activities:
            if not f.activity_id or not f.order_id or f.activity_id in seen:
                return Decision("BLOCK_UNRECONCILED_ACTIVITY", session)
            seen.add(f.activity_id)
            if f.symbol != proof.symbol or f.side not in VALID_SIDES:
                return Decision("BLOCK_UNRECONCILED_ACTIVITY", session)
            if f.writer not in ("MBB", "OTHER"):
                return Decision("BLOCK_UNRECONCILED_ACTIVITY", session)
            shares = _quantity(f.shares)
            if shares <= 0:
                return Decision("BLOCK_UNRECONCILED_ACTIVITY", session)
            if f.writer == "MBB":
                mbb += VALID_SIDES[f.side] * shares
            else:
                others += VALID_SIDES[f.side] * shares
    except ValueError:
        return Decision("BLOCK_UNRECONCILED_ACTIVITY", session)
    if mbb < 0 or others < 0 or broker != mbb + others:
        return Decision("BLOCK_INVENTORY_DRIFT_OR_SHORT", session,
                        str(mbb), str(others))

    if broker > 0:
        if (purpose == "flatten" and others == 0 and mbb == broker
                and proof.exclusive_mbb_lease_proven):
            return Decision("VERIFIED_MBB_EXIT_OBLIGATION", session,
                            str(mbb), str(others))
        return Decision("BLOCK_AND_ESCALATE_OWNERSHIP", session,
                        str(mbb), str(others))
    if purpose == "flatten":
        return Decision("VERIFIED_FLAT_NO_EXIT_ORDER", session, "0", "0")
    if proof.current_session_attempts:
        return Decision("SAME_SESSION_REENTRY_REQUIRES_BROKER_PROOF", session,
                        "0", "0")
    # Historical 'tracked' state alone does not block a first new-session entry.
    return Decision("NEW_SESSION_FIRST_ENTRY_ELIGIBLE_FOR_NORMAL_GATES",
                    session, "0", "0")
