"""Offline, research-only corroboration of an Alpaca PAPER exit.
No network, broker credentials, order submission, or live strategy imports.
Input consists of broker-verified, separately collected evidence.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from collections import Counter

def stamp(v):
    d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return d.astimezone(timezone.utc)

def amount(v):
    return Decimal(str(v))

def validate_fills(orders, activities):
    if len({o["id"] for o in orders}) != len(orders):
        raise ValueError("duplicate broker order UUID")
    if len({a["id"] for a in activities}) != len(activities):
        raise ValueError("duplicate activity UUID")
    by_order = {o["id"]: [] for o in orders}
    for a in activities:
        if a["order_id"] not in by_order:
            raise ValueError("activity references unverified broker order")
        by_order[a["order_id"]].append(a)
    for o in orders:
        if o["status"] != "filled" or not o.get("filled_at"):
            raise ValueError("not a filled order")
        if sum((amount(a["qty"]) for a in by_order[o["id"]]), Decimal("0")) != amount(o["filled_qty"]):
            raise ValueError("broker and activity quantities disagree")
        if not by_order[o["id"]]:
            raise ValueError("missing broker fill activities")
    if len(orders) != 2 or orders[0]["side"] != "buy" or orders[1]["side"] != "sell":
        raise ValueError("one buy and one sell required")
    if orders[0]["symbol"] != orders[1]["symbol"] or amount(orders[0]["filled_qty"]) != amount(orders[1]["filled_qty"]):
        raise ValueError("symbol or matched quantity mismatch")
    return True

def assess(orders, activities, accepted, bars, peak_quote, exit_quote):
    validate_fills(orders, activities)
    buy, sell = orders
    if accepted.get("broker_order_id") != sell["id"] or accepted.get("symbol") != sell["symbol"] or accepted.get("side") != "sell":
        raise ValueError("journal and broker sell UUID do not match")
    if accepted.get("exit_fill_verified") is True:
        raise ValueError("acceptance cannot assert final fill")
    decision = stamp(accepted["at"])
    filled = stamp(sell["filled_at"])
    entry = stamp(buy["filled_at"])
    if not entry < decision <= filled:
        raise ValueError("noncausal broker timing")
    qty = amount(buy["filled_qty"])
    entry_price = amount(buy["filled_avg_price"])
    exit_price = amount(sell["filled_avg_price"])
    observed = []
    for b in sorted(bars, key=lambda x: stamp(x["t"])):
        start = stamp(b["t"])
        end = start + timedelta(minutes=1)
        if start >= entry and end <= decision:
            observed.append((end, amount(b["h"]), amount(b["c"])))
    if not observed:
        raise ValueError("no fully completed post-fill minute bars")
    peak = Decimal("0")
    first_cross = None
    for end, high, close in observed:
        peak = max(peak, high)
        if first_cross is None and peak >= entry_price * Decimal("1.005") and close <= peak * Decimal("0.995"):
            first_cross = (end, close, peak)
    def quote(q):
        t = stamp(q["t"])
        bid, ask, size = amount(q["bp"]), amount(q["ap"]), amount(q["bs"])
        if bid <= 0 or ask < bid or size < qty:
            raise ValueError("invalid, crossed, or undersized quote")
        return t, bid, ask, size
    peak_at, peak_bid, _, peak_size = quote(peak_quote)
    exit_at, exit_bid, exit_ask, exit_size = quote(exit_quote)
    if not (entry < peak_at <= decision and peak_at <= exit_at <= decision):
        raise ValueError("future or prefill quotes")
    age = (decision - exit_at).total_seconds()
    if age < 0 or age > 1.5:
        raise ValueError("exit quote outside freshness budget")
    return {
        "symbol": buy["symbol"],
        "quantity": str(qty),
        "gross_pnl_usd": str((exit_price - entry_price) * qty),
        "broker_fill_activity_events": len(activities),
        "sell_accept_to_fill_seconds": round((filled - decision).total_seconds(), 3),
        "accepted_reason": accepted.get("exit_signal_reason") or "UNKNOWN",
        "first_completed_reversal_at": first_cross[0].isoformat() if first_cross else None,
        "first_completed_reversal_close": str(first_cross[1]) if first_cross else None,
        "completed_bar_peak": str(peak),
        "peak_quote_bid": str(peak_bid),
        "peak_bid_size": str(peak_size),
        "exit_quote_bid": str(exit_bid),
        "exit_quote_ask": str(exit_ask),
        "exit_bid_size": str(exit_size),
        "exit_quote_age_seconds": round(age, 6),
        "one_pct_target_reached_by_completed_bar_high": peak >= entry_price * Decimal("1.01"),
        "corroborated": accepted.get("exit_signal_reason") == "trailing peak reversal" and first_cross is not None and peak_bid >= peak - Decimal("0.01") and exit_bid <= peak * Decimal("0.995"),
        "execution_note": "Historical SIP quotes not proof of simultaneous executable alternative fills; gross broker PAPER P/L before unknown fees."
    }
