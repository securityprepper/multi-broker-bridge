"""Pure V2 research join of Alpaca PAPER order UUIDs to fill-activity UUIDs.

No broker connection, SQL, credentials, order writing, or V1 integration.
Evidence must be externally read/attested, complete from a proven flat anchor.
This module does NOT prove a cross-strategy ownership lease and cannot
authorize a buy or sell by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Sequence

TERMINAL = frozenset({"filled", "canceled", "expired", "rejected"})
SIGN = {"buy": 1, "sell": -1}

@dataclass(frozen=True)
class BrokerOrder:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    filled_quantity: str
    status: str
    created_at: datetime
    # Independently confirmed from a complete writer registry AND broker ID.
    writer: str
    writer_attested: bool

@dataclass(frozen=True)
class FillActivity:
    activity_uuid: str
    order_id: str
    symbol: str
    side: str
    quantity: str
    transacted_at: datetime

@dataclass(frozen=True)
class Proof:
    symbol: str
    asof: datetime
    verified_flat_anchor: datetime
    broker_position_quantity: str
    broker_orders_complete: bool
    broker_activities_complete: bool
    broker_positions_complete: bool
    writer_registry_complete: bool
    orders: tuple[BrokerOrder, ...]
    activities: tuple[FillActivity, ...]

@dataclass(frozen=True)
class Result:
    status: str
    mbb_net: str | None = None
    other_net: str | None = None
    # Non-executable rows for the independent higher-level V2 policy gate.
    # (activity_uuid, order_id, writer, symbol, side, quantity)
    normalized_activities: tuple[tuple[str, str, str, str, str, str], ...] = ()

def whole(value: str, *, positive: bool = False) -> Decimal:
    try:
        n = Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid quantity") from exc
    if not n.is_finite() or n != n.to_integral_value() or n < 0:
        raise ValueError("non-whole or negative quantity")
    if positive and n <= 0:
        raise ValueError("non-positive fill")
    return n

def aware(t: datetime) -> bool:
    return isinstance(t, datetime) and t.tzinfo is not None and t.utcoffset() is not None

def verify(proof: Proof) -> Result:
    """Fail-closed on missing/future activity, partial fill or inventory drift.

    Successful result verifies only arithmetic and recorded writer attribution.
    It does NOT independently create a lease, prove exclusive ownership, or
    permit broker actions. External policy checks remain mandatory.
    """
    if not all((proof.broker_orders_complete, proof.broker_activities_complete,
                proof.broker_positions_complete, proof.writer_registry_complete)):
        return Result("BLOCK_INCOMPLETE_HISTORY")
    if not aware(proof.asof) or not aware(proof.verified_flat_anchor):
        return Result("BLOCK_INVALID_TIMESTAMPS")
    if proof.verified_flat_anchor > proof.asof:
        return Result("BLOCK_INVALID_TIMESTAMPS")
    try:
        position = whole(proof.broker_position_quantity)
    except ValueError:
        return Result("BLOCK_INVALID_BROKER_POSITION")

    orders: dict[str, BrokerOrder] = {}
    for row in proof.orders:
        if (not row.order_id or row.order_id in orders or
                not row.client_order_id or row.symbol != proof.symbol or
                row.side not in SIGN or row.status not in TERMINAL or
                not row.writer_attested or row.writer not in ("MBB", "OTHER") or
                not aware(row.created_at) or
                not proof.verified_flat_anchor <= row.created_at <= proof.asof):
            return Result("BLOCK_ORDER_PROVENANCE")
        # An MBB-looking client ID by itself is not attestation. The registry
        # also must agree: FDR, unknown, or user-tagged shares are OTHER.
        if (row.writer == "MBB") != row.client_order_id.startswith("MBB-"):
            return Result("BLOCK_ORDER_PROVENANCE")
        try:
            quantity = whole(row.quantity, positive=True)
            filled = whole(row.filled_quantity)
        except ValueError:
            return Result("BLOCK_ORDER_PROVENANCE")
        if filled > quantity or (row.status == "filled" and filled != quantity):
            return Result("BLOCK_ORDER_PROVENANCE")
        orders[row.order_id] = row

    seen: set[str] = set()
    filled_by_order = {k: Decimal(0) for k in orders}
    mbb = Decimal(0)
    other = Decimal(0)
    events = []  # chronological writer balances must never go below zero
    normalized = []
    for activity in proof.activities:
        row = orders.get(activity.order_id)
        if (not activity.activity_uuid or activity.activity_uuid in seen or
                row is None or activity.symbol != proof.symbol or
                activity.symbol != row.symbol or activity.side != row.side or
                not aware(activity.transacted_at) or
                not row.created_at <= activity.transacted_at <= proof.asof):
            return Result("BLOCK_ACTIVITY_UUID_CHAIN")
        seen.add(activity.activity_uuid)
        try:
            qty = whole(activity.quantity, positive=True)
        except ValueError:
            return Result("BLOCK_ACTIVITY_UUID_CHAIN")
        filled_by_order[row.order_id] += qty
        signed = SIGN[activity.side] * qty
        events.append((activity.transacted_at, row.writer, signed))
        if row.writer == "MBB":
            mbb += signed
        else:
            other += signed
        normalized.append((activity.activity_uuid, activity.order_id,
                           row.writer, proof.symbol, activity.side, str(qty)))
    for oid, order in orders.items():
        if filled_by_order[oid] != whole(order.filled_quantity):
            return Result("BLOCK_PARTIAL_OR_MISSING_FILLS")
    # A final net-zero balance is not enough: one writer may have sold shares
    # belonging to another writer *before* later replenishing that symbol.
    # The flat anchor means both writer balances begin at zero. Unordered
    # opposite-side fills at an identical timestamp are ambiguous.
    running = {"MBB": Decimal(0), "OTHER": Decimal(0)}
    signs_at_time = {}
    for when, writer, signed in sorted(events, key=lambda e: e[0]):
        direction = 1 if signed > 0 else -1
        if when in signs_at_time and signs_at_time[when] != direction:
            return Result("BLOCK_AMBIGUOUS_FILL_SEQUENCE")
        signs_at_time[when] = direction
        running[writer] += signed
        if running[writer] < 0:
            return Result("BLOCK_WRITER_OVERSELL_SEQUENCE")
    if mbb < 0 or other < 0 or mbb + other != position:
        return Result("BLOCK_WRITER_NET_OR_POSITION_DRIFT", str(mbb), str(other))
    return Result("FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY",
                  str(mbb), str(other), tuple(normalized))