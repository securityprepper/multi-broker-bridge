"""Durable, separate PAPER recommendation intake-to-order-to-fill metrics.

No broker calls; all measurements are point-in-time and preserve unknowns.
The fixed limit and the actual FILL are separate from order acceptance.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CHASING_LIMIT_PCT = Decimal("0.50")  # conservative provisional BUY cap
ROUND = Decimal("0.0001")

class EntryExtended(ValueError):
    pass

def dec(v):
    if isinstance(v, (float, bool)) or v is None:
        raise ValueError("decimal string required")
    try:
        x=Decimal(str(v))
    except (ValueError, InvalidOperation):
        raise ValueError("invalid decimal")
    if not x.is_finite() or x<=0:
        raise ValueError("invalid positive price")
    return x

def pct(value, baseline):
    v,b=dec(value),dec(baseline)
    return ((v/b-1)*100).quantize(ROUND,rounding=ROUND_HALF_UP)

def pre_order(row, proof):
    if not isinstance(proof,dict):
        raise ValueError("preflight missing")
    ext=proof["entry_extension"]
    reference=dec(ext["previous_rth_close"])
    ask=dec(proof["ask"])
    initial_ask=dec(row["quote_ask"])
    initial_last=dec(row["quote_last"])
    limit=dec(row["limit_price"])
    proposed_price=min(ask,limit)  # a resting BUY limit cannot execute above limit
    from_recommendation=pct(proposed_price,initial_ask)
    out={
        "previous_rth_close":str(reference),
        "previous_session_date":ext["previous_session_date"],
        "quote_at_order_utc":proof["quote_at"].isoformat(),
        "recommended_quote_ask":str(initial_ask),
        "recommended_quote_last":str(initial_last),
        "preorder_bid":str(dec(proof["bid"])),
        "preorder_ask":str(ask),
        "limit_price":str(limit),
        "max_executable_price_at_limit":str(proposed_price),
        "already_up_at_recommendation_pct":str(pct(initial_last,reference)),
        "already_up_at_order_ask_pct":str(pct(ask,reference)),
        "move_ask_since_recommendation_pct":str(pct(ask,initial_ask)),
        "max_price_move_since_recommendation_pct":str(from_recommendation),
        "max_entry_vs_previous_close_pct":str(pct(proposed_price,reference)),
        "max_chase_pct":str(CHASING_LIMIT_PCT),
        "price_gate":"NO_CHASE" if from_recommendation<=CHASING_LIMIT_PCT else "TOO_EXTENDED",
    }
    if from_recommendation>CHASING_LIMIT_PCT:
        raise EntryExtended("EXTENDED_FROM_RECOMMENDATION:"+
                            str(from_recommendation)+"_PCT")
    return out

def at_fill(row, average_price, qty, first_fill_utc):
    p=dec(average_price)
    old=dec(row["quote_ask"])
    close=dec(row["previous_rth_close"])
    return {
        "filled_average_price":str(p),"filled_quantity":str(dec(qty)),
        "first_fill_at_utc":first_fill_utc,
        "fill_vs_previous_close_pct":str(pct(p,close)),
        "fill_vs_recommendation_ask_pct":str(pct(p,old)),
        "fill_vs_recommendation_last_pct":str(pct(p,dec(row["quote_last"]))),
        "execution_is_fill":True,
    }
