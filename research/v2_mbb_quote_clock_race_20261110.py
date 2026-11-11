"""RESEARCH-ONLY MBB quote clock diagnostic. Never fetches data or sends orders.

Active V1 bug under investigation: scan-start `now` remains frozen while
account, positions, orders, 47-minute bars and quotes/latest are fetched.
A quote created later in that same run is incorrectly rejected as future.
Use actual receipt-time, not scan-start-time, to check age; never allow quotes
which are later than retrieval or older than 100 seconds.
"""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from collections import Counter

MAX_QUOTE_AGE_SECONDS=100
MAX_SPREAD=Decimal("0.01")

def validate_observed_quote(quote,received_at):
    """Return category + validated bid/ask if and only if quote is usable."""
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise ValueError("aware receipt timestamp required")
    if quote is None:return {"reason":"QUOTE_ABSENT"}
    if not isinstance(quote,dict):return {"reason":"MALFORMED"}
    try:
        qt=datetime.fromisoformat(quote["t"].replace("Z","+00:00"))
        if qt.tzinfo is None or qt.utcoffset() is None:
            return {"reason":"TIMESTAMP_INVALID"}
    except (KeyError,ValueError,TypeError,AttributeError):
        return {"reason":"TIMESTAMP_INVALID"}
    age=(received_at-qt).total_seconds()
    if age<0:return {"reason":"AFTER_RECEIPT_FUTURE","age_seconds":round(age,3)}
    if age>MAX_QUOTE_AGE_SECONDS:
        return {"reason":"STALE","age_seconds":round(age,3)}
    try:
        bid=Decimal(str(quote["bp"]));ask=Decimal(str(quote["ap"]))
    except (KeyError,ValueError,TypeError,InvalidOperation):
        return {"reason":"PRICE_INVALID","age_seconds":round(age,3)}
    if not bid.is_finite() or not ask.is_finite() or bid<=0 or ask<=0:
        return {"reason":"PRICE_INVALID","age_seconds":round(age,3)}
    if bid>ask:return {"reason":"CROSSED","age_seconds":round(age,3)}
    spread=(ask-bid)/ask
    if spread>MAX_SPREAD:return {"reason":"WIDE_SPREAD","age_seconds":round(age,3)}
    return {"reason":"ACCEPT","bid":bid,"ask":ask,"age_seconds":round(age,3),
            "spread_percent":round(float(spread)*100,4)}

def classify_batch(symbols,payload,received_at):
    """Audit already fetched GET /quotes/latest payload, no market API call."""
    if not isinstance(payload,dict) or not isinstance(payload.get("quotes"),dict):
        raise ValueError("quote response envelope malformed")
    if len(symbols)!=len(set(symbols)) or not symbols:
        raise ValueError("symbol list invalid/duplicate")
    result={s:validate_observed_quote(payload["quotes"].get(s),received_at) for s in symbols}
    return {"counts":dict(Counter(x["reason"] for x in result.values())),
            "symbols":result,"no_network":True,"no_orders":True,
            "asof_receipt":received_at.isoformat()}

def old_v1_acceptance(quote,scan_start):
    """Reproduce only the source's 100-second/1% timestamp+price checks."""
    return validate_observed_quote(quote,scan_start)["reason"]=="ACCEPT"

def temporal_diagnostic(quote,scan_start,receipt_time):
    if receipt_time<scan_start:
        raise ValueError("receipt preceding scan")
    return {"v1_accepts":old_v1_acceptance(quote,scan_start),
            "correct_at_receipt":validate_observed_quote(quote,receipt_time)["reason"],
            "elapsed_between_scan_and_receipt_seconds":round((receipt_time-scan_start).total_seconds(),3)}
