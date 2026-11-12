"""Research-only historical SIP quote-width audit for already filled PAPER orders.

Uses existing broker-verified research ledger; GET only, never submits orders.
Wide-window bid/ask demonstrates historical quote presence/staleness, NOT execution.
"""
from __future__ import annotations
import collections, json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path("/tmp/v2-rapid-exit-run6-20261111")
PREV=Path("/tmp/v2-run14-quote-typeerror-retry-20261112/quote_typeerror_retry_sanitized.json")
DEST=Path("/tmp/v2-run15-sip-quote-width-20261112")
CT=ZoneInfo("America/Chicago")

def parse(value):
    result=datetime.fromisoformat(value.replace("Z","+00:00"))
    if result.tzinfo is None: raise ValueError("Timezone required")
    return result.astimezone(timezone.utc)

def classify_rows(rows, end, qty, side):
    candidates=[]
    invalid=collections.Counter()
    for q in rows:
        if not isinstance(q,dict):
            invalid["not_object"]+=1
            continue
        try:
            ts=parse(q["t"])
            bp,ap,bs,ass=[Decimal(str(q[k])) for k in ("bp","ap","bs","as")]
            if not all(x.is_finite() for x in (bp,ap,bs,ass)): raise ValueError()
        except (KeyError,ValueError,TypeError,ArithmeticError):
            invalid["parse_error"]+=1
            continue
        if ts>end:
            invalid["future"]+=1
            continue
        if bp<=0 or ap<bp or bs<=0 or ass<=0:
            invalid["bad_cross_or_size"]+=1
            continue
        spread=Decimal(100)*(ap-bp)/ap
        if spread>1:
            invalid["spread_over_1pct"]+=1
            continue
        candidates.append((ts,spread,ass if side=="entry" else bs))
    if not candidates:
        return {"status":"NO_VALID_DISPLAYED_QUOTES","invalid":dict(invalid)}
    ts,spread,size=max(candidates,key=lambda x:x[0])
    age=round((end-ts).total_seconds(),3)
    if age<0: raise ValueError("Future quote")
    if age<=1.5 and size>=Decimal(str(qty)):
        state="FRESH_ASOF_QUOTE"
    elif age<=1.5:
        state="DISPLAYED_SIZE_INSUFFICIENT"
    else:
        state="STALE_ASOF_QUOTE"
    return {"status":state,"last_valid_quote_age_s":age,
            "last_valid_spread_pct":round(float(spread),6),
            "last_valid_side_size_ge_qty":size>=Decimal(str(qty)),
            "invalid":dict(invalid)}

def get_pages(symbol,start,end,headers):
    url="https://data.alpaca.markets/v2/stocks/"+urllib.parse.quote(symbol,safe="")+"/quotes"
    base={"start":start.isoformat(),"end":end.isoformat(),
          "feed":"sip","limit":10000,"sort":"asc"}
    items=[]
    token=None
    calls=0
    returned_null=False
    for _ in range(12):
        q=dict(base)
        if token: q["page_token"]=token
        req=urllib.request.Request(url+"?"+urllib.parse.urlencode(q),
                                   headers=headers,method="GET")
        with urllib.request.urlopen(req,timeout=30) as response:
            if response.status!=200: raise RuntimeError("GET non200")
            raw=response.read(8_000_001)
        if len(raw)>8_000_000: raise RuntimeError("Response too large")
        obj=json.loads(raw)
        if not isinstance(obj,dict) or "quotes" not in obj:
            raise RuntimeError("Malformed API shape")
        quotes=obj["quotes"]
        if quotes is None:
            returned_null=True
            quotes=[]
        if not isinstance(quotes,list):
            raise RuntimeError("Malformed quote rows")
        items.extend(quotes)
        calls+=1
        token=obj.get("next_page_token")
        if not token: return items,calls,returned_null
    raise RuntimeError("Pagination more than 12 pages: fail closed")

def main():
    if DEST.exists(): raise RuntimeError("Never overwrite prior evidence")
    reference=json.loads(PREV.read_text())
    assert len(reference["records"])==25
    assert reference["summary"]["all_completed_pairs"]==60
    data=json.loads((ROOT/"raw_research_private.json").read_text())
    assert len(data["trades"])==60
    trade_map={(t["day"],t["source"],t["symbol"]):t for t in data["trades"]}
    cred=Path("/etc/securityprepper/alpaca-feed/private")
    headers={"APCA-API-KEY-ID":(cred/"alpaca_data_key_id").read_text().strip(),
             "APCA-API-SECRET-KEY":(cred/"alpaca_data_secret").read_text().strip(),
             "Accept":"application/json"}
    records=[]
    for item in reference["records"]:
        key=(item["trade_date"],item["source"],item["symbol"])
        t=trade_map[key];side=item["leg"];end=parse(t[side+"_at"])
        if item["status"]!="MALFORMED_RESPONSE": raise ValueError("Unfamiliar cohort")
        note={"trade_date":key[0],"source":key[1],"symbol":key[2],"leg":side,
              "is_premarket":end.astimezone(CT).time().hour<8 or
                (end.astimezone(CT).time().hour==8 and end.astimezone(CT).time().minute<30)}
        for window_s in (120,300):
            try:
                rows,calls,null=get_pages(t["symbol"],end-timedelta(seconds=window_s),end,headers)
                cls=classify_rows(rows,end,t["qty"],side)
                note["window_"+str(window_s)+"s"]={"http":"200","quote_rows":len(rows),
                   "pages":calls,"quotes_null_first_response":null,**cls}
                if rows: break
            except Exception as exc:
                note["window_"+str(window_s)+"s"]={"status":"GET_ERROR",
                   "error_type":type(exc).__name__}
                break
        records.append(note)
    counts=collections.Counter()
    kinds=collections.Counter()
    ages=[]
    for r in records:
        k="window_120s"
        if r[k].get("quote_rows",0)==0 and "window_300s" in r: k="window_300s"
        entry=r[k]
        counts[entry.get("status","UNKNOWN")]+=1
        if entry.get("quote_rows",0)>0:
            kinds["with_any_raw_quote"]+=1
        if entry.get("status")=="STALE_ASOF_QUOTE": ages.append(entry["last_valid_quote_age_s"])
        kinds[("premarket" if r["is_premarket"] else "regular_or_after",entry.get("status","UNKNOWN"))]+=1
    aggregate={"sample_trades":60,"sample_leg_count":120,"target_legs":25,
               "prior_fresh_quotes":62,
               "widened_window_result":dict(counts),
               "with_any_raw_quote":kinds["with_any_raw_quote"],
               "latest_ages_seconds":sorted(ages),
               "session_status":{str(k):v for k,v in kinds.items() if isinstance(k,tuple)},
               "research_only":True,"broker_orders_submitted":0,
               "limitation":"Wider historical quotes are not contemporaneous executable liquidity; original <=1.5s coverage unchanged"}
    DEST.mkdir(mode=0o700)
    path=DEST/"quote_width_private.json"
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as f:json.dump({"summary":aggregate,"records":records},f,indent=2)
    print(json.dumps(aggregate,sort_keys=True))
if __name__=="__main__": main()
