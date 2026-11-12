"""Offline-only exit attribution: never infer a broker fill from sell acceptance."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

def _date(value):
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None

def _quantity(value):
    try:
        q = Decimal(str(value))
        return q if q.is_finite() and q > 0 else None
    except (TypeError, InvalidOperation):
        return None

def attribute_exit(decision, order, activities):
    """Require independently retrieved same-account order UUID and all unique fills."""
    def unknown(reason):
        return {"status": "UNKNOWN", "detail": reason}
    if not isinstance(decision, dict) or not isinstance(order, dict):
        return unknown("MISSING_DECISION_OR_ORDER")
    oid, account = order.get("id"), order.get("account_id")
    if not oid or not account or decision.get("account_id") != account:
        return unknown("ACCOUNT_NOT_VERIFIED")
    if decision.get("broker_order_id") != oid:
        return unknown("ORDER_UUID_NOT_VERIFIED")
    if order.get("side") != "sell" or decision.get("symbol") != order.get("symbol"):
        return unknown("SYMBOL_OR_SIDE_MISMATCH")
    if order.get("status") != "filled":
        return unknown("SELL_NOT_FULLY_FILLED")
    qty, requested = _quantity(order.get("filled_qty")), _quantity(order.get("qty"))
    if qty is None or requested is None or qty != requested:
        return unknown("PARTIAL_OR_INVALID_ORDER_QUANTITY")
    sent, completed = _date(decision.get("decision_at")), _date(order.get("filled_at"))
    if sent is None or completed is None or completed < sent:
        return unknown("ORDER_TIMING_NOT_VERIFIED")
    if not isinstance(activities, list) or not activities:
        return unknown("FILL_ACTIVITIES_MISSING")
    seen = set()
    total = Decimal(0)
    for f in activities:
        if not isinstance(f, dict):
            return unknown("MALFORMED_ACTIVITY")
        if not f.get("id") or f["id"] in seen:
            return unknown("DUPLICATE_OR_MISSING_FILL_ID")
        seen.add(f["id"])
        if (f.get("order_id") != oid or f.get("account_id") != account
                or f.get("symbol") != order.get("symbol") or f.get("side") != "sell"):
            return unknown("FILL_ORIGIN_MISMATCH")
        ft, fq = _date(f.get("transaction_time")), _quantity(f.get("qty"))
        if ft is None or fq is None or ft < sent:
            return unknown("INVALID_FILL_TIME_OR_QUANTITY")
        total += fq
    if total != qty:
        return unknown("FILL_QUANTITIES_NOT_RECONCILED")
    reason = decision.get("exit_signal_reason")
    if not isinstance(reason, str) or not reason.strip():
        return unknown("REASON_NOT_RECORDED")
    return {"status": "VERIFIED_RECORDED_REASON", "reason": reason.strip(),
            "fill_count": len(activities), "filled_qty": str(qty),
            "strategy_version": decision.get("strategy_version") or "UNKNOWN"}
