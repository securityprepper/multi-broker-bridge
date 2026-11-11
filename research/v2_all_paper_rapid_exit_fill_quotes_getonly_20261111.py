"""GET-only historical SIP NBBO at actual filled-order final timestamps.
For each observed filled BUY/SELL order fetch bid/ask strictly <= filled_at;
no lookahead, broker order submission, account credential persistence or
assertion about full size, queue, hidden liquidity, or actual commission.
"""
import json,urllib.parse,urllib.request
from datetime import datetime,timedelta
from pathlib import Path
from collections import Counter
ROOT=Path("/tmp/v2-rapid-exit-run6-20261111")
z=json.loads((ROOT/"raw_research_private.json").read_text())
creds=Path("/etc/securityprepper/alpaca-feed/private")
headers={"APCA-API-KEY-ID":(creds/"alpaca_data_key_id").read_text().strip(),
         "APCA-API-SECRET-KEY":(creds/"alpaca_data_secret").read_text().strip(),
         "Accept":"application/json"}
outpath=ROOT/"actual_fill_quotes_private.json"
if outpath.exists():raise RuntimeError("will not rewrite raw private quote evidence")
snapshot={}
for trade in z["trades"]:
 for side in ("entry","exit"):
    sym=trade["symbol"]
    ts=datetime.fromisoformat(trade[side+"_at"])
    st=ts-timedelta(seconds=5)
    q={"start":st.isoformat(),"end":ts.isoformat(),"limit":10000,"feed":"sip"}
    url="https://data.alpaca.markets/v2/stocks/"+sym+"/quotes?"+urllib.parse.urlencode(q)
    key=trade["day"]+"|"+trade["source"]+"|"+sym+"|"+side
    r={"status":"UNKNOWN"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers,method="GET"),timeout=12) as h:
            if h.status!=200:raise ValueError("HTTP status not OK")
            blob=h.read(4_000_001)
        if len(blob)>4_000_000:raise ValueError("payload too large")
        payload=json.loads(blob)
        if payload.get("next_page_token"):raise ValueError("truncated quotes, fail closed")
        values=[]
        for x in payload.get("quotes",[]):
            qt=datetime.fromisoformat(x["t"].replace("Z","+00:00"))
            bp=float(x["bp"]);ap=float(x["ap"])
            if not (st<=qt<=ts and bp>0 and ap>=bp):continue
            spread=100*(ap-bp)/ap
            if spread>1:continue
            values.append((qt,bp,ap,int(x.get("bs",0)),int(x.get("as",0)),spread))
        if values:
            qt,bp,ap,bs,ass,spread=sorted(values)[-1]
            age=(ts-qt).total_seconds()
            if age<=1.5:
                qsize=bs if side=="exit" else ass
                r={"status":"FRESH_ASOF_QUOTE","quote_time_utc":qt.isoformat(),
                   "quote_age_seconds":round(age,4),"bid":bp,"ask":ap,
                   "bid_size":bs,"ask_size":ass,
                   "spread_pct":round(spread,6),
                   "size_at_best_at_least_order_quantity":qsize>=trade["qty"],
                   "actual_fill_vs_quote_pct":round(100*((trade["exit"]/bp-1) if side=="exit" else (trade["entry"]/ap-1)),6)}
            else:r={"status":"QUOTE_STALE","age_seconds":round(age,3)}
        else:r={"status":"NO_VALID_ASOF_QUOTE"}
    except Exception as e:r={"status":"HISTORICAL_QUOTE_UNAVAILABLE","error_type":type(e).__name__}
    snapshot[key]=r
outpath.write_text(json.dumps({"evidence":"SIP quotes strictly before actual broker final-fill timestamps",
    "quotes":snapshot,"research_only":True,"orders_submitted":0},separators=(",",":")))
outpath.chmod(0o600)
print("HISTORICAL_FILL_ASOF_QUOTE_COVERAGE",len(snapshot),dict(Counter(x["status"] for x in snapshot.values())))
