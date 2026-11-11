"""Research-only receiving-Alpaca PAPER shared-budget admission proof.

No connections, credentials, orders or active broker integration. This code
MUST be executed under a durable per-PAPER-account/session database lock when
used by a future commissioned router. In-memory simulation is not a lock.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from research.v2_router_allsource_risk_coverage_20261111 import evaluate, decimal

ACTIVE = {"RESERVED_UNKNOWN", "POST_IN_FLIGHT", "SUBMISSION_UNKNOWN", "BROKER_ACCEPTED"}
TERMINAL = {"PROVEN_NO_POST", "CLOSED_VERIFIED"}

def evaluate_with_reservations(*, account, positions, orders, monitor, inventory,
                               reservations, proposed, now, expected_id):
    """Return strict shadow decision, accounting for simultaneous source intents.

    All decisions remain `order_authorized=False`, including eligible ones.
    Requires complete fresh receiving-broker readbacks and durable reservation
    list read inside an exclusive account-level transaction by the caller.
    """
    def deny(reason):
        return {"ready":False,"reason":reason,"order_authorized":False,
                "broker_calls":0,"broker_orders":0}
    try:
        if not isinstance(proposed,dict) or not isinstance(reservations,list):
            return deny("UNTRUSTED_RESERVATIONS")
        if not proposed.get("source_task") or not proposed.get("recommendation_id"):
            return deny("UNTRUSTED_PROPOSAL")
        if not isinstance(inventory,dict) or inventory.get("account_id")!=expected_id:
            return deny("INVENTORY_WRONG_RECEIVING_ACCOUNT")
        if inventory.get("positions_complete") is not True or inventory.get("orders_complete") is not True:
            return deny("INVENTORY_COVERAGE_INCOMPLETE")
        observed=datetime.fromisoformat(inventory["received_at_utc"].replace("Z","+00:00"))
        if now.tzinfo is None or observed.tzinfo is None or not timedelta(0)<=now-observed<=timedelta(seconds=20):
            return deny("INVENTORY_STALE")
        if inventory.get("reservations_read_with_exclusive_account_lock") is not True:
            return deny("NO_ACCOUNT_WIDE_ATOMIC_LOCK")
        fp=sha256(expected_id.encode()).hexdigest()[:24]
        if inventory.get("account_fingerprint")!=fp:
            return deny("INVENTORY_FINGERPRINT_MISMATCH")
        price=decimal(proposed["ticket_notional"])
        if price<=0: return deny("BAD_TICKET_COST")
        base=evaluate(account,positions,orders,monitor,now,expected_id,price)
        if not base["ready"]:
            return deny(base["reason"])
        if decimal(monitor["daily_equity_change"])<=Decimal("-400"):
            return deny("DAILY_PAPER_LOSS_LIMIT_REACHED")
        session=now.astimezone(__import__("zoneinfo").ZoneInfo("America/Chicago")).date().isoformat()
        if proposed.get("session_date")!=session:
            return deny("PROPOSAL_WRONG_SESSION")
        observed_order_ids={str(o.get("id")) for o in orders if isinstance(o,dict) and o.get("id")}
        additional=Decimal("0")
        seen=set()
        for r in reservations:
            if not isinstance(r,dict): return deny("RESERVATION_MALFORMED")
            if r.get("account_fingerprint")!=fp or r.get("session_date")!=session:
                continue
            ident=r.get("recommendation_id")
            if not ident or ident in seen: return deny("RESERVATION_DUPLICATE_OR_UNKNOWN")
            seen.add(ident)
            if ident==proposed["recommendation_id"]:
                return deny("ALREADY_RESERVED_SAME_RECOMMENDATION")
            state=r.get("status")
            if state in ACTIVE:
                if state=="BROKER_ACCEPTED" and (r.get("broker_order_id")
                        and str(r["broker_order_id"]) in observed_order_ids
                        and r.get("order_id_broker_verified") is True):
                    # Remaining size already in the fresh broker order snapshot.
                    continue
                commitment=decimal(r["committed_notional"])
                if commitment<=0:
                    return deny("INVALID_RESERVATION_AMOUNT")
                additional+=commitment
            elif state=="PROVEN_NO_POST":
                if r.get("post_started") is not False or r.get("exclusive_no_post_proof") is not True:
                    return deny("UNPROVEN_RESERVATION_RELEASE")
            elif state=="CLOSED_VERIFIED":
                if (r.get("broker_terminal_verified") is not True or
                    r.get("receiving_inventory_reconciled") is not True):
                    return deny("UNPROVEN_TERMINAL_RELEASE")
            else:
                return deny("UNKNOWN_RESERVATION_STATE")
        if additional<0: return deny("INVALID_RESERVATION_AMOUNT")
        before=decimal(base["projected_gross"])-price
        after=before+additional+price
        if after>Decimal("11800"):
            return deny("ACCOUNT_WIDE_RISK_AND_RESERVED_EXPOSURE")
        return {"ready":True,"reason":"ACCOUNT_BUDGET_SHADOW_READY",
                "projected_with_reservations":str(after),
                "shadow_reservations":str(additional),
                "order_authorized":False,"broker_calls":0,"broker_orders":0}
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError):
        return deny("UNTRUSTED_RISK_OR_RESERVATION_DATA")
