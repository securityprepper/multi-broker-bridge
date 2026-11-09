"""Historical SIP bid/ask snapshots near completed-bar entry candidates.

READ ONLY. Bounded GET to data.alpaca.markets; never broker order endpoints.
Quotes near a historical signal do not guarantee PAPER or real fills.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from decimal import Decimal
from urllib.parse import urlencode
import json
from zoneinfo import ZoneInfo
from .auto_paper import _fetch_json,market_headers,DATA_HOST

CT=ZoneInfo("America/Chicago")
CANDIDATES=(
    ("AMD","2026-11-09 03:18"),
    ("CAT","2026-11-09 06:50"),
    ("CRWD","2026-11-09 08:46"),
    ("PANW","2026-11-09 08:47"),
    ("PWR","2026-11-09 08:50"),
    ("GS","2026-11-09 09:53"),
)
LIMIT=10000

def sample(symbol:str,when:datetime)->dict:
    # service itself evaluates after one-minute candle completion; use 40s
    # later to approximate the existing observer's one-minute schedule.
    clock=when+timedelta(seconds=40)
    start=clock-timedelta(seconds=15)
    end=clock+timedelta(seconds=5)
    query=urlencode({"start":start.isoformat(),"end":end.isoformat(),
                     "feed":"sip","limit":LIMIT,"sort":"asc"})
    result=_fetch_json(DATA_HOST+"/v2/stocks/"+symbol+"/quotes?"+query,
                       headers=market_headers(),timeout=12)
    if result.get("next_page_token"):
        return {"status":"INCOMPLETE_PAGE","signal_ct":when.strftime("%H:%M")}
    items=result.get("quotes",[])
    if not isinstance(items,list):raise ValueError("Quotes not list")
    eligible=[]
    for obj in items:
        try:
            timestamp=datetime.fromisoformat(obj["t"].replace("Z","+00:00"))
            bid=Decimal(str(obj["bp"]));ask=Decimal(str(obj["ap"]))
            if (timestamp.tzinfo is None or timestamp>clock or
                not all(v.is_finite() and v>0 for v in (bid,ask)) or ask<bid):
                continue
            if (ask-bid)/ask>Decimal("0.01"):continue
            eligible.append((timestamp,bid,ask))
        except (KeyError,ValueError,TypeError):
            continue
    if not eligible:
        return {"status":"NO_VERIFIED_QUOTE_AT_DECISION_TIME",
                "signal_ct":when.strftime("%H:%M"),
                "observed_quotes":len(items)}
    t,bid,ask=max(eligible,key=lambda x:x[0])
    return {"status":"HISTORICAL_SIP_QUOTE_AVAILABLE",
            "signal_ct":when.strftime("%H:%M"),
            "decision_ct":clock.strftime("%H:%M:%S"),
            "latest_eligible_quote_ct":t.astimezone(CT).strftime("%H:%M:%S.%f")[:12],
            "bid":str(bid),"ask":str(ask),
            "spread_pct":str(((ask-bid)/ask*100).quantize(Decimal(".001"))),
            "quote_age_seconds":round((clock-t).total_seconds(),2),
            "observed_quotes":len(items)}

def main():
    result={}
    for symbol,txt in CANDIDATES:
        when=datetime.strptime(txt,"%Y-%m-%d %H:%M").replace(tzinfo=CT)
        try:
            result[symbol]=sample(symbol,when)
        except Exception as err:
            result[symbol]={"status":"QUERY_FAILED",
                            "error_type":type(err).__name__}
    print(json.dumps({"status":"HISTORICAL_QUOTE_REPLAY",
                      "results":result,
                      "not_executions":True,
                      "orders_submitted":0},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
