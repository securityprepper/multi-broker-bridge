"""Research-only, no-HTTP/no-DB post-reservation failure disposition.

Never call this to authorize a POST. It models the safe terminal states for a
future receiving-Alpaca PAPER router release after the *last-moment* check.
A crash/timeout or ambiguous broker contact MUST stay UNKNOWN and cannot
be converted to "no order" merely because no receipt was recorded.
"""
from __future__ import annotations
import re

ALLOWED_VETO = frozenset({
    "ENTRY_CUTOFF_PASSED", "QUOTE_STALE_AT_POST",
    "QUOTE_FUTURE_AT_POST", "HOLIDAY_INVALIDATED",
    "RECEIVING_BROKER_PREFLIGHT_INVALIDATED",
})

def resolution(*, intent_status: str, reservation_lock_owned: bool,
               exclusive_writer_proven: bool, broker_post_started: bool | None,
               veto_code: str | None, client_order_id: str) -> dict:
    """Pure outcome evidence. A caller must atomically persist it under lock.

    A successful return is NOT a database write, broker proof, or permission
    to place any orders. Keep the same-session claim retained even for a
    locally confirmed no-POST veto, avoiding unsafe retry/double submit.
    """
    def unresolved(reason: str):
        return {
            "proposed_status": "RESERVED_UNKNOWN",
            "reason": reason,
            "post_permitted": False,
            "automatic_retry_permitted": False,
            "requires_broker_readback": True,
            "retain_same_broker_claim": True,
            "broker_order_verified": False,
        }

    if intent_status != "RESERVED_UNKNOWN":
        return unresolved("unexpected reservation status")
    if not isinstance(client_order_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{5,47}", client_order_id):
        return unresolved("client id evidence invalid")
    if reservation_lock_owned is not True or exclusive_writer_proven is not True:
        return unresolved("atomic sole-writer proof absent")
    if broker_post_started is not False:
        return unresolved("broker POST could have started")
    if veto_code not in ALLOWED_VETO:
        return unresolved("no valid final-check rejection")
    return {
        "proposed_status": "PRE_SUBMIT_NO_ORDER",
        "reason": veto_code,
        "post_permitted": False,
        "automatic_retry_permitted": False,
        "requires_broker_readback": False,
        "retain_same_broker_claim": True,
        "broker_order_verified": False,
        "evidence_level": "LOCAL_NO_POST_CONTROL_FLOW_ONLY",
    }
