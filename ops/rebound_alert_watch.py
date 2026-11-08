#!/usr/bin/env python3
"""Read-only five-minute monitor handoff for separately managed PAPER rebounds.

The monitor cannot submit orders. It reads a nonsecret atomic signal file,
deduplicates notifications, and uses its existing Pushover service credential.
Ambiguous HTTP delivery is never repeated automatically.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from alert_delivery import get_credentials
from holiday_gate import current_gate

UTC=dt.timezone.utc
HANDOFF=Path("/var/lib/sector-rebound-handoff/current.json")
DATABASE=Path("/var/lib/trading-sector-monitor/state.sqlite3")
HOLIDAY=Path("/var/lib/trading-sector-monitor/holiday_gate.json")
API="https://api.pushover.net/1/messages.json"


def _datetime(value):
    when=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if when.tzinfo is None:raise ValueError("timestamp timezone required")
    return when.astimezone(UTC)


def run(now=None,send=True):
    now=(now or dt.datetime.now(UTC)).astimezone(UTC)
    if not HANDOFF.is_file() or HANDOFF.is_symlink() or HANDOFF.stat().st_size>4096:
        return {"status":"NO_TRUSTED_REBOUND_SIGNAL"}
    signal=json.loads(HANDOFF.read_text(encoding="utf-8"))
    if signal.get("schema_version")!=1 or signal.get("strategy")!="five_day_rebound" or signal.get("kind")!="BULLISH_SIGNAL":
        return {"status":"UNEXPECTED_SIGNAL_SCHEMA"}
    issued=_datetime(signal.get("issued_at_utc"))
    signal_time=_datetime(signal.get("signal_at_utc"))
    if not dt.timedelta(0)<=now-issued<=dt.timedelta(minutes=12) or signal_time>issued+dt.timedelta(minutes=1):
        return {"status":"STALE_OR_FUTURE_REBOUND_SIGNAL"}
    day=signal.get("trading_day")
    if not isinstance(day,str) or len(day)!=10:
        return {"status":"MALFORMED_TRADING_DAY"}
    gate,_=current_gate(HOLIDAY,now)
    if not gate or gate.get("paused") is not False:
        return {"status":"HOLIDAY_GATE_UNVERIFIED"}
    creds_dir=os.getenv("CREDENTIALS_DIRECTORY")
    creds=get_credentials(Path(creds_dir)) if creds_dir else None
    if not creds:
        return {"status":"PUSHOVER_CREDENTIALS_UNAVAILABLE"}
    key="FDR:"+day+":"+signal_time.isoformat()
    with sqlite3.connect(DATABASE,timeout=8,isolation_level=None) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS rebound_alert_delivery ("
                     "event_key TEXT PRIMARY KEY, state TEXT NOT NULL,"
                     "reserved_at TEXT NOT NULL, completed_at TEXT)")
        conn.execute("BEGIN IMMEDIATE")
        existing=conn.execute("SELECT state FROM rebound_alert_delivery WHERE event_key=?",(key,)).fetchone()
        if existing:
            conn.execute("COMMIT")
            return {"status":"ALREADY_NOTIFIED_OR_RESERVED","delivery_state":existing[0]}
        if send:
            conn.execute("INSERT INTO rebound_alert_delivery VALUES(?,?,?,NULL)",
                         (key,"SENDING",now.isoformat()))
        conn.execute("COMMIT")
    if not send:return {"status":"WOULD_NOTIFY","strategy":"five_day_rebound"}
    user,token=creds
    text=("Semiconductor bullish rebound: previous 5 completed trading days DOWN; "
          "new breadth, momentum and breakout confirmed for "+day+". "
          "Dedicated Alpaca PAPER executor may attempt limit buys. "
          "SIGNAL ONLY: do not treat as broker-filled purchase. "
          "Follow-up ChatGPT alert task reconciles accepted orders and fills.")
    req=Request(API,data=json.dumps({"token":token,"user":user,
               "device":"IlanPhone","title":"PAPER rebound BUY signal",
               "message":text,"priority":0}).encode("utf-8"),
               headers={"Content-Type":"application/json","Accept":"application/json"},
               method="POST")
    try:
        with urlopen(req,timeout=6) as reply:
            body=json.loads(reply.read(4096))
            if reply.status!=200 or body.get("status")!=1:raise RuntimeError("provider did not accept")
        status="PROVIDER_ACCEPTED"
    except (HTTPError,URLError,TimeoutError,RuntimeError,OSError,ValueError):
        status="DELIVERY_UNKNOWN_NO_AUTO_RETRY"
    with sqlite3.connect(DATABASE,timeout=8) as conn:
        conn.execute("UPDATE rebound_alert_delivery SET state=?,completed_at=? WHERE event_key=? AND state='SENDING'",
                     (status,dt.datetime.now(UTC).isoformat(),key))
        conn.commit()
    return {"status":status,"strategy":"five_day_rebound","trading_day":day}


if __name__=="__main__":
    try:
        print(json.dumps(run(),sort_keys=True))
    except (OSError,sqlite3.Error,ValueError,TypeError,KeyError):
        print(json.dumps({"status":"REBOUND_ALERT_READ_FAILED","broker_order_access":False}))
    sys.exit(0)  # This observer must never prevent the existing sector monitor's success handoff.
