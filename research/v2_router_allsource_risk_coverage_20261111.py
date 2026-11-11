"""Read-only, all-source receiving-Alpaca PAPER risk gate prototype.

Source research only. Does not access any broker, database, secrets, or orders.
"""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from zoneinfo import ZoneInfo
CT = ZoneInfo("America/Chicago")

def decimal(v):
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValueError("invalid numeric risk evidence") from e
    if not d.is_finite():
        raise ValueError("non-finite risk evidence")
    return d

def evaluate(account, positions, orders, monitor, now, expected_id, cost):
    def no(reason):
        return {"ready": False, "reason": reason, "broker_calls": 0,
                "broker_orders": 0, "order_authorized": False}
    if now.tzinfo is None or not isinstance(account,dict):
        return no("UNTRUSTED_RECEIVING_ACCOUNT_OR_TIME")
    if (account.get("id")!=expected_id or account.get("status")!="ACTIVE"
        or account.get("account_blocked") is not False
        or account.get("trading_blocked") is not False):
        return no("RECEIVING_PAPER_ACCOUNT_NOT_VERIFIED")
    if not isinstance(positions,list) or not isinstance(orders,list) or len(orders)>=500:
        return no("RECEIVING_BROKER_INVENTORY_INCOMPLETE")
    if not isinstance(monitor,dict) or monitor.get("broker_verified") is not True or monitor.get("paper_only") is not True:
        return no("RECEIVING_BROKER_RISK_NOT_VERIFIED")
    if monitor.get("paper_account_fingerprint")!=sha256(expected_id.encode()).hexdigest()[:24]:
        return no("RECEIVING_BROKER_RISK_WRONG_ACCOUNT")
    if monitor.get("session_date")!=now.astimezone(CT).date().isoformat():
        return no("RECEIVING_BROKER_RISK_WRONG_SESSION")
    try:
        observed=datetime.fromisoformat(monitor["asof_utc"].replace("Z","+00:00"))
        if observed.tzinfo is None or not timedelta(0)<=now-observed<=timedelta(seconds=95):
            return no("RECEIVING_BROKER_RISK_STALE")
        if (monitor.get("loss_lockout") is not False or
            monitor.get("daily_loss_limit")!="400" or
            monitor.get("combined_exposure_limit")!="11800"):
            return no("RECEIVING_BROKER_RISK_LOCK_OR_CONFIGURATION")
        if decimal(monitor.get("daily_equity_change"))<Decimal("-400"):
            return no("RECEIVING_BROKER_DAILY_LOSS_LIMIT")
        new=decimal(cost)
        if not Decimal(0)<new<=Decimal("2000") or new>decimal(account.get("cash")):
            return no("RECEIVING_BROKER_TICKET_CASH_LIMIT")
        held=sum((abs(decimal(p["market_value"])) for p in positions),Decimal(0))
        pending=Decimal(0)
        for o in orders:
            if o["side"]!="buy": continue
            remain=decimal(o["qty"])-decimal(o.get("filled_qty",0))
            if remain<0: return no("RECEIVING_BROKER_PENDING_ORDER_INVALID")
            if remain>0: pending+=remain*decimal(o["limit_price"])
        if held+pending+new>Decimal("11800"):
            return no("RECEIVING_BROKER_COMBINED_EXPOSURE")
    except (KeyError, ValueError, TypeError, AttributeError):
        return no("RECEIVING_BROKER_RISK_DATA_INVALID")
    return {"ready":True,"reason":"ALL_SOURCE_PAPER_SHADOW_RISK_OK",
            "projected_gross":str(held+pending+new), "broker_calls":0,
            "broker_orders":0,"order_authorized":False}
