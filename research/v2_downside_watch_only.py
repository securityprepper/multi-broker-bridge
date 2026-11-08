"""Independent V2 alert-only semiconductor downside watcher.

Only HTTP GET historical Alpaca stock market bars and POST Pushover alerts.
NEVER submits, cancels, retries or changes PAPER/LIVE broker orders.
Designed as a separate read-only warning sidecar, without altering V1 monitors.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone, date, time
from decimal import Decimal
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
CT=ZoneInfo("America/Chicago")
DATA_HOST="https://data.alpaca.markets"
PUSHOVER="https://api.pushover.net/1/messages.json"
ANCHORS=("AMD","MU","SNDK")
ETF="SOXX"
PEERS=("NVDA","AVGO","WDC","TSM","INTC")
UNIVERSE=(*ANCHORS,ETF,*PEERS)


def session_and_feed(now):
    """Return target regular session / observable extended hours feed."""
    local=now.astimezone(ET)
    wd=local.weekday()
    h=local.hour
    if wd==5 or wd==6 and h<20 or wd==4 and h>=20:return None,None
    if wd==6:return local.date()+timedelta(days=1),"boats"
    if local.time()>=time(16):
        if wd==4:return None,None
        return local.date()+timedelta(days=1),("sip" if h<20 else "boats")
    return local.date(),("boats" if h<4 else "sip")


def classify(prior, observed):
    """Use only completed, same-feed 5m bars ending before current time.

    Each symbol mapping is [oldest_close_at_minus15m, latest_close],
    with newest close adjusted consistently with its completed daily close.
    """
    details={}
    for symbol in UNIVERSE:
        if symbol not in prior or symbol not in observed:
            continue
        old,cur=observed[symbol]
        base=Decimal(str(prior[symbol]))
        old=Decimal(str(old));cur=Decimal(str(cur))
        if min(base,old,cur)<=0:continue
        change=cur/base-1
        momentum=cur/old-1
        details[symbol]=(change,momentum)
    sector_watch=False
    sector_severe=False
    if all(x in details for x in (*ANCHORS,ETF)):
        sector_watch=(sum(details[s][0]<=Decimal("-.003") and
                          details[s][1]<=Decimal("-.002") for s in ANCHORS)>=2
                      and details[ETF][0]<=Decimal("-.0015")
                      and details[ETF][1]<=0)
        sector_severe=(sum(details[s][0]<=Decimal("-.015") and
                           details[s][1]<=Decimal("-.007") for s in ANCHORS)>=2
                       and details[ETF][0]<=Decimal("-.0075")
                       and details[ETF][1]<=0)
    stock_watch=[s for s,(p,m) in details.items()
                 if s!=ETF and p<=Decimal("-.02") and m<=Decimal("-.005")]
    stock_urgent=[s for s,(p,m) in details.items()
                  if s!=ETF and p<=Decimal("-.04") and m<=Decimal("-.01")]
    return {
        "sector_watch":sector_watch,
        "sector_severe":sector_severe,
        "stock_watch":stock_watch,
        "stock_urgent":stock_urgent,
        "details":{s:{"since_close_pct":round(float(p*100),2),
                      "last_15m_pct":round(float(m*100),2)}
                   for s,(p,m) in details.items()},
    }


def creds(name):
    root=Path(os.environ.get("CREDENTIALS_DIRECTORY","/path-not-configured"))
    value=(root/name).read_text(encoding="utf-8").strip()
    if not value:raise RuntimeError("missing credential: "+name)
    return value


def get_json(url,headers):
    if not url.startswith(DATA_HOST+"/v2/stocks/"):
        raise ValueError("bad market data URL")
    with urlopen(Request(url,headers=headers,method="GET"),timeout=9) as response:
        if response.status!=200:raise ValueError("market data non-200")
        blob=response.read(2400000)
        if len(blob)>=2400000:raise ValueError("oversized historical data")
        result=json.loads(blob)
        if not isinstance(result,dict):raise ValueError("malformed market response")
        return result


def market_snapshot(now,target,feed):
    api={"APCA-API-KEY-ID":creds("alpaca_data_key_id"),
         "APCA-API-SECRET-KEY":creds("alpaca_data_secret")}
    q=urlencode({"symbols":",".join(UNIVERSE),"feed":"sip","timeframe":"1Day",
                "adjustment":"split","start":(now-timedelta(days=25)).isoformat(),
                "end":now.isoformat(),"limit":10000})
    daily=get_json(DATA_HOST+"/v2/stocks/bars?"+q,api)
    if daily.get("next_page_token"):raise ValueError("incomplete daily response")
    prior={}
    for s in UNIVERSE:
        candles=[x for x in daily.get("bars",{}).get(s,[])
                 if str(x.get("t",""))[:10]<target.isoformat()]
        if candles:prior[s]=Decimal(str(candles[-1]["c"]))
    q=urlencode({"symbols":",".join(UNIVERSE),"feed":feed,"timeframe":"5Min",
                 "adjustment":"split","start":(now-timedelta(minutes=40)).isoformat(),
                 "end":(now-timedelta(seconds=15)).isoformat(),"limit":10000})
    bars=get_json(DATA_HOST+"/v2/stocks/bars?"+q,api)
    if bars.get("next_page_token"):raise ValueError("incomplete 5min response")
    observed={};asof=[]
    for s in UNIVERSE:
        candles={}
        for b in bars.get("bars",{}).get(s,[]):
            when=datetime.fromisoformat(b["t"].replace("Z","+00:00"))
            if when.tzinfo is None or when+timedelta(minutes=5)>now-timedelta(seconds=15):continue
            candles[when]=Decimal(str(b["c"]))
        if not candles:continue
        latest=max(candles)
        previous=latest-timedelta(minutes=15)
        if previous in candles and timedelta(0)<=now-(latest+timedelta(minutes=5))<=timedelta(minutes=10):
            observed[s]=(candles[previous],candles[latest])
            asof.append(latest+timedelta(minutes=5))
    return prior,observed,max(asof) if asof else None


def state_file():
    home=Path(os.environ.get("SEMIS_DOWNSIDE_V2_STATE_DIR",""))
    if not home.is_absolute() or home.is_symlink() or not home.is_dir() or home.stat().st_mode & 0o077:
        raise ValueError("private absolute state path required")
    file=home/"notifications.json"
    if file.is_symlink():raise ValueError("symlink state blocked")
    return file


def remember(file,key,status):
    data={}
    if file.exists():
        data=json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data,dict):raise ValueError("malformed notification state")
    data[key]=status
    data={k:v for k,v in data.items() if k[:10]>=(datetime.now(timezone.utc)-timedelta(days=14)).date().isoformat()}
    temp=file.parent/"notifications.new"
    temp.write_text(json.dumps(data,sort_keys=True),encoding="utf-8")
    os.chmod(temp,0o600)
    os.replace(temp,file)


def already_seen(file,key):
    if not file.exists():return False
    data=json.loads(file.read_text(encoding="utf-8"))
    return key in data


def push(title,message):
    user=creds("pushover_user")
    token=creds("pushover_token")
    payload=json.dumps({"user":user,"token":token,"title":title,
                        "message":message,"priority":0}).encode("utf-8")
    with urlopen(Request(PUSHOVER,data=payload,headers={
        "Content-Type":"application/json"},method="POST"),timeout=8) as res:
        reply=json.loads(res.read(10000))
        if res.status!=200 or reply.get("status")!=1:
            raise ValueError("notification acceptance not confirmed")


def run(now=None,send=False):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("aware datetime required")
    day,feed=session_and_feed(now)
    if day is None:return {"status":"SESSION_CLOSED","order_permissions":False}
    prior,observed,asof=market_snapshot(now,day,feed)
    risk=classify(prior,observed)
    if asof is None:return {"status":"NO_FRESH_BARS","order_permissions":False}
    status="SECTOR_SEVERE" if risk["sector_severe"] else (
        "STOCK_URGENT" if risk["stock_urgent"] else
        "DOWNSIDE_WATCH" if risk["sector_watch"] or risk["stock_watch"] else "NO_RISK_SIGNAL")
    event="sector_severe" if risk["sector_severe"] else (
        "stock_urgent" if risk["stock_urgent"] else
        "watch" if risk["sector_watch"] or risk["stock_watch"] else None)
    # This sidecar only PUSHES severe sector and urgent company symptoms.
    # Lesser watch observations are logged, not spammed to the user's phone.
    if send and event in ("sector_severe","stock_urgent"):
        file=state_file()
        key=day.isoformat()+":"+event
        if not already_seen(file,key):
            symbols=",".join(risk["stock_urgent"]) if risk["stock_urgent"] else "AMD/MU/SNDK,SOXX"
            now_ct=asof.astimezone(CT).strftime("%m/%d %I:%M %p CT")
            message=(f"EARLY DOWNSIDE WATCH {day.isoformat()} at {now_ct}. "
                     f"Observed selling pressure: {symbols}. "
                     "Possible additional downside; NOT a forecast of a 5% drop. "
                     "Review held positions, fresh quotes, and news before deciding to exit. "
                     "No broker orders placed.")
            # Reserve before HTTP to avoid repeat alerts on ambiguous response.
            remember(file,key,"SEND_ATTEMPTED_NOT_CONFIRMED")
            try:
                push("Semiconductor risk warning",message)
                remember(file,key,"PROVIDER_ACCEPTED_NOT_DELIVERED")
            except (OSError,ValueError,TimeoutError):
                return {"status":"DELIVERY_UNKNOWN_NO_RETRY","event":event,
                        "order_permissions":False}
    return {"status":status,"event":event,"session":day.isoformat(),
            "asof_utc":asof.astimezone(timezone.utc).isoformat(),
            "sector_severe":risk["sector_severe"],
            "stock_urgent":risk["stock_urgent"],
            "stock_watch":risk["stock_watch"],
            "order_permissions":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true",required=True)
    parser.add_argument("--send-pushover",action="store_true")
    args=parser.parse_args()
    try:
        print(json.dumps(run(send=args.send_pushover),sort_keys=True))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        print(json.dumps({"status":"DATA_OR_NOTIFIER_ERROR","order_permissions":False}))
