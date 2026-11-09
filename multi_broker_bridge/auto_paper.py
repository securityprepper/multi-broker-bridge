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
from .premarket_policy import (
    is_early_market,premarket_sell_decision,eligible_discount_reentry,
    sustained_trend_shape,recent_price_spike,trading_session_day,
    quoted_return,EMERGENCY_LOSS,peak_trail_percent
)
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
    highest TEXT NOT NULL, entry_time TEXT NOT NULL,
    entry_qty INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS premarket_steady_flags(
    trading_session TEXT NOT NULL, symbol TEXT NOT NULL,
    confirmed_at TEXT NOT NULL, PRIMARY KEY(trading_session,symbol));"""

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
    start = end - timedelta(minutes=47)  # allow 45m distribution/spike comparison
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
                    if (ts.tzinfo is None or ts+timedelta(minutes=1)>now
                        or not timedelta(0)<=now-ts<=timedelta(minutes=48)
                        or int(obj["v"])<=0):
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
    key, secret = _credentials()
    raw = None if body is None else json.dumps(body).encode("utf-8")
    headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,
             "Accept":"application/json","Content-Type":"application/json"}
    req = Request("https://paper-api.alpaca.markets" + path,
                  headers=headers, data=raw, method=method)
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

def _verified_cheaper_reentry(
    db,now:datetime,symbol:str,tracked:dict,
    next_ask:Decimal,occupied:set,positions:dict
)->bool:
    """Broker-verified filled profitable premarket exit, then cheaper new ask.

    One controlled subsequent attempt, only after a new independent
    rising-sector BUY_WATCH. Caller must independently validate its
    holiday gate, quote freshness, available CASH and per-order exposure.
    """
    if (symbol not in tracked or symbol in positions or symbol in occupied
        or now.astimezone(CHICAGO).time() >=
           __import__("datetime").time(10,0)):
        return False
    entry_ref,_,_,initial_qty=tracked[symbol]
    d=now.astimezone(NY).date()
    date_candidates=(d.isoformat(),(d-timedelta(days=1)).isoformat())
    matches=list(db.execute(
        "SELECT trade_date,client_id FROM attempts WHERE symbol=? "
        "AND side='sell' AND trade_date IN (?,?) ORDER BY trade_date DESC",
        (symbol,*date_candidates)
    ))
    if not matches:return False
    reentries=db.execute(
        "SELECT COUNT(*) FROM attempts WHERE symbol=? AND side='reentry' "
        "AND trade_date IN (?,?)", (symbol,*date_candidates)
    ).fetchone()[0]
    if reentries:
        return False
    from urllib.parse import quote
    for date,client_id in matches:
        if not str(client_id).startswith("MBB-"):
            continue
        try:
            sell=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+
                           quote(client_id,safe=""))
            prior=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+
                           quote(entry_ref,safe=""))
            if (not isinstance(sell,dict) or not isinstance(prior,dict)
                or sell.get("client_order_id")!=client_id
                or prior.get("client_order_id")!=entry_ref
                or sell.get("symbol")!=symbol or prior.get("symbol")!=symbol
                or sell.get("side")!="sell" or prior.get("side")!="buy"
                or sell.get("status")!="filled" or prior.get("status")!="filled"
                or not sell.get("filled_at")):
                continue
            sell_qty=Decimal(str(sell["filled_qty"]))
            buy_qty=Decimal(str(prior["filled_qty"]))
            if not (sell_qty==buy_qty==Decimal(initial_qty)):
                continue
            sale=Decimal(str(sell["filled_avg_price"]))
            buy=Decimal(str(prior["filled_avg_price"]))
            sold_at=datetime.fromisoformat(sell["filled_at"].replace("Z","+00:00"))
            if eligible_discount_reentry(
                now,sell_filled_at=sold_at,sell_filled_price=sale,
                entry_filled_price=buy,next_verified_ask=next_ask,
                fully_filled=True,actual_rising_breadth=True,
                positions_absent=True,pending_orders_absent=True,
                already_reentered=False):
                return True
        except (OrderRejected,UnknownSubmission,ValueError,TypeError,KeyError,
                ArithmeticError):
            continue
    return False


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
        # The 13:40 CT PAPER liquidation has priority over signal scans.
        # It queries broker positions/orders and the broker's open clock;
        # it does not depend on premium minute-bar delivery or fresh quotes.
        from .paper_time_exit import timed_flatten
        mandatory_exit=timed_flatten(now,positions,orders,db,paper_api)
        if mandatory_exit is not None:
            return {
                "status":"PAPER_DAILY_EXIT_GUARD",
                "mode":mode,"data_feed":feed,
                "gate_allows_new_entries":False,
                "orders":mandatory_exit["actions"],
                "exit_guard":mandatory_exit,
            }
        tracked={row[0]:(row[1],Decimal(row[2]),
                         datetime.fromisoformat(row[3]),int(row[4])) for row in
                 db.execute("SELECT symbol,entry_ref,highest,entry_time,entry_qty FROM tracked")}
        symbols=list(dict.fromkeys([*symbols,*tracked]))
        bars,quotes=fetch_bars_and_quotes(now,symbols,feed)
        engine=TrendMonitor()
        for symbol,records in bars.items():
            for bar in records:
                engine.add(bar)
        holdings={}
        for symbol,(entry_id,peak,entry_time,entry_qty) in tracked.items():
            position=pos_by_symbol.get(symbol)
            if position is None:
                # Broker positions may lag newly accepted orders. Never drop
                # tracking merely because an open-order snapshot is empty.
                # Only terminal broker readback with ZERO fills can clear it.
                if symbol not in occupied:
                    try:
                        from urllib.parse import quote
                        status=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="
                                          +quote(entry_id,safe=""))
                        if (isinstance(status,dict)
                                and status.get("client_order_id")==entry_id
                                and status.get("status") in ("canceled","expired","rejected")
                                and Decimal(str(status.get("filled_qty",0)))==0):
                            db.execute("DELETE FROM tracked WHERE symbol=?",(symbol,))
                            db.commit()
                    except (OrderRejected,UnknownSubmission,ValueError,TypeError):
                        pass  # never infer missing holdings are proof of flatness
                continue
            qty=Decimal(str(position.get("qty_available",position.get("qty",0))))
            entry=Decimal(str(position.get("avg_entry_price",0)))
            if position.get("side")!="long" or not qty.is_finite() or not entry.is_finite() or entry<=0:
                continue
            if qty==qty.to_integral_value() and qty>0:
                observed=max((bar.high for bar in bars.get(symbol,[])
                              if bar.timestamp>=entry_time),default=entry)
                updated_peak=max(peak,entry,observed)
                if updated_peak>peak:
                    db.execute("UPDATE tracked SET highest=? WHERE symbol=?",
                               (str(updated_peak),symbol))
                    db.commit()
                holdings[symbol]=Holding(symbol,min(int(qty),entry_qty),entry,updated_peak)
        steady_symbols=set()
        if is_early_market(now):
            # Persist a confirmed distributed-rise *once* so a 20-minute
            # routine shakeout does not suddenly narrow a 2.5% trailing
            # threshold to 2%. Never infer from an incomplete minute.
            session_date=trading_session_day(now).isoformat()
            for symbol in holdings:
                if sustained_trend_shape(bars.get(symbol,[]),now):
                    db.execute(
                        "INSERT OR IGNORE INTO premarket_steady_flags "
                        "(trading_session,symbol,confirmed_at) VALUES(?,?,?)",
                        (session_date,symbol,now.isoformat()))
            db.commit()
            steady_symbols={
                sym for (sym,) in db.execute(
                    "SELECT symbol FROM premarket_steady_flags "
                    "WHERE trading_session=?",(session_date,)).fetchall()
                if sym in holdings
            }
        # A sudden one-minute discontinuity outranks the persistent steady
        # classification for the next 12 minutes, allowing profit-taking
        # if a genuine spike reverses. Ordinary dips cannot erase the
        # previously confirmed uptrend.
        spike_symbols=(
            {sym for sym in holdings if recent_price_spike(bars.get(sym,[]),now)}
            if is_early_market(now) else set())
        effective_steady=steady_symbols-spike_symbols
        result=engine.scan(now,holdings,executable_session=False,
                           steady_uptrend_symbols=effective_steady)
        # A verified executable bid may cross the risk threshold before
        # the latest completed one-minute CLOSE. Software exits should
        # not wait for a bar if a fresh broker-data quote proves the breach.
        if is_early_market(now):
            for sym,position in holdings.items():
                if sym not in quotes:
                    continue
                bid=quotes[sym][0]
                distance=peak_trail_percent(
                    steady_confirmed=sym in effective_steady)
                falling_from_peak=(bid/position.highest_since_entry-1)
                falling_from_entry=quoted_return(position.entry_price,bid)
                if falling_from_entry<=EMERGENCY_LOSS:
                    reason="premarket emergency downside exit"
                elif falling_from_peak<=-distance:
                    reason=("premarket steady peak trailing stop"
                            if sym in effective_steady else
                            "premarket standard peak trailing stop")
                else:
                    continue
                if not any(r.get("symbol")==sym and r.get("action")=="EXIT_WATCH"
                           for r in result):
                    result.append({"symbol":sym,"action":"EXIT_WATCH",
                                   "quantity":position.quantity,
                                   "reason":reason,
                                   "reference_bid":str(bid)})
        # A healthy scheduled exit is prioritized over new buys.
        decision=[r for r in result if r["action"] in ("EXIT_WATCH","BUY_WATCH")]
        decision.sort(key=lambda x:0 if x["action"]=="EXIT_WATCH" else 1)
        local_date=now.astimezone(NY).date().isoformat()
        placed=[]
        # Diagnostic-only evidence for the next missed-entry review.
        # Never log API keys, broker account ID, cash amounts or source quotes.
        skipped_entries=[]
        def note_skip(sym:str,reason:str):
            if len(skipped_entries)<48:
                skipped_entries.append({"symbol":sym,"reason":reason})
        # Retire only the strategy's old BUY orders; preserve all manual orders.
        # A cancel request is NOT proof of cancellation: on this scan, the
        # symbol remains occupied until a fresh broker readback next tick.
        for old in orders:
            if not isinstance(old,dict) or old.get("side")!="buy":
                continue
            if not str(old.get("client_order_id","")).startswith("MBB-"):
                continue
            oid=old.get("id")
            if not isinstance(oid,str) or not oid:
                continue
            try:
                created=datetime.fromisoformat(str(old["created_at"]).replace("Z","+00:00"))
                age=now-created
            except (KeyError,ValueError,TypeError):
                continue
            if age>=timedelta(minutes=2) and execute:
                try:
                    paper_api("DELETE","/v2/orders/"+oid)
                    placed.append({"symbol":old.get("symbol"),
                                   "action":"CANCEL_STALE_BUY","status":"CANCEL_REQUESTED"})
                except (OrderRejected,UnknownSubmission):
                    placed.append({"symbol":old.get("symbol"),
                                   "action":"CANCEL_STALE_BUY","status":"CANCEL_UNVERIFIED"})
        # At 13:55 Central, cancel prior pending exits (if any). Do not
        # replace them with a market order until the next verified broker
        # snapshot confirms cancellation.
        local_time=now.astimezone(CHICAGO).time()
        if local_time>=__import__("datetime").time(13,55) and execute:
            for old in orders:
                if not isinstance(old,dict) or old.get("side")!="sell":
                    continue
                if not str(old.get("client_order_id","")).startswith("MBB-"):
                    continue
                oid=old.get("id")
                if not isinstance(oid,str) or not oid:
                    continue
                try:
                    paper_api("DELETE","/v2/orders/"+oid)
                    placed.append({"symbol":old.get("symbol"),
                                   "action":"CANCEL_PENDING_EXIT_FOR_FLATTEN",
                                   "status":"CANCEL_REQUESTED"})
                except (OrderRejected,UnknownSubmission):
                    placed.append({"symbol":old.get("symbol"),
                                   "action":"CANCEL_PENDING_EXIT_FOR_FLATTEN",
                                   "status":"CANCEL_UNVERIFIED"})
        gate_ok=False
        try:
            gate_ok=holiday_gate(now)
        except (ValueError,KeyError,TypeError):
            gate_ok=False
        for row in decision:
            symbol=row["symbol"]
            prices=quotes.get(symbol)
            if not prices:
                if row["action"]=="BUY_WATCH":note_skip(symbol,"NO_FRESH_BID_ASK")
                continue
            if symbol in occupied:
                if row["action"]=="BUY_WATCH":note_skip(symbol,"BROKER_ORDER_ALREADY_OPEN")
                continue
            bid,ask=prices
            if row["action"]=="BUY_WATCH":
                if not gate_ok:
                    note_skip(symbol,"HOLIDAY_GATE_BLOCKED")
                    continue
                if symbol in pos_by_symbol:
                    note_skip(symbol,"EXISTING_BROKER_POSITION")
                    continue
                if now.astimezone(CHICAGO).time()>=__import__("datetime").time(13,15):
                    note_skip(symbol,"AFTER_ENTRY_CUTOFF")
                    continue
                # A second entry is exceptional: the first complete premarket
                # sell must have BANKED >=2% and the next true ask must be
                # at least 0.25% lower, plus a FRESH BUY_WATCH.
                # No uncontrolled re-buy at a higher price on AMD-like days.
                reentry=False
                if symbol in tracked:
                    reentry=_verified_cheaper_reentry(
                        db,now,symbol,tracked,ask,occupied,pos_by_symbol)
                    if not reentry:
                        note_skip(symbol,"PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")
                        continue
                side="buy"
                price=ask.quantize(Decimal("0.01"),rounding="ROUND_UP")
                # One high-priced share, up to the buying-power-supported
                # whole-share quantity under $2k (not an account-level cap).
                quantity=1 if ask>=Decimal("750") else int(MAX_NOTIONAL//price)
                if quantity<1 or quantity*price>MAX_NOTIONAL:
                    note_skip(symbol,"PER_ORDER_NOTIONAL_CAP")
                    continue
                available=Decimal(str(account.get("cash",0)))
                if not available.is_finite() or available<quantity*price:
                    note_skip(symbol,"PAPER_CASH_INSUFFICIENT")
                    continue
            else:
                if symbol not in holdings:
                    continue
                if is_early_market(now):
                    early=premarket_sell_decision(
                        now,holdings[symbol].entry_price,bid,
                        str(row.get("reason","")),
                        peak=holdings[symbol].highest_since_entry,
                        steady_confirmed=symbol in effective_steady)
                    if early not in ("SUBSTANTIAL_PROFIT_TAKE",
                                     "EMERGENCY_DOWNSIDE_EXIT",
                                     "TRAILING_STOP_SOFTWARE"):
                        continue
                side="sell"
                price=bid.quantize(Decimal("0.01"),rounding=ROUND_DOWN)
                quantity=holdings[symbol].quantity
            urgent_flatten=(side=="sell" and
                now.astimezone(CHICAGO).time()>=__import__("datetime").time(13,55)
                and now.astimezone(CHICAGO).time()<__import__("datetime").time(15,0)
                and now.astimezone(CHICAGO).weekday()<5)
            reservation_side=("flatten" if urgent_flatten else
                              "reentry" if side=="buy" and reentry else side)
            ref=_unique_id(local_date,reservation_side,symbol)
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
            if not _reserve(db,local_date,symbol,reservation_side,ref):
                continue
            payload={"symbol":symbol,"side":side,"qty":str(quantity),
                     "type":"market" if urgent_flatten else "limit",
                     "time_in_force":"day","extended_hours":not urgent_flatten,
                     "client_order_id":ref}
            if not urgent_flatten:
                payload["limit_price"]=str(price)
            try:
                receipt=paper_api("POST","/v2/orders",payload)
            except OrderRejected:
                _record(db,local_date,symbol,reservation_side,"REJECTED")
                placed.append({"symbol":symbol,"side":side,"status":"REJECTED"})
                continue
            # A timeout or unknown broker response leaves UNKNOWN without retry.
            if not isinstance(receipt,dict) or not receipt.get("id") or receipt.get("client_order_id")!=ref:
                raise UnknownSubmission("PAPER submission cannot be uniquely verified")
            _record(db,local_date,symbol,reservation_side,str(receipt.get("status","ACCEPTED")))
            if side=="buy":
                db.execute("INSERT OR REPLACE INTO tracked VALUES (?,?,?,?,?)",
                           (symbol,ref,str(price),now.isoformat(),quantity))
                db.commit()
            placed.append({"symbol":symbol,"side":side,"qty":quantity,
                           "status":receipt.get("status"),"broker_order_id":receipt["id"]})
            occupied.add(symbol)
            # Refresh broker cash/positions before sizing another stock.
            if side=="buy":
                account=paper_api("GET","/v2/account")
        return {"status":"SCAN_COMPLETE","mode":mode,"data_feed":feed,
                "established_premarket_uptrends":sorted(steady_symbols),
                "premarket_rapid_spike_names":sorted(spike_symbols),
                "premarket_effective_steady_names":sorted(effective_steady),
                "gate_allows_new_entries":gate_ok,"candidate_count":len(decision),
                "orders":placed,"tracked":len(tracked),
                "buy_watch_symbols":[r["symbol"] for r in decision
                                     if r["action"]=="BUY_WATCH"][:48],
                "skipped_buy_reasons":skipped_entries}
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
