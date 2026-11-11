"""GET-ONLY Alpaca latest SIP/BOATS quote timing audit (no trading).

Use an authorized market-DATA-only credential pair supplied as systemd LoadCredential.
Requests exact allowlisted /v2/stocks/quotes/latest endpoint, never broker API.
Logs only timestamp/age/spread/rejection categories; never keys, cash or positions.
This is a prospective observational research diagnostic, NOT a live V1 patch.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from time import sleep
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

DATA_ENDPOINT="https://data.alpaca.markets/v2/stocks/quotes/latest"
VALID_FEEDS={"sip","boats"}
MAX_AGE=timedelta(seconds=100)
MAX_SPREAD=Decimal("0.01")
MAX_SYMBOLS=20

def _parse_quote(quote, clock):
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise ValueError("reference clock must be aware")
    if quote is None:return {"status":"MISSING"}
    if not isinstance(quote,dict):return {"status":"MALFORMED"}
    try:
        stamp=datetime.fromisoformat(quote["t"].replace("Z","+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None: return {"status":"INVALID_TIMESTAMP"}
    except (KeyError,TypeError,ValueError,AttributeError):
        return {"status":"INVALID_TIMESTAMP"}
    age=clock-stamp
    age_seconds=round(age.total_seconds(),3)
    if age < timedelta(0):return {"status":"FUTURE","age_seconds":age_seconds}
    if age>MAX_AGE:return {"status":"STALE","age_seconds":age_seconds}
    try:
        bid,ask=Decimal(str(quote["bp"])),Decimal(str(quote["ap"]))
    except (KeyError,ValueError,TypeError,InvalidOperation):
        return {"status":"INVALID_PRICE","age_seconds":age_seconds}
    if not bid.is_finite() or not ask.is_finite() or min(bid,ask)<=0:
        return {"status":"INVALID_PRICE","age_seconds":age_seconds}
    if bid>ask:return {"status":"CROSSED","age_seconds":age_seconds}
    spread=(ask-bid)/ask
    if spread>MAX_SPREAD:
        return {"status":"WIDE_SPREAD","age_seconds":age_seconds,
                "spread_pct":round(100*float(spread),4)}
    return {"status":"ACCEPT","age_seconds":age_seconds,
            "spread_pct":round(100*float(spread),4)}

def categorize_response(symbols, payload, scan_started, quote_received):
    if quote_received<scan_started:raise ValueError("negative elapsed fetch")
    if not isinstance(payload,dict) or not isinstance(payload.get("quotes"),dict):
        raise ValueError("invalid quote response envelope")
    if not symbols or len(symbols)>MAX_SYMBOLS or len(symbols)!=len(set(symbols)):
        raise ValueError("invalid symbols")
    if any(not s.isalnum() or not s.isascii() for s in symbols):
        raise ValueError("invalid symbol")
    if any(s not in symbols for s in payload["quotes"]):
        raise ValueError("unexpected quote symbol")
    rows=[]
    for s in symbols:
        q=payload["quotes"].get(s)
        old=_parse_quote(q,scan_started)
        new=_parse_quote(q,quote_received)
        rows.append({"symbol":s,
                     "original_scan_clock_status":old["status"],
                     "receipt_clock_status":new["status"],
                     "receipt_age_sec":new.get("age_seconds"),
                     "spread_percent":new.get("spread_pct")})
    return {"scan_started_utc":scan_started.isoformat(),
            "quote_received_utc":quote_received.isoformat(),
            "scan_to_receipt_sec":round((quote_received-scan_started).total_seconds(),3),
            "symbol_count":len(symbols),"source":"Alpaca quotes/latest",
            "original_scan_clock_counts":dict(Counter(x["original_scan_clock_status"] for x in rows)),
            "correct_receipt_clock_counts":dict(Counter(x["receipt_clock_status"] for x in rows)),
            "old_future_but_valid_at_receipt":[x["symbol"] for x in rows if
                x["original_scan_clock_status"]=="FUTURE" and x["receipt_clock_status"]=="ACCEPT"],
            "by_symbol":rows,"orders_submitted":0,"broker_api_calls":0,"research_only":True}

def fetch_latest(symbols,feed,headers, *, opener=urlopen):
    if feed not in VALID_FEEDS:raise ValueError("unsupported feed")
    if not symbols or len(symbols)>MAX_SYMBOLS or len(symbols)!=len(set(symbols)):
        raise ValueError("invalid symbols")
    if any(not s.isascii() or not s.isalnum() for s in symbols):
        raise ValueError("invalid symbols")
    query=urlencode({"symbols":",".join(symbols),"feed":feed})
    req=Request(DATA_ENDPOINT+"?"+query, headers=headers,method="GET")
    with opener(req,timeout=12) as res:
        if res.status!=200:raise ValueError("market data HTTP failure")
        blob=res.read(500001)
        if len(blob)>500000:raise ValueError("market data payload too large")
        payload=json.loads(blob)
    received=datetime.now(timezone.utc)
    return payload,received

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--feed",choices=sorted(VALID_FEEDS),required=True)
    ap.add_argument("--symbols",default="AMD,MU,AMAT,AVGO,INTC,TSM,NVDA")
    ap.add_argument("--pre-get-delay-seconds",type=int,default=0)
    args=ap.parse_args(argv)
    if not (0<=args.pre_get_delay_seconds<=8):
        raise ValueError("delay out of bounds")
    symbols=args.symbols.split(",")
    root=Path(os.environ["CREDENTIALS_DIRECTORY"])
    headers={"APCA-API-KEY-ID":(root/"alpaca_data_key_id").read_text().strip(),
             "APCA-API-SECRET-KEY":(root/"alpaca_data_secret").read_text().strip(),
             "Accept":"application/json"}
    started=datetime.now(timezone.utc)
    if args.pre_get_delay_seconds:sleep(args.pre_get_delay_seconds)
    try:
        payload,received=fetch_latest(symbols,args.feed,headers)
        result=categorize_response(symbols,payload,started,received)
        result["feed"]=args.feed
        result["simulated_pre_get_delay_sec"]=args.pre_get_delay_seconds
        print(json.dumps(result,sort_keys=True))
        return 0
    except (HTTPError,URLError,OSError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({"status":"GET_ONLY_FAILED","error_type":type(exc).__name__,
                          "http_code":getattr(exc,"code",None),
                          "feed":args.feed,"orders_submitted":0,"broker_api_calls":0}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
