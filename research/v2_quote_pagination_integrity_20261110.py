"""Research-only causal quote completeness check; no network or broker orders.

Alpaca historical multi-symbol quote GET can return a page token after its
10,000-record limit. Never label absent symbols NO_QUOTE until every page is
complete. This historical endpoint is distinct from the executor's /quotes/latest
endpoint; this tool cannot prove the executor's original runtime rejection cause.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from collections import Counter

def classify(q, observed_at):
    if q is None: return "NO_QUOTE_IN_COMPLETE_WINDOW"
    try:
        t=datetime.fromisoformat(q["t"].replace("Z","+00:00"))
        if t.tzinfo is None: return "INVALID_TIMESTAMP"
        age=(observed_at-t).total_seconds()
        if age<0:return "FUTURE"
        if age>100:return "STALE"
        b,a=Decimal(str(q["bp"])),Decimal(str(q["ap"]))
        if not (b.is_finite() and a.is_finite()) or min(b,a)<=0:return "INVALID_PRICE"
        if b>a:return "CROSSED"
        if (a-b)/a>Decimal("0.01"):return "WIDE_SPREAD"
        return "ACCEPT"
    except (KeyError,TypeError,ValueError,InvalidOperation):
        return "MALFORMED"

def audit_pages(symbols, pages, observed_at):
    """pages are previously obtained GET responses, no HTTP performed."""
    if observed_at.tzinfo is None: raise ValueError("aware reference required")
    if not symbols or len(symbols)!=len(set(symbols)):raise ValueError("duplicate/empty symbols")
    last_by_symbol={}
    for i,page in enumerate(pages):
        if not isinstance(page,dict) or not isinstance(page.get("quotes"),dict):
            raise ValueError("malformed quote page")
        token=page.get("next_page_token")
        if i<len(pages)-1 and not token:
            raise ValueError("unexpected extra pages after completed page")
        for symbol,items in page["quotes"].items():
            if symbol not in symbols or not isinstance(items,list):raise ValueError("unexpected symbol/quote rows")
            for q in items:
                try:t=datetime.fromisoformat(q["t"].replace("Z","+00:00"))
                except (KeyError,TypeError,ValueError):continue
                if t.tzinfo is None or t>observed_at:continue
                if symbol not in last_by_symbol or t>last_by_symbol[symbol][0]:
                    last_by_symbol[symbol]=(t,q)
    complete=bool(pages) and not pages[-1].get("next_page_token")
    rows={}
    for s in symbols:
        if s in last_by_symbol: rows[s]=classify(last_by_symbol[s][1],observed_at)
        else:rows[s]="NO_QUOTE_IN_COMPLETE_WINDOW" if complete else "NOT_YET_FETCHED_PAGE"
    return {"complete":complete,"observed_at":observed_at.isoformat(),
            "reason_counts":dict(Counter(rows.values())),"symbol_reasons":rows,
            "source":"historical multi-symbol quotes (NOT original executor latest response)",
            "no_orders":True}

def requires_more_pages(audit):
    return not audit["complete"] and "NOT_YET_FETCHED_PAGE" in audit["reason_counts"]
