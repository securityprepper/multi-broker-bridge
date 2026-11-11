"""GET-only independent SIP latest-quote receipt-time diagnostic.
Research-only, no broker endpoints, positions, orders, notification or recommendations.
Output is aggregated acceptance/rejection reasons, no credentials, cash or prices.
"""
from __future__ import annotations
import json,math,os,re
from collections import Counter
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

HOST="https://data.alpaca.markets/v2/stocks/quotes/latest"
SYMBOLS=("AMD","MU","SNDK","NVDA","AMAT","AVGO","INTC","TSM","CRWD","PANW","ZS","CAT","GE","BA","GS","JPM","BAC")
MAX_AGE_SEC=100.0
MAX_SPREAD=0.01
def parse(ts):
    d=datetime.fromisoformat(str(ts).replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("missing timezone")
    return d.astimezone(timezone.utc)

def evaluate_one(quote, received_at, scan_started_at):
    """Same quote-validation gates as V1 corrected code, with old-clock what-if."""
    d={"corrected":"REJECT_BAD_QUOTE","scan_start_clock":"REJECT_BAD_QUOTE",
       "age_at_receipt_s":None,"age_at_scan_start_s":None,"spread_pct":None}
    if not isinstance(quote,dict):return d
    try:
        q=parse(quote["t"])
        bid=float(quote["bp"]);ask=float(quote["ap"])
        if not all(map(math.isfinite,(bid,ask))) or min(bid,ask)<=0 or bid>ask:
            d["corrected"]=d["scan_start_clock"]="REJECT_INVALID_MARKET"
            return d
        spread=(ask-bid)/ask
        d["spread_pct"]=round(spread*100,5)
        if spread>MAX_SPREAD:
            d["corrected"]=d["scan_start_clock"]="REJECT_SPREAD"
            return d
        actual_age=(received_at-q).total_seconds()
        scan_age=(scan_started_at-q).total_seconds()
        d["age_at_receipt_s"]=round(actual_age,4)
        d["age_at_scan_start_s"]=round(scan_age,4)
        d["corrected"]=("ACCEPT" if 0<=actual_age<=MAX_AGE_SEC
                       else "REJECT_QUOTE_FUTURE" if actual_age<0
                       else "REJECT_QUOTE_STALE")
        d["scan_start_clock"]=("ACCEPT" if 0<=scan_age<=MAX_AGE_SEC
                              else "REJECT_QUOTE_FUTURE" if scan_age<0
                              else "REJECT_QUOTE_STALE")
    except (ValueError,TypeError,KeyError,OverflowError):
        pass
    return d

def classify(quotes,received_at,scan_started_at,symbols=SYMBOLS):
    if not isinstance(quotes,dict):raise ValueError("invalid quotes envelope")
    rows={symbol:evaluate_one(quotes.get(symbol),received_at,scan_started_at) for symbol in symbols}
    counts={name:dict(sorted(Counter(x[name] for x in rows.values()).items()))
            for name in ("corrected","scan_start_clock")}
    changed=[symbol for symbol,x in rows.items() if x["corrected"]!=x["scan_start_clock"]]
    return {"symbols_checked":len(symbols),
            "quote_received_at_utc":received_at.isoformat(),
            "comparison_scan_start_utc":scan_started_at.isoformat(),
            "scan_start_comparison_is_illustrative_not_live_v1_scan":True,
            "earlier_lookback_s":round((received_at-scan_started_at).total_seconds(),4),
            "reason_counts":counts,
            "changed_acceptance_symbols":changed,
            "symbols_diagnostic":rows,
            "orders_submitted":0,
            "research_only":True,
            "credentials_exposed":False,
            "not_executable_fills":True}

def run(fetch=urlopen,now=lambda:datetime.now(timezone.utc)):
    directory=Path(os.environ.get("CREDENTIALS_DIRECTORY",""))
    if not directory.is_absolute() or not directory.is_dir():
        raise ValueError("systemd LoadCredential required")
    key=(directory/"alpaca_data_key_id").read_text().strip()
    secret=(directory/"alpaca_data_secret").read_text().strip()
    if not key or not secret:raise ValueError("data-only credential empty")
    observed_start=now()
    req=Request(HOST+"?"+urlencode({"symbols":",".join(SYMBOLS),"feed":"sip"}),
                headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,
                         "Accept":"application/json"},method="GET")
    with fetch(req,timeout=10) as response:
        if response.status!=200:raise ValueError("GET provider not 200")
        raw=response.read(250000)
    actual_receipt=now()
    payload=json.loads(raw)
    if not isinstance(payload,dict):raise ValueError("missing payload")
    quotes=payload.get("quotes")
    if not isinstance(quotes,dict):raise ValueError("no quote envelope")
    # Compare to emulated historical scan-start ~6 seconds pre-receipt;
    # not an assertion that active V1 had this exact start timestamp.
    hypothetical_scan_start=actual_receipt-timedelta(seconds=6)
    output=classify(quotes,actual_receipt,hypothetical_scan_start)
    output.update({"request_sent_at_utc":observed_start.isoformat(),
                   "request_total_elapsed_s":round((actual_receipt-observed_start).total_seconds(),4),
                   "quotes_received":sum(s in quotes for s in SYMBOLS)})
    return output
if __name__=="__main__":
    try:print(json.dumps(run(),sort_keys=True))
    except Exception as exc:
        # Never include raw error string; could contain credentials, headers or URLs.
        print(json.dumps({"status":"GET_ONLY_QUOTE_SAMPLE_ERROR","kind":type(exc).__name__,
                          "orders_submitted":0,"credentials_exposed":False}))
        raise SystemExit(2)
