"""Official SEC issuer-submissions metadata research pilot for activist Schedule 13D.
Research only: no broker API, no trading, no alerts, no background process.
Issuer submission lists are not a certified target-issuer index for third-party filers.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json, time
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

SEC="https://www.sec.gov"
DSEC="https://data.sec.gov"
UA="SecurityPrepper public EDGAR research home@securityprepper.com"
SYMBOLS=("AMD","MU","NVDA","CAT","GS","JPM","BAC","CRWD","PANW",
          "MSFT","XOM","CVX","UNH","LLY","PEP","ACN","SBUX")
FORMS=("SC 13D","SC 13D/A","SC 13G","SC 13G/A")
MAX_RESPONSE_BYTES=3_000_000

def get_json(url):
    time.sleep(.55)
    if not url.startswith((SEC+"/",DSEC+"/")): raise ValueError("non-SEC URL")
    with urlopen(Request(url,headers={"User-Agent":UA,"Accept":"application/json"}),timeout=14) as r:
        if r.status!=200:raise ValueError("status not 200")
        return json.loads(r.read(MAX_RESPONSE_BYTES))

def bounded_summary(sub, *, cutoff):
    recent=sub.get("filings",{}).get("recent",{})
    forms=recent.get("form",[])
    acc=recent.get("acceptanceDateTime",[])
    nums=recent.get("accessionNumber",[])
    if not (isinstance(forms,list) and len(forms)==len(acc)==len(nums)):
        raise ValueError("malformed parallel SEC metadata")
    counts=Counter()
    sample=[]
    for f,dt,number in zip(forms,acc,nums):
        if f not in FORMS:continue
        try:when=datetime.fromisoformat(dt.replace("Z","+00:00"))
        except (TypeError,ValueError):continue
        if when.tzinfo is None: continue
        when=when.astimezone(timezone.utc)
        if when>cutoff:continue
        counts[f]+=1
        if len(sample)<5:sample.append({"form":f,"accepted_at_utc":when.isoformat(),"accession":number})
    return {"form_counts":dict(counts),"recent_rows":len(forms),"examples":sample}

def main():
    cutoff=datetime.now(timezone.utc)
    output={"research_only":True,"observation_utc":cutoff.isoformat(),
        "source":"public official SEC issuer submissions (NOT target-issuer comprehensive)",
        "first_observed_historical_13d_available":False,
        "approved_strategy":False,"broker_requests":0,"broker_orders":0,
        "sample_scope":list(SYMBOLS),"issuers":{}}
    raw=get_json(SEC+"/files/company_tickers.json")
    mapping={v["ticker"].upper():v["cik_str"] for v in raw.values()}
    for sym in SYMBOLS:
        issuer={"ticker":sym,"source_scope":"issuer-submissions only","cik":mapping.get(sym),
                "status":"UNKNOWN","form_counts":{},"recent_rows":None}
        output["issuers"][sym]=issuer
        if issuer["cik"] is None:issuer["status"]="CIK_UNRESOLVED";continue
        try:
            d=get_json(f"{DSEC}/submissions/CIK{int(issuer['cik']):010d}.json")
            summ=bounded_summary(d,cutoff=cutoff)
            issuer.update(summ);issuer["status"]="ISSUER_SUBMISSIONS_READ"
        except (HTTPError,URLError,TimeoutError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
            issuer["status"]="SOURCE_UNAVAILABLE_"+type(exc).__name__
        print(sym,issuer["status"],issuer["form_counts"],flush=True)
    valid=[v for v in output["issuers"].values() if v["status"]=="ISSUER_SUBMISSIONS_READ"]
    output["totals"]={"issuer_reads_valid":len(valid),"issuer_reads_unknown":len(SYMBOLS)-len(valid),
        "form_counts":dict(sum((Counter(x["form_counts"]) for x in valid), Counter())),
        "complete_target_issuer_13d_coverage":False,
        "qualified_trades":0,"observed_credible_first_seen_event_count":0}
    p=Path("/tmp/v2-distinct-13d-issuer-20261111.json")
    p.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("TOTALS",output["totals"])
if __name__=="__main__":main()