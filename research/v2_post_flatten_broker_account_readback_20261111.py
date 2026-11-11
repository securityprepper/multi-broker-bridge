"""Pure research-only post-flatten Alpaca PAPER account-flat verification.

A filled forced SELL alone does not prove that the receiving broker now has
zero shares and no outstanding same-symbol orders. This has NO network access,
credentials, order method, timer, or permission to trade. Status is a bounded
readback observation, not proof that the position stays flat indefinitely.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256

MAX_RECEIPT_AGE = timedelta(seconds=20)


def _dt(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware receipt clock required")
    return value.astimezone(timezone.utc)


def _num(value):
    if isinstance(value, (float, bool)) or value is None:
        raise ValueError("broker quantity must be decimal text")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid broker quantity") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("bad broker quantity")
    return result


def _flat_id(recommendation_id):
    if not isinstance(recommendation_id, str) or not recommendation_id:
        raise ValueError("recommendation ID required")
    return "TO-F-" + sha256((recommendation_id + "|PAPER|FLATTEN|v1").encode()).hexdigest()[:40]


def verify_post_flatten(*, recommendation_id, symbol, expected_account_id,
                        parent_sell_order, account, positions, open_orders,
                        sell_read_at, positions_read_at, orders_read_at, now,
                        complete_positions, complete_orders,
                        exclusive_paper_account_lock_held):
    """Require independent post-fill same-account positions AND working-order GET.

    No additional sell is ever authorized on failure. An account could acquire
    a new position after the bounded readback; no continuous coverage is claimed.
    """
    def result(status):
        return {"status": status, "paper_only": True, "research_only": True,
                "order_authorized": False, "broker_calls": 0, "orders_submitted": 0}
    try:
        if not (isinstance(expected_account_id, str) and expected_account_id
                and isinstance(symbol, str) and symbol
                and isinstance(account, dict) and account.get("id") == expected_account_id
                and isinstance(parent_sell_order, dict)):
            return result("UNKNOWN_WRONG_ACCOUNT_OR_SOURCE")
        if (not complete_positions or not complete_orders
                or exclusive_paper_account_lock_held is not True
                or not isinstance(positions, list) or not isinstance(open_orders, list)
                or len(open_orders) >= 500):
            return result("UNKNOWN_INCOMPLETE_OR_UNLOCKED_RECEIVING_INVENTORY")
        now = _dt(now)
        received = [_dt(sell_read_at), _dt(positions_read_at), _dt(orders_read_at)]
        if (not all(t <= now and timedelta(0) <= now-t <= MAX_RECEIPT_AGE for t in received)
                or received[1] < received[0] or received[2] < received[0]):
            return result("UNKNOWN_STALE_OR_PRESELL_INVENTORY")
        if (parent_sell_order.get("client_order_id") != _flat_id(recommendation_id)
                or parent_sell_order.get("symbol") != symbol
                or parent_sell_order.get("side") != "sell"
                or not parent_sell_order.get("id")
                or parent_sell_order.get("status") != "filled"):
            return result("UNKNOWN_UNVERIFIED_FLATTEN_ORDER")
        total = _num(parent_sell_order.get("qty"))
        filled = _num(parent_sell_order.get("filled_qty"))
        if total <= 0 or filled != total:
            return result("UNKNOWN_PARTIAL_OR_INVALID_FLATTEN_FILL")
        for p in positions:
            if not isinstance(p, dict) or not p.get("symbol") or p.get("qty") is None:
                return result("UNKNOWN_MALFORMED_POSITION_INVENTORY")
            if p["symbol"] == symbol:
                return result("FLATTEN_ORDER_FILLED_BUT_POSITION_STILL_REPORTED")
        for o in open_orders:
            if not isinstance(o, dict) or not o.get("symbol") or not o.get("id"):
                return result("UNKNOWN_MALFORMED_OPEN_ORDER_INVENTORY")
            if o["symbol"] == symbol:
                return result("FLATTEN_ORDER_FILLED_BUT_WORKING_ORDER_REMAINS")
        return result("BOUNDED_RECEIVING_PAPER_ACCOUNT_FLAT_VERIFIED")
    except (KeyError, ValueError, TypeError, OverflowError):
        return result("UNKNOWN_INVALID_BROKER_READBACK")
