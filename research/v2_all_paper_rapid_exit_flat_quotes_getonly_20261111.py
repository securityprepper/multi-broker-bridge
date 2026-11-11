"""Research-only historical SIP quote snapshot at intended 13:40 CT forced-flat; GET-only.
Does NOT assert executable fill, full displayed depth, or absence of cancellation.
"""
import json,urllib.parse,urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago")
BASE=Path("/tmp/v2-rapid-exit-run6-20261111")
obj=json.loads((BASE/"raw_research_private.json").read_text())
k=Path("/etc/securityprepper/alpaca-feed/private")
headers={"APCA-API-KEY-ID":(k/"alpaca_data_key_id").read_text().strip(),
         "APCA-API-SECRET-KEY":(k/"alpaca_data_secret").read_text().strip(),
         "Accept":"application/json"}
if (BASE/"flat_quotes_private.json").exists():
    raise RuntimeError("refuse to rewrite completed snapshot")
results={}
for day,sym in sorted({(x["day"],x["symbol"]) for x in obj["trades"]}):
    stop=datetime.fromisoformat(day+"T13:40:00-06:00").astimezone(timezone.utc)
    start=stop-timedelta(seconds=7)
    q={"start":start.isoformat(),"end":stop.isoformat(),"feed":"sip","limit":10000}
    url="https://data.alpaca.markets/v2/stocks/"+sym+"/quotes?"+urllib.parse.urlencode(q)
    r={"status":"UNKNOWN_QUOTE_MISSING"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers,method="GET"),timeout=15) as h:
            if h.status!=200:raise ValueError("GET returned non-200")
            raw=h.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError("oversized quote batch")
        doc=json.loads(raw)
        if doc.get("next_page_token"):raise ValueError("quotes incomplete pagination")
        values=[]
        for x in doc.get("quotes",[]):
            ts=datetime.fromisoformat(x["t"].replace("Z","+00:00"))
            bid=float(x["bp"]);ask=float(x["ap"])
            if ts>stop or ts<start or bid<=0 or ask<=0 or bid>ask:continue
            if (ask-bid)/ask>0.01:continue
            values.append((ts,bid,ask,int(x.get("bs",0)),int(x.get("as",0))))
        if values:
            dt,bid,ask,bs,ass=sorted(values)[-1]
            age=(stop-dt).total_seconds()
            if age<=2:
                r={"status":"FRESH_TIGHT_INDICATIVE_QUOTE","quote_t_utc":dt.isoformat(),
                   "age_s":round(age,4),"bid":bid,"ask":ask,"bid_size":bs,
                   "ask_size":ass,"spread_pct":round(100*(ask-bid)/ask,5)}
            else:r={"status":"STALE_LAST_QUOTE","age_s":round(age,3)}
    except Exception as exc:r={"status":"QUOTE_DATA_UNAVAILABLE","cause_type":type(exc).__name__}
    results[day+"|"+sym]=r
out=BASE/"flat_quotes_private.json"
out.write_text(json.dumps({"source":"Alpaca historical SIP NBBO GET only", "no_orders":True,
    "quotes":results},separators=(",",":")))
out.chmod(0o600)
from collections import Counter
print("QUOTES_GET_DONE",len(results),dict(Counter(r["status"] for r in results.values())),
      "TOTAL_FRESH_DISPLAYED_BID",sum(r.get("bid_size",0)>0 for r in results.values()))
