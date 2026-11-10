"""Offline V2 cross-strategy PAPER intent reservation model. NO BROKER/SQL ACTIONS.

The in-memory lock is a specification/test double, NOT a deployed concurrency
control. Real release requires a Percona unique index, atomic transactions and
independent broker readbacks. Never auto-expire unknown submissions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from threading import RLock
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
FINAL_EMPTY = {"CANCELED_EMPTY", "REJECTED_EMPTY", "EXPIRED_EMPTY"}
PENDING = {"RESERVED", "SUBMISSION_UNKNOWN", "ACKNOWLEDGED", "PARTIAL", "FILLED"}
ALL_STATES = FINAL_EMPTY | PENDING | {"CLOSED_VERIFIED"}


@dataclass(frozen=True)
class Readback:
    asof: datetime
    account_scope: str
    session_key: str
    symbol: str
    calendar_authorized_session_key: str
    calendar_revision_valid: bool
    session_eligible: bool
    broker_history_complete: bool
    fill_uuid_chain_reconciled: bool
    writer_registry_attested: bool
    positions_complete: bool
    open_orders_complete: bool
    broker_flat: bool
    no_open_orders: bool
    no_unknown_submissions: bool


@dataclass
class Intent:
    account_scope: str
    session_key: str
    symbol: str
    slot: int
    writer: str
    client_order_id: str
    state: str = "RESERVED"
    broker_order_id: str | None = None


@dataclass(frozen=True)
class Response:
    status: str
    slot: int | None = None


class OfflineIntentRegistry:
    """Atomic-in-memory proof exercise, NOT distributed broker locking."""

    def __init__(self):
        self._lock = RLock()
        self._rows: dict[tuple[str, str, str, int], Intent] = {}
        self._client_ids: set[str] = set()

    @staticmethod
    def _fresh(now: datetime, r: Readback) -> bool:
        if any(x.tzinfo is None or x.utcoffset() is None for x in (now, r.asof)):
            return False
        age = (now - r.asof).total_seconds()
        return 0 <= age <= 60

    @staticmethod
    def _trusted(r: Readback, *, now: datetime) -> bool:
        return (
            OfflineIntentRegistry._fresh(now, r)
            and bool(r.account_scope and r.symbol and r.session_key)
            and r.calendar_revision_valid and r.session_eligible
            and r.session_key == r.calendar_authorized_session_key
            and r.broker_history_complete and r.fill_uuid_chain_reconciled
            and r.writer_registry_attested and r.positions_complete
            and r.open_orders_complete and r.broker_flat
            and r.no_open_orders and r.no_unknown_submissions
        )

    def reserve(self, r: Readback, *, now: datetime, writer: str,
                client_order_id: str, slot: int = 0,
                prior_profit_sale_verified: bool = False,
                discounted_fresh_ask_verified: bool = False,
                holiday_unpaused: bool = True) -> Response:
        """Fail closed: only owner-approved slots and complete reconciled flat readbacks.

        slot=0 first purchase, slot=1 ONE optional post-profit discounted reentry.
        Historical prior-session rows never block slot=0; same-session rows do.
        """
        if not holiday_unpaused:
            return Response("BLOCK_HOLIDAY")
        if not self._trusted(r, now=now):
            return Response("BLOCK_BROKER_OR_SESSION_PROOF")
        local_time = now.astimezone(CHICAGO).time()
        if time(13, 15) <= local_time < time(19, 0):
            return Response("BLOCK_ENTRY_CUTOFF")
        if writer not in {"MBB", "FDR", "NEWS"} or not client_order_id:
            return Response("BLOCK_INVALID_WRITER_OR_ID")
        if slot not in (0, 1):
            return Response("BLOCK_INVALID_SLOT")
        if slot == 1 and (local_time >= time(10) or
                          not prior_profit_sale_verified or
                          not discounted_fresh_ask_verified):
            return Response("BLOCK_REENTRY_PROOF")
        scope = (r.account_scope, r.session_key, r.symbol)
        with self._lock:
            rows = {key[3]: v for key, v in self._rows.items() if key[:3] == scope}
            if client_order_id in self._client_ids:
                return Response("BLOCK_DUPLICATE_CLIENT_ID")
            if slot in rows:
                return Response("BLOCK_SAME_SLOT_ALREADY_RESERVED")
            if slot == 0 and rows:
                return Response("BLOCK_EXISTING_SESSION_INTENT")
            if slot == 1 and not (0 in rows and rows[0].writer == writer and
                                  rows[0].state == "CLOSED_VERIFIED"):
                return Response("BLOCK_PREDECESSOR_NOT_CLOSED")
            self._rows[(*scope, slot)] = Intent(
                *scope, slot, writer, client_order_id)
            self._client_ids.add(client_order_id)
        return Response("RESEARCH_RESERVATION_ONLY", slot)

    def transition(self, *, account_scope: str, session_key: str, symbol: str,
                   slot: int, writer: str, new_state: str,
                   broker_order_id: str | None = None,
                   complete_broker_readback: bool = False,
                   verified_flat: bool = False) -> Response:
        """Only broker-observed state can end UNKNOWN/PARTIAL/FILLED exposure."""
        with self._lock:
            row = self._rows.get((account_scope, session_key, symbol, slot))
            if row is None or row.writer != writer or new_state not in ALL_STATES:
                return Response("BLOCK_NO_MATCHING_RESERVATION")
            if row.state == new_state and row.broker_order_id == broker_order_id:
                return Response("IDEMPOTENT_NOOP", slot)
            if row.state == "CLOSED_VERIFIED":
                return Response("BLOCK_TERMINAL_REPLAY")
            if broker_order_id and row.broker_order_id and broker_order_id != row.broker_order_id:
                return Response("BLOCK_ORDER_UUID_CONFLICT")
            if new_state in FINAL_EMPTY | {"CLOSED_VERIFIED"}:
                if not (complete_broker_readback and verified_flat):
                    return Response("BLOCK_NEEDS_BROKER_FLAT_PROOF")
            if row.state in {"SUBMISSION_UNKNOWN", "PARTIAL", "FILLED"}:
                if not complete_broker_readback:
                    return Response("BLOCK_UNKNOWN_OR_FILLED_NOT_RECONCILED")
            valid = {
                "RESERVED": {"SUBMISSION_UNKNOWN", "ACKNOWLEDGED"} | FINAL_EMPTY,
                "SUBMISSION_UNKNOWN": {"ACKNOWLEDGED", "PARTIAL", "FILLED"} | FINAL_EMPTY,
                "ACKNOWLEDGED": {"PARTIAL", "FILLED", "SUBMISSION_UNKNOWN"} | FINAL_EMPTY,
                "PARTIAL": {"FILLED", "CLOSED_VERIFIED"},
                "FILLED": {"CLOSED_VERIFIED"},
                "CANCELED_EMPTY": set(), "REJECTED_EMPTY": set(),
                "EXPIRED_EMPTY": set(),
            }
            if new_state not in valid.get(row.state, set()):
                return Response("BLOCK_INVALID_TRANSITION")
            row.state = new_state
            if broker_order_id:
                row.broker_order_id = broker_order_id
            return Response("RESEARCH_TRANSITION_ONLY", slot)

    def snapshot(self) -> tuple[Intent, ...]:
        with self._lock:
            return tuple(Intent(**vars(x)) for x in self._rows.values())
