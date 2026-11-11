"""Pure GET-only historical SIP trade bars; no orders or live strategy state.
No credential output or persistence. Offline research outcome source only.
"""
from __future__ import annotations
import json,urllib.parse,urllib.request,time
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago")
ROOT=Path("/tmp/v2-rapid-exit-run6-20261111")
SNAP=Path("/var/lib/securityprepper-paper-inventory/current.json")
KEYS=Path("/etc/securityprepper/alpaca-feed/private")
def parse(x):
    y=datetime.fromisoformat(x.replace("Z","+00:00"))
    if y.tzinfo is None: raise ValueError("naive time")
    return y
def auth():
    return {"APCA-API-KEY-ID":(KEYS/"alpaca_data_key_id").read_text().strip(),
            "APCA-API-SECRET-KEY":(KEYS/"alpaca_data_secret").read_text().strip(),
            "Accept":"application/json"}
def get(url,headers):
    req=urllib.request.Request(url,headers=headers,method="GET")
    with urllib.request.urlopen(req,timeout=18) as resp:
        if resp.status!=200:raise ValueError("GET failed")
        raw=resp.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError("oversized payload")
        return json.loads(raw)
def session(t):
    a=t.astimezone(CT)
    return (a.date()+timedelta(days=1) if a.hour>=19 else a.date()).isoformat()
def trades():
    d=json.loads(SNAP.read_text())
    if not(d.get("broker_verified") is True and d.get("paper_only") is True and
        d.get("recent_orders_complete") is True and isinstance(d.get("recent_orders"),list)):
        raise ValueError("not authoritative single paper account snapshot")
    rows=[]
    for o in d["recent_orders"]:
        if o.get("status")!="filled" or o.get("side") not in ("buy","sell"):continue
        if not o.get("filled_at") or not o.get("client_order_id"):raise ValueError("invalid fill")
        rows.append((parse(o["filled_at"]),o))
    rows.sort(key=lambda x:x[0])
    grouped=defaultdict(list)
    for ts,o in rows:
        cid=o["client_order_id"]
        source="MBB" if cid.startswith("MBB-") else "FDR" if cid.startswith("FDR-") else "OTHER"
        grouped[(source,session(ts),o["symbol"])].append((ts,o))
    matched=[]
    missing=[]
    for (source,date,symbol),x in sorted(grouped.items()):
        if len(x)!=2 or [o["side"] for _,o in x]!=["buy","sell"]:
            missing.append((source,date,symbol,len(x)))
            continue
        (entry,eo),(exit_,xo)=x
        if eo["filled_qty"]!=xo["filled_qty"]:raise ValueError("quantity mismatch")
        q=float(eo["filled_qty"])
        matched.append({"source":source,"day":date,"symbol":symbol,
            "entry_at":entry.isoformat(),"exit_at":exit_.isoformat(),
            "entry":float(eo["filled_avg_price"]),"exit":float(xo["filled_avg_price"]),
            "qty":q,"entry_type":eo.get("type"),"exit_type":xo.get("type"),
            "entry_order_id":eo["client_order_id"],"exit_order_id":xo["client_order_id"]})
    if missing:raise ValueError("ambiguous pairing, fail closed: "+str(len(missing)))
    return matched,d
def collect():
    if ROOT.exists():raise ValueError("scratch path already exists, avoid overwrite")
    ROOT.mkdir(mode=0o700)
    tr,snap=trades()
    byday=defaultdict(set)
    for r in tr:byday[r["day"]].add(r["symbol"])
    headers=auth()
    allbars={}
    coverage={}
    for day,symbols in sorted(byday.items()):
        syms=sorted(symbols)
        start=parse(day+"T00:00:00-06:00").astimezone(timezone.utc)
        end=parse(day+"T13:46:00-06:00").astimezone(timezone.utc)
        daybars={s:[] for s in syms}
        calls=0
        for i in range(0,len(syms),12):
            batch=syms[i:i+12]
            base={"symbols":",".join(batch),"timeframe":"1Min","feed":"sip",
                  "adjustment":"split","start":start.isoformat(),
                  "end":end.isoformat(),"sort":"asc","limit":10000}
            token=None
            for page in range(20):
                req=dict(base)
                if token:req["page_token"]=token
                url="https://data.alpaca.markets/v2/stocks/bars?"+urllib.parse.urlencode(req)
                obj=get(url,headers);calls+=1
                if not isinstance(obj.get("bars"),dict):raise ValueError("malformed bars")
                for sym,bb in obj["bars"].items():
                    if sym not in batch or not isinstance(bb,list):raise ValueError("unexpected symbol/bar")
                    daybars[sym].extend(bb)
                token=obj.get("next_page_token")
                if not token:break
            else:raise ValueError("unbounded SIP pagination")
        n=sum(len(v) for v in daybars.values())
        coverage[day]={"symbols":len(syms),"bars":n,"get_calls":calls,
                       "symbols_without_bars":[s for s in syms if not daybars[s]]}
        for symbol,rows in daybars.items():
            seen=set();normalized=[]
            for b in rows:
                ts=parse(b["t"])
                if ts.isoformat() in seen:raise ValueError("duplicate timestamp")
                seen.add(ts.isoformat())
                p=[float(b[k]) for k in ("o","h","l","c")]
                if min(p)<=0 or not(p[2]<=p[0]<=p[1] and p[2]<=p[3]<=p[1]):
                    raise ValueError("invalid OHLC")
                normalized.append({"t":ts.isoformat(),"o":p[0],"h":p[1],"l":p[2],
                                   "c":p[3],"v":int(b["v"])})
            allbars[day+"|"+symbol]=normalized
    sanitized={"research_only":True,"snapshot_asof_utc":snap["asof_utc"],
          "scope":"ONE_PAPER_ACCOUNT_AUTHENTICATED_ACCOUNT_ID_UNAVAILABLE",
          "trades":tr,"bars":allbars,"coverage":coverage,
          "source":"Alpaca SIP 1Min trade bars, split adjusted, GET only",
          "broker_orders_submitted":0,"execution_data_proven":False}
    out=ROOT/"raw_research_private.json"
    out.write_text(json.dumps(sanitized,separators=(",",":")))
    out.chmod(0o600)
    print("GET_ONLY_COMPLETE",json.dumps(coverage,sort_keys=True),"ROUND_TRIPS",len(tr),
          "DISTINCT_DAYS",len(coverage))
if __name__=="__main__":
    collect()
