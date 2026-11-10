"""Research-only recommendation/PAPER reconciliation. Zero broker/network/database actions.

Each recommendation is durable even if its PAPER attempt is rejected. A future
commissioned router must be separately authorized and return verifiable receipts.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import re

ALLOWED_TASKS = {f"Task - Trading Opportunities {word}" for word in ("One", "Two", "Three", "Four")}
VALID_ACTIONS = {"BUY NOW", "BUY AT PULLBACK"}
VALID_TERMINAL = {"FILLED", "CANCELED", "EXPIRED", "REJECTED"}

class UnverifiedExecution(ValueError):
    pass

def number(value, name):
    if isinstance(value, (float, bool)):
        raise UnverifiedExecution(f"{name}: floats/booleans forbidden")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise UnverifiedExecution(f"{name}: invalid decimal")
    if not d.is_finite() or d <= 0:
        raise UnverifiedExecution(f"{name}: must be positive")
    return d

def instant(value, field):
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise UnverifiedExecution(f"{field}: invalid timestamp")
    if d.tzinfo is None:
        raise UnverifiedExecution(f"{field}: timezone required")
    return d.astimezone(timezone.utc)

def validate_recommendation(r):
    required = ("recommendation_id","issued_at_utc","quote_at_utc","symbol",
                "action","quote_last","quote_bid","quote_ask","limit",
                "profit_target","stop_loss","rationale","source_task","source_run_id")
    for name in required:
        if name not in r or r[name] is None or r[name] == "":
            raise UnverifiedExecution(f"missing {name}")
    if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,11}",r["symbol"]):
        raise UnverifiedExecution("invalid symbol")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}",r["recommendation_id"]):
        raise UnverifiedExecution("invalid recommendation id")
    if r["action"] not in VALID_ACTIONS or r["source_task"] not in ALLOWED_TASKS:
        raise UnverifiedExecution("invalid action/source")
    issued, observed = instant(r["issued_at_utc"],"issued"),instant(r["quote_at_utc"],"quote")
    if observed > issued or (issued-observed).total_seconds() > 300:
        raise UnverifiedExecution("quote stale or in future at recommendation")
    last,bid,ask,limit,target,stop=[number(r[k],k) for k in
        ("quote_last","quote_bid","quote_ask","limit","profit_target","stop_loss")]
    if not bid <= last <= ask or not stop < limit < target:
        raise UnverifiedExecution("invalid bid/ask or protection ordering")
    if r["action"]=="BUY NOW" and ask > limit:
        raise UnverifiedExecution("BUY NOW ask exceeds limit")
    if not str(r["rationale"]).strip() or not str(r["source_run_id"]).strip():
        raise UnverifiedExecution("missing decision provenance")
    return r

def intent_record(r, *, commissioned=False):
    validate_recommendation(r)
    key = sha256((r["recommendation_id"]+"|ALPACA_PAPER|BUY").encode()).hexdigest()[:28]
    # Never create a broker order here: commissioned flag only distinguishes the
    # router-ready state, it does not itself constitute a verified broker receipt.
    return {"recommendation_id":r["recommendation_id"],"client_order_id":"TO-P-"+key,
            "order_status":"ROUTER_READY_NOT_SUBMITTED" if commissioned else "NOT_PLACED_UNCOMMISSIONED",
            "broker_order_id":None,"recorded_limit":str(r["limit"]),
            "recorded_profit":str(r["profit_target"]),"recorded_stop":str(r["stop_loss"])}

def audit_closed(r, intent, fills):
    """Strict FIFO for a single recommendation. No attribution from aggregate position."""
    validate_recommendation(r)
    if intent.get("recommendation_id")!=r["recommendation_id"]:
        raise UnverifiedExecution("intent mismatch")
    if not intent.get("broker_order_id"):
        return {"status":"NOT_CLOSED_OR_NO_VERIFIED_ORDER"}
    if not fills:
        return {"status":"NOT_CLOSED_OR_NO_VERIFIED_FILLS"}
    ids=set(); bought=Decimal(0); sold=Decimal(0); basis=Decimal(0); proceeds=Decimal(0)
    fees=Decimal(0); first_buy=None; last_sell=None
    for f in sorted(fills,key=lambda z:instant(z["time_utc"],"fill")):
        if f.get("recommendation_id")!=r["recommendation_id"] or f.get("broker_order_id") is None:
            raise UnverifiedExecution("unattributed fill")
        if not f.get("activity_id") or f["activity_id"] in ids:
            raise UnverifiedExecution("missing/duplicate activity UUID")
        ids.add(f["activity_id"])
        q=number(f["qty"],"qty"); p=number(f["price"],"price")
        fee=Decimal(str(f.get("commission","0")))
        if fee < 0 or not fee.is_finite():
            raise UnverifiedExecution("invalid commission")
        fees+=fee
        t=instant(f["time_utc"],"fill")
        if f["side"]=="BUY":
            bought+=q; basis+=q*p
            first_buy=t if first_buy is None else min(first_buy,t)
        elif f["side"]=="SELL":
            sold+=q; proceeds+=q*p;last_sell=t
            if sold > bought:
                raise UnverifiedExecution("sell exceeds attributable purchased quantity")
        else:
            raise UnverifiedExecution("unsupported side")
    if not bought or sold < bought:
        return {"status":"OPEN_OR_PARTIAL","bought":str(bought),"sold":str(sold)}
    return {"status":"CLOSED","recommendation_id":r["recommendation_id"],
            "entry_at_utc":first_buy.isoformat(),"exit_at_utc":last_sell.isoformat(),
            "quantity":str(bought),"actual_average_buy":str(basis/bought),
            "actual_average_sell":str(proceeds/sold),
            "gross_realized_pnl":str(proceeds-basis),
            "after_fee_realized_pnl":str(proceeds-basis-fees),
            "fees":str(fees),"audit_watermark":intent["client_order_id"]+"|"+last_sell.isoformat()}
