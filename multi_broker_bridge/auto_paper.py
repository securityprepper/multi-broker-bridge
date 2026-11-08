"""One-minute Alpaca PAPER strategy runner, triggered independently of the read-only observer.

Alpaca SIP/BOATS one-minute bars -> shared trend rules -> broker-paper LIMIT
orders. No LIVE host, Robinhood, short selling, additional exposure cap, or
automated retry on ambiguous broker submission.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from .models import LimitOrder, OrderRejected, UnknownSubmission
from .watchlists import SECTORS
from .trend import Bar, Holding, TrendMonitor, CHICAGO
from .alpaca import _http as paper_request

DATA_HOST = "https://data.alpaca.markets"
STATUS_URL = "https://securityprepper.com/.well-known/task-gate.json"
NY = ZoneInfo("America/New_York")
MAX_NOTIONAL = Decimal("2000")
MAX_SPREAD = Decimal("0.01")
MAX_QUOTE_AGE = timedelta(seconds=100)
STATE_SCHEMA = """CREATE TABLE IF NOT EXISTS attempts(
    trade_date TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
    client_id TEXT NOT NULL, state TEXT NOT NULL,
    PRIMARY KEY(trade_date,symbol,side));
CREATE TABLE IF NOT EXISTS tracked(
    symbol TEXT PRIMARY KEY, entry_ref TEXT NOT NULL,
    highest TEXT NOT NULL, entry_time TEXT NOT NULL);"""

def _credentials() -> tuple[str, str]:
    base = os.getenv("CREDENTIALS_DIRECTORY")
    if base:
        root = Path(base)
        key = (root / "alpaca_data_key_id").read_text().strip()
        secret = (root / "alpaca_data_secret").read_text().strip()
    else:
        key = os.getenv("ALPACA_PAPER_KEY_ID", "")
        secret = os.getenv("ALPACA_PAPER_SECRET_KEY", "")
    if not key or not secret:
        raise OrderRejected("Alpaca PAPER credentials unavailable")
    return key, secret

def _fetch_json(url: str, *, headers: dict, timeout: int = 9):
    if not (url.startswith(DATA_HOST + "/v2/stocks/") or url == STATUS_URL):
        raise OrderRejected("unexpected data/gate URL")
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout) as res:
            if res.status != 200:
                raise ValueError("data response not OK")
            body = res.read(3_000_001)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise ValueError("trusted data or schedule source unavailable") from exc
    if len(body) > 3_000_000:
        raise ValueError("data payload oversized")
    obj = json.loads(body)
    if not isinstance(obj, dict):
        raise ValueError("data payload not object")
    return obj

def trading_feed(now: datetime) -> str | None:
    local = now.astimezone(NY)
    wd = local.weekday()
    hour = local.hour
    if wd == 5 or (wd == 6 and hour < 20) or (wd == 4 and hour >= 20):
        return None
    return "boats" if hour >= 20 or hour < 4 else "sip"

def market_headers() -> dict:
    key, secret = _credentials()
    return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json"}

def holiday_gate(now: datetime) -> bool:
    # In the absence of an independently validated current holiday decision,
    # never open a new PAPER position. Existing position exits stay evaluated.
    payload = _fetch_json(STATUS_URL, headers={"Accept": "application/json"})
    if payload.get("schema_version") != 1 or payload.get("timezone") != "America/Chicago":
        return False
    if payload.get("status_valid") is not True or payload.get("calendar_coverage_ok") is not True:
        return False
    valid = datetime.fromisoformat(payload["valid_until"].replace("Z", "+00:00"))
    publish = datetime.fromisoformat(payload["published_at"].replace("Z", "+00:00"))
    if valid.tzinfo is None or publish.tzinfo is None:
        return False
    if not timedelta(0) <= now - publish <= timedelta(minutes=3) or now >= valid:
        return False
    return payload.get("paused") is False

def _batched(items: list[str], n: int = 20):
    for i in range(0, len(items), n):
        yield items[i:i+n]

def fetch_bars_and_quotes(now: datetime, symbols: list[str], feed: str):
    if feed not in ("sip", "boats"):
        raise ValueError("unsupported feed")
    end = now - timedelta(seconds=30)
    start = end - timedelta(minutes=12)
    headers = market_headers()
    bars = {}
    quotes = {}
    for batch in _batched(symbols):
        query = urlencode({"symbols": ",".join(batch), "timeframe": "1Min",
                           "start": start.isoformat(), "end": end.isoformat(),
                           "feed": feed, "limit": 10000, "sort": "asc"})
        payload = _fetch_json(DATA_HOST + "/v2/stocks/bars?" + query, headers=headers)
        if payload.get("next_page_token"):
            raise ValueError("incomplete minute-bar pagination")
        for symbol, rows in payload.get("bars", {}).items():
            if symbol not in batch or not isinstance(rows, list):
                raise ValueError("unexpected bar symbol/format")
            parsed = []
            for obj in rows:
                try:
                    ts = datetime.fromisoformat(obj["t"].replace("Z", "+00:00"))
                    if ts.tzinfo is None or not timedelta(0) <= now-ts <= timedelta(minutes=13):
                        continue
                    parsed.append(Bar(symbol, ts, Decimal(str(obj["h"])),
                                      Decimal(str(obj["l"])), Decimal(str(obj["c"]))))
                except (ValueError, TypeError, KeyError):
                    continue
            bars[symbol] = sorted(parsed, key=lambda x: x.timestamp)
        qparams = urlencode({"symbols": ",".join(batch), "feed": feed})
        quoted = _fetch_json(DATA_HOST + "/v2/stocks/quotes/latest?" + qparams,
                             headers=headers)
        for symbol, quote in quoted.get("quotes", {}).items():
            if symbol not in batch or not isinstance(quote, dict):
                raise ValueError("unexpected quote")
            try:
                quote_time = datetime.fromisoformat(quote["t"].replace("Z", "+00:00"))
                bid, ask = Decimal(str(quote["bp"])), Decimal(str(quote["ap"]))
                if quote_time.tzinfo is None or not timedelta(0) <= now-quote_time <= MAX_QUOTE_AGE:
                    continue
                if min(bid,ask) <= 0 or not bid.is_finite() or not ask.is_finite() or bid>ask:
                    continue
                if (ask-bid)/ask>MAX_SPREAD:
                    continue
                quotes[symbol] = (bid,ask)
            except (KeyError,TypeError,ValueError):
                continue
    return bars, quotes

def paper_api(method: str, path: str, body=None):
    # alpaca._http currently accepts only object responses. This endpoint
    # wrapper is used for array-valued positions/open orders as well.
    if not path.startswith("/v2/") or "://" in path or ".." in path:
        raise OrderRejected("bad paper endpoint")
    from .alpaca import _headers
    raw = None if body is None else json.dumps(body).encode("utf-8")
    req = Request("https://paper-api.alpaca.markets" + path,
                  headers=_headers(), data=raw, method=method)
    try:
        with urlopen(req, timeout=9) as response:
            status = response.status
            data = response.read(1_000_001)
    except HTTPError as exc:
        if exc.code in (400, 401, 403, 404, 422):
            raise OrderRejected("broker rejected request HTTP_" + str(exc.code)) from exc
        raise UnknownSubmission("uncertain broker HTTP response") from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise UnknownSubmission("broker transport unavailable; reconcile order first") from exc
    if status not in (200,201,204) or len(data)>1_000_000:
        raise UnknownSubmission("unexpected broker response")
    return json.loads(data) if data else {}

def _state():
    folder = Path(os.getenv("MULTI_BROKER_STATE_DIR", ""))
    if not folder.is_absolute() or not folder.exists() or folder.is_symlink():
        raise OrderRejected("private absolute state directory required")
    if folder.stat().st_uid != os.geteuid() or (folder.stat().st_mode & 0o077):
        raise OrderRejected("state directory must be private and owned by runner")
    path = folder / "strategy.sqlite3"
    if path.is_symlink() or (path.exists() and path.stat().st_mode & 0o077):
        raise OrderRejected("state database not private")
    previous = os.umask(0o077)
    try:
        db = sqlite3.connect(path, timeout=8)
    finally:
        os.umask(previous)
    db.executescript(STATE_SCHEMA)
    return db

def _reserve(db, date: str, symbol: str, side: str, ref: str):
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?)",
                   (date,symbol,side,ref,"UNKNOWN"))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False

def _record(db, date: str, symbol: str, side: str, state: str):
    db.execute("UPDATE attempts SET state=? WHERE trade_date=? AND symbol=? AND side=?",
               (state,date,symbol,side))
    db.commit()

def _unique_id(date: str, side: str, symbol: str) -> str:
    # Stable across restarts for a symbol and trade-date: no duplicate retry.
    return ("MBB-" + date.replace("-","") + "-" + side[:1].upper() + "-" + symbol)[:48]

def _active_orders(rows):
    return {x.get("symbol") for x in rows if isinstance(x,dict) and
            x.get("status") not in ("filled","canceled","expired","rejected","done_for_day")}

def run(now: datetime, execute: bool = False) -> dict:
    mode = "PAPER_EXECUTION" if execute else "SIMULATION"
    feed = trading_feed(now)
    if feed is None:
        return {"status":"SESSION_CLOSED","mode":mode,"orders":[]}
    account = paper_api("GET", "/v2/account")
    if account.get("status")!="ACTIVE" or account.get("trading_blocked") is not False or not account.get("id"):
        raise OrderRejected("PAPER account not verified for trading")
    positions = paper_api("GET", "/v2/positions")
    orders = paper_api("GET", "/v2/orders?status=open&limit=500")
    if not isinstance(positions,list) or not isinstance(orders,list):
        raise OrderRejected("broker position/order inventory incomplete")
    if len(orders)>=500:
        raise OrderRejected("open-order inventory truncated; no new orders")
    pos_by_symbol={p["symbol"]:p for p in positions if isinstance(p,dict) and p.get("symbol")}
    occupied=_active_orders(orders)
    symbols=list(dict.fromkeys(x for sector in SECTORS.values() for x in sector))
    # Cover tracked symbols even if universe changes after an entry.
    db=_state()
    try:
        tracked={row[0]:(row[1],Decimal(row[2])) for row in
                 db.execute("SELECT symbol,entry_ref,highest FROM tracked")}
        symbols=list(dict.fromkeys([*symbols,*tracked]))
        bars,quotes=fetch_bars_and_quotes(now,symbols,feed)
        engine=TrendMonitor()
        for symbol,records in bars.items():
            for bar in records:
                engine.add(bar)
        holdings={}
        for symbol,(entry_id,peak) in tracked.items():
            position=pos_by_symbol.get(symbol)
            if position is None:
                # If buy still open, do not mistake unfilled shares for a position.
                if symbol not in occupied:
                    db.execute("DELETE FROM tracked WHERE symbol=?",(symbol,))
                    db.commit()
                continue
            qty=Decimal(str(position.get("qty_available",position.get("qty",0))))
            entry=Decimal(str(position.get("avg_entry_price",0)))
            if position.get("side")!="long" or not qty.is_finite() or not entry.is_finite() or entry<=0:
                continue
            if qty==qty.to_integral_value() and qty>0:
                holdings[symbol]=Holding(symbol,int(qty),entry,max(peak,entry))
        result=engine.scan(now,holdings,executable_session=False)
        # A healthy scheduled exit is prioritized over new buys.
        decision=[r for r in result if r["action"] in ("EXIT_WATCH","BUY_WATCH")]
        decision.sort(key=lambda x:0 if x["action"]=="EXIT_WATCH" else 1)
        local_date=now.astimezone(NY).date().isoformat()
        placed=[]
        gate_ok=False
        try:
            gate_ok=holiday_gate(now)
        except (ValueError,KeyError,TypeError):
            gate_ok=False
        for row in decision:
            symbol=row["symbol"]
            prices=quotes.get(symbol)
            if not prices or symbol in occupied:
                continue
            bid,ask=prices
            if row["action"]=="BUY_WATCH":
                if not gate_ok or symbol in pos_by_symbol or symbol in tracked:
                    continue
                if now.astimezone(CHICAGO).time()>=__import__("datetime").time(13,30):
                    continue
                side="buy"
                price=ask.quantize(Decimal("0.01"),rounding="ROUND_UP")
                # One high-priced share, up to the buying-power-supported
                # whole-share quantity under $2k (not an account-level cap).
                quantity=1 if ask>=Decimal("750") else int(MAX_NOTIONAL//price)
                if quantity<1 or quantity*price>MAX_NOTIONAL:
                    continue
                available=Decimal(str(account.get("cash",0)))
                if not available.is_finite() or available<quantity*price:
                    continue
            else:
                if symbol not in holdings:
                    continue
                side="sell"
                price=bid.quantize(Decimal("0.01"),rounding=ROUND_DOWN)
                quantity=holdings[symbol].quantity
            ref=_unique_id(local_date,side,symbol)
            request=LimitOrder.make("alpaca",symbol,side,quantity,str(price),ref)
            # Exits of tracked PAPER positions could have appreciated above
            # $2000, but the public bridge intentionally enforces $2000 per
            # order: do not silently split or violate this contract.
            if not execute:
                placed.append({"symbol":symbol,"side":side,"qty":quantity,
                               "limit":str(price),"mode":"SIMULATION"})
                continue
            if os.getenv("MULTI_BROKER_ALLOW_PAPER")!="1":
                raise OrderRejected("PAPER execution gate disabled")
            if not _reserve(db,local_date,symbol,side,ref):
                continue
            payload={"symbol":symbol,"side":side,"qty":str(quantity),
                     "type":"limit","limit_price":str(price),
                     "time_in_force":"day","extended_hours":True,
                     "client_order_id":ref}
            try:
                receipt=paper_api("POST","/v2/orders",payload)
            except OrderRejected:
                _record(db,local_date,symbol,side,"REJECTED")
                placed.append({"symbol":symbol,"side":side,"status":"REJECTED"})
                continue
            # A timeout or unknown broker response leaves UNKNOWN without retry.
            if not isinstance(receipt,dict) or not receipt.get("id") or receipt.get("client_order_id")!=ref:
                raise UnknownSubmission("PAPER submission cannot be uniquely verified")
            _record(db,local_date,symbol,side,str(receipt.get("status","ACCEPTED")))
            if side=="buy":
                db.execute("INSERT OR REPLACE INTO tracked VALUES (?,?,?,?)",
                           (symbol,ref,str(price),now.isoformat()))
                db.commit()
            placed.append({"symbol":symbol,"side":side,"qty":quantity,
                           "status":receipt.get("status"),"broker_order_id":receipt["id"]})
            occupied.add(symbol)
            # Refresh broker cash/positions before sizing another stock.
            if side=="buy":
                account=paper_api("GET","/v2/account")
        return {"status":"SCAN_COMPLETE","mode":mode,"data_feed":feed,
                "gate_allows_new_entries":gate_ok,"candidate_count":len(decision),
                "orders":placed,"tracked":len(tracked)}
    finally:
        db.close()

def main(argv=None)->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true")
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args(argv)
    now=datetime.now(timezone.utc)
    try:
        result=run(now,execute=args.execute)
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"FAIL_CLOSED","error_type":type(exc).__name__,
                          "orders_may_require_broker_reconciliation":isinstance(exc,UnknownSubmission)}))
        return 2

if __name__=="__main__":
    sys.exit(main())
