"""Five-day semiconductor rebound — separate, PAPER-only Alpaca runner.

No LIVE routing. Uses separately tagged orders and its own private state.
The generic PAPER sector runner is not modified. Requires verified broker
inventory; never assumes order acceptance means a fill. Time-based exit
attempts continue even if signals, data or the holiday gate are unavailable.

Run with --once for read-only evaluation, or --once --execute to permit
verified PAPER orders. Enable only with systemd credential and state guards.
"""
from __future__ import annotations
import argparse
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from .auto_paper import (
    _credentials, _fetch_json, market_headers, paper_api,
    holiday_gate, trading_feed, OrderRejected, UnknownSubmission,
    DATA_HOST
)
from .five_day_rebound import Candle, SYMBOLS, ANCHORS, evaluate
from .rebound_catalysts import screen as screen_adverse_catalysts

ET=ZoneInfo("America/New_York")
BASKET=("AMD","MU","SNDK","SOXX","NVDA","AVGO","WDC","TSM","INTC")
STATE_PREFIX="FDR-"
MAX_ORDER_USD=Decimal("2000")
MAX_TOTAL_USD=Decimal("18000")
MAX_QUOTE_SPREAD=Decimal(".003")
FIRST_ENTRY=time(16,0)
LAST_ENTRY=time(8,15)
FIRST_EXIT=time(8,30)
LAST_PREOPEN=time(9,25)
LAST_EXIT=time(15,50)  # RTH emergency fallback when premarket limit cannot be verified
ALERT_NAME="five_day_rebound"


def _next_session(now: datetime):
    local=now.astimezone(ET)
    wd=local.weekday()
    if wd==5 or (wd==6 and local.time()<time(20)):return None
    if wd==4 and local.time()>=time(16):return None
    if wd==6:return local.date()+timedelta(days=1)
    if local.time()>=time(16):
        nxt=local.date()+timedelta(days=1)
        if nxt.weekday()>=5:return None
        return nxt
    return local.date()


def _entering_window(now):
    local=now.astimezone(ET)
    if local.weekday()<5 and time(16)<=local.time()<time(20) and local.weekday()!=4:return True
    if (local.weekday()==6 or local.weekday()<5) and (
        local.time()>=time(20) or local.time()<LAST_ENTRY
    ):
        return not (local.weekday()==4 and local.time()>=time(20))
    return False


def _fetch_daily(now, session_date):
    """Six completed trading closes, with daily split-adjusted OHLC data."""
    start=(now-timedelta(days=25)).astimezone(timezone.utc)
    end=(now+timedelta(minutes=1)).astimezone(timezone.utc)
    query=urlencode({"symbols":",".join(SYMBOLS),"timeframe":"1Day",
                     "start":start.isoformat(),"end":end.isoformat(),
                     "feed":"sip","adjustment":"split","limit":10000})
    body=_fetch_json(DATA_HOST+"/v2/stocks/bars?"+query,headers=market_headers())
    if body.get("next_page_token"):raise OrderRejected("incomplete historical daily pagination")
    rows=body.get("bars",{})
    close={}
    expected_dates=None
    for s in SYMBOLS:
        seq=rows.get(s)
        if not isinstance(seq,list):raise OrderRejected("missing prior daily bars: "+s)
        days={}
        for row in seq:
            date=str(row["t"])[:10]
            if date>=session_date.isoformat():continue
            days[date]=Decimal(str(row["c"]))
        keys=sorted(days)[-6:]
        if len(keys)!=6:raise OrderRejected("insufficient completed prior daily closes")
        if expected_dates is not None and keys!=expected_dates:
            raise OrderRejected("misaligned completed sector daily history")
        expected_dates=keys
        close[s]=[days[d] for d in keys]
    return close


def _fetch_sector_bars(now):
    feed=trading_feed(now)
    if feed is None:return None
    end=now-timedelta(seconds=15)
    start=end-timedelta(minutes=35)
    query=urlencode({"symbols":",".join(SYMBOLS),"timeframe":"5Min",
                     "start":start.isoformat(),"end":end.isoformat(),
                     "feed":feed,"adjustment":"split","limit":10000,"sort":"asc"})
    body=_fetch_json(DATA_HOST+"/v2/stocks/bars?"+query,headers=market_headers())
    if body.get("next_page_token"):raise OrderRejected("incomplete sector bar pagination")
    result={}
    for s in SYMBOLS:
        vals=[]
        for obj in body.get("bars",{}).get(s,[]):
            when=datetime.fromisoformat(obj["t"].replace("Z","+00:00"))
            if when.tzinfo is None or when+timedelta(minutes=5)>now-timedelta(seconds=15):
                continue
            vals.append(Candle(when,Decimal(str(obj["h"])),Decimal(str(obj["c"]))))
        result[s]=sorted(vals,key=lambda x:x.timestamp)
    return result


def _quotes(now):
    feed=trading_feed(now)
    if feed is None:return {}
    query=urlencode({"symbols":",".join(BASKET),"feed":feed})
    body=_fetch_json(DATA_HOST+"/v2/stocks/quotes/latest?"+query,headers=market_headers())
    result={}
    for s,q in body.get("quotes",{}).items():
        if s not in BASKET:continue
        try:
            ts=datetime.fromisoformat(q["t"].replace("Z","+00:00"))
            bid,ask=Decimal(str(q["bp"])),Decimal(str(q["ap"]))
            if not (bid.is_finite() and ask.is_finite() and 0<bid<=ask):continue
            if not timedelta(seconds=0)<=now-ts<=timedelta(seconds=75):continue
            if (ask-bid)/ask>MAX_QUOTE_SPREAD:continue
            result[s]=(bid,ask)
        except (KeyError,ValueError,TypeError):continue
    return result


def _db():
    state=Path(os.getenv("MULTI_BROKER_REBOUND_STATE_DIR",""))
    if not state.is_absolute() or not state.is_dir() or state.is_symlink():
        raise OrderRejected("private absolute rebound state directory required")
    if state.stat().st_uid!=os.geteuid() or state.stat().st_mode & 0o077:
        raise OrderRejected("rebound state path owner/mode unsafe")
    path=state/"rebound.sqlite3"
    if path.is_symlink() or path.exists() and path.stat().st_mode & 0o077:
        raise OrderRejected("unsafe state database")
    old=os.umask(0o077)
    try:
        conn=sqlite3.connect(path,timeout=6)
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS attempts(
          trading_day TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
          count INTEGER NOT NULL, client_id TEXT NOT NULL, state TEXT NOT NULL,
          PRIMARY KEY(trading_day,symbol,side,count));
        CREATE TABLE IF NOT EXISTS owned(
          trading_day TEXT NOT NULL, symbol TEXT PRIMARY KEY,
          buy_client_id TEXT NOT NULL, purchased_qty INTEGER NOT NULL,
          status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, time_utc TEXT NOT NULL,
          trading_day TEXT NOT NULL, type TEXT NOT NULL, symbol TEXT,
          details TEXT NOT NULL);
        """)
        conn.commit()
        return conn
    finally:
        os.umask(old)


def _event(conn,now,day,kind,symbol="",details=""):
    conn.execute("INSERT INTO events(time_utc,trading_day,type,symbol,details) VALUES(?,?,?,?,?)",
                 (now.isoformat(),day,kind,symbol,details[:1000]))
    conn.commit()


def _reserve(conn,day,symbol,side):
    # Stable client order ID for an individual attempt. Reserve *before* POST.
    count=conn.execute("SELECT COALESCE(MAX(count),0)+1 FROM attempts WHERE trading_day=? AND symbol=? AND side=?",
                       (day,symbol,side)).fetchone()[0]
    client=f"FDR-{day.replace('-','')}-{side[0].upper()}-{symbol}-{count}"
    conn.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?)",
                 (day,symbol,side,count,client,"UNKNOWN"))
    conn.commit()
    return client


def _mark(conn,client,status):
    conn.execute("UPDATE attempts SET state=? WHERE client_id=?",(status,client))
    conn.commit()


def _broker_inventory():
    acct=paper_api("GET","/v2/account")
    if not isinstance(acct,dict) or acct.get("status")!="ACTIVE" or acct.get("trading_blocked") is not False:
        raise OrderRejected("PAPER account not tradeable")
    pos=paper_api("GET","/v2/positions")
    orders=paper_api("GET","/v2/orders?status=open&limit=500")
    if not isinstance(pos,list) or not isinstance(orders,list) or len(orders)>=500:
        raise OrderRejected("broker account inventory missing or truncated")
    return acct,pos,orders


def _open_orders(orders,symbol):
    return [o for o in orders if isinstance(o,dict) and o.get("symbol")==symbol
            and o.get("status") not in ("filled","canceled","expired","rejected","done_for_day")]


def _cancel_open(conn,now,day,orders,symbol):
    relevant=[o for o in _open_orders(orders,symbol)
              if str(o.get("client_order_id","")).startswith(STATE_PREFIX)]
    for order in relevant:
        oid=order.get("id")
        if not isinstance(oid,str) or not oid:raise OrderRejected("missing broker order ID")
        paper_api("DELETE","/v2/orders/"+quote(oid,safe=""))
        _event(conn,now,day,"CANCEL_REQUESTED",symbol,str(order.get("client_order_id","")))
    return bool(relevant)


def _submit(conn,now,day,symbol,side,qty,limit=None,market=False):
    ref=_reserve(conn,day,symbol,"exit" if side=="sell" else "buy")
    payload={"symbol":symbol,"side":side,"qty":str(qty),
             "type":"market" if market else "limit",
             "time_in_force":"day","extended_hours":not market,
             "client_order_id":ref}
    if not market:payload["limit_price"]=str(limit)
    try:
        receipt=paper_api("POST","/v2/orders",payload)
    except OrderRejected:
        _mark(conn,ref,"REJECTED")
        _event(conn,now,day,"ORDER_REJECTED",symbol,side)
        return None
    # Unknown response deliberately preserves reserved UNKNOWN, no duplicate retries.
    if not isinstance(receipt,dict) or receipt.get("client_order_id")!=ref or not receipt.get("id"):
        raise UnknownSubmission("new order receipt could not be verified")
    _mark(conn,ref,str(receipt.get("status","ACCEPTED")))
    _event(conn,now,day,"ORDER_ACCEPTED_NOT_FILLED",symbol,side+" "+str(qty)+" "+str(limit))
    return ref



def _archive_completed(conn,now,today,managed,bypos,orders):
    """Release next-session eligibility only after exact broker readback.

    A missing broker position alone cannot establish an old order finished.
    Entry with no fill must be terminal. Filled entry must be matched by
    broker-confirmed exit quantities and no currently held/open shares.
    """
    removed=[]
    for symbol,(old_day,entry_qty,buy_id,state) in managed.items():
        if old_day>=today or symbol in bypos or _open_orders(orders,symbol):
            continue
        try:
            entry=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+quote(buy_id,safe=""))
            if not isinstance(entry,dict) or entry.get("client_order_id")!=buy_id:
                continue
            quantity=Decimal(str(entry.get("filled_qty",0)))
            if not quantity.is_finite() or quantity<0 or quantity>entry_qty:
                continue
            if quantity==0:
                ready=entry.get("status") in ("canceled","expired","rejected","done_for_day")
            else:
                exits=conn.execute(
                    "SELECT client_id FROM attempts WHERE trading_day=? AND symbol=? AND side='exit'",
                    (old_day,symbol)).fetchall()
                covered=Decimal("0")
                for (cid,) in exits:
                    receipt=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+quote(cid,safe=""))
                    if not isinstance(receipt,dict) or receipt.get("client_order_id")!=cid:
                        continue
                    if receipt.get("side")=="sell":
                        covered+=Decimal(str(receipt.get("filled_qty",0)))
                ready=covered>=quantity
            if ready:
                conn.execute("DELETE FROM owned WHERE symbol=? AND trading_day=?",(symbol,old_day))
                conn.commit()
                _event(conn,now,today,"PREVIOUS_PAPER_POSITION_RECONCILED",symbol,old_day)
                removed.append(symbol)
        except (OrderRejected,UnknownSubmission,ValueError,TypeError,KeyError):
            pass  # any uncertain state remains blocked
    return removed




def _fetch_causal_news(asof:datetime):
    """Fetch news that existed by the completed signal candle's end.

    Page through the full 24-hour query. Network or pagination failure blocks
    NEW PAPER purchases, never pending exit management.
    """
    end=asof.astimezone(timezone.utc)
    begin=end-timedelta(hours=24)
    params={"symbols":",".join(ANCHORS),"start":begin.isoformat(),
            "end":end.isoformat(),"limit":50,"sort":"asc"}
    rows=[]
    token=None
    for page in range(15):
        q=dict(params)
        if token:q["page_token"]=token
        uri="https://data.alpaca.markets/v1beta1/news?"+urlencode(q)
        try:
            with urlopen(Request(uri,headers=market_headers(),method="GET"),timeout=7) as response:
                if response.status!=200:raise OrderRejected("news provider returned non-200")
                payload=json.loads(response.read(1_000_001))
        except (HTTPError,URLError,OSError,TimeoutError,ValueError) as exc:
            raise OrderRejected("historical catalyst news unavailable") from exc
        if not isinstance(payload,dict) or not isinstance(payload.get("news"),list):
            raise OrderRejected("news payload malformed")
        rows.extend(payload["news"])
        token=payload.get("next_page_token")
        if not token:return rows
        if not isinstance(token,str) or len(token)>512:
            raise OrderRejected("news pagination invalid")
    raise OrderRejected("news pages incomplete; fail closed")

def _publish_monitor_signal(now:datetime,day:str,signal_time:datetime,kind="BULLISH_SIGNAL"):
    """Atomic nonsecret read-only handoff to the five-minute alert monitor.

    Monitor cannot order and only sees this alert, never broker credentials.
    """
    root=Path(os.getenv("MULTI_BROKER_REBOUND_HANDOFF_DIR",""))
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise OrderRejected("monitored rebound handoff directory invalid")
    # The host provisioning owns the group permissions; runner cannot write to
    # arbitrary untrusted destinations or follow symlinks.
    if root.stat().st_uid != os.geteuid() or root.stat().st_mode & 0o007:
        raise OrderRejected("rebound handoff owner / mode invalid")
    out=root/"current.json"
    if out.is_symlink():raise OrderRejected("rebound signal handoff symlink")
    stamp=now.astimezone(timezone.utc).isoformat()
    notice={
        "schema_version":1,
        "strategy":"five_day_rebound",
        "trading_day":day,
        "kind":kind,
        "issued_at_utc":stamp,
        "signal_at_utc":signal_time.astimezone(timezone.utc).isoformat(),
        "order_status":"SIGNAL_ONLY_ORDER_FILL_NOT_VERIFIED",
        "report":("Adverse company-specific earnings/guidance news blocked rebound PAPER buys."
                  if kind=="CATALYST_VETO" else
                  "Prior-five-day downtrend and confirmed semiconductor breakout.")
    }
    tmp=root/("signal-"+str(os.getpid())+".tmp")
    old=os.umask(0o027)
    try:
        with tmp.open("x",encoding="utf-8") as fd:
            json.dump(notice,fd,sort_keys=True)
            fd.flush()
            os.fsync(fd.fileno())
        os.replace(tmp,out)
    finally:
        os.umask(old)
        try:tmp.unlink(missing_ok=True)
        except OSError:pass


def _exit_retry_allowed(conn,day,symbol):
    """No second sell unless previous exact broker order is terminal and unfilled."""
    prior=conn.execute(
        "SELECT client_id FROM attempts WHERE trading_day=? AND symbol=? AND side='exit'"
        " ORDER BY count DESC LIMIT 1",(day,symbol)).fetchone()
    if not prior:
        return True
    cid=prior[0]
    receipt=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+quote(cid,safe=""))
    if not isinstance(receipt,dict) or receipt.get("client_order_id")!=cid:
        return False
    filled=Decimal(str(receipt.get("filled_qty",0)))
    if not filled.is_finite() or filled<0:
        return False
    return filled==0 and receipt.get("status") in ("canceled","expired","rejected")


def run(now:datetime, execute=False):
    if now.tzinfo is None:raise ValueError("timezone aware current time required")
    if execute and os.getenv("MULTI_BROKER_ALLOW_PAPER")!="1":
        raise OrderRejected("PAPER strategy explicit activation flag required")
    day=_next_session(now)
    if day is None:return {"status":"SESSION_CLOSED","orders":[]}
    daystr=day.isoformat()
    local=now.astimezone(ET)
    state=_db()
    try:
        account,positions,orders=_broker_inventory()
        bypos={x["symbol"]:x for x in positions if isinstance(x,dict) and x.get("symbol")}
        managed={symbol:(trading_day,int(qty),ref,status)
                 for trading_day,symbol,ref,qty,status in state.execute(
                    "SELECT trading_day,symbol,buy_client_id,purchased_qty,status FROM owned")}
        for symbol in _archive_completed(state,now,daystr,managed,bypos,orders):
            managed.pop(symbol,None)
        actions=[]
        # Exit-owned positions and stale entry orders before evaluating any new signal.
        in_exit=local.weekday()<5 and local.date()==day and local.time()>=FIRST_EXIT
        if in_exit:
            prices=_quotes(now) if local.time()<LAST_PREOPEN else {}
            for symbol,(trade_day,qty,ref,status) in managed.items():
                if trade_day!=daystr:continue
                open_own=_open_orders(orders,symbol)
                if open_own:
                    # Never add another SELL while a previous SELL is live.
                    # Buy orders are canceled immediately in the exit window;
                    # sell orders are allowed a short fill window, then canceled.
                    # The NEXT tick must verify broker cancellation readback.
                    pending_buys=any(o.get("side")=="buy" for o in open_own)
                    old_sell=False
                    for o in open_own:
                        try:
                            created=datetime.fromisoformat(str(o["created_at"]).replace("Z","+00:00"))
                            if now-created>=timedelta(minutes=3):old_sell=True
                        except (KeyError,TypeError,ValueError):old_sell=False
                    if execute and (pending_buys or old_sell or local.time()>=LAST_PREOPEN):
                        if _cancel_open(state,now,daystr,orders,symbol):
                            actions.append("AWAIT_CANCELLATION:"+symbol)
                    else:
                        actions.append("AWAIT_SELL_FILL:"+symbol)
                    continue
                held=bypos.get(symbol)
                if held is None:
                    # Do not erase ledger. Prior client-id readback is required.
                    try:
                        detail=paper_api("GET","/v2/orders:by_client_order_id?client_order_id="+quote(ref,safe=""))
                        if (isinstance(detail,dict) and detail.get("client_order_id")==ref and
                            detail.get("status") in ("filled","canceled","expired","rejected")):
                            state.execute("UPDATE owned SET status='NO_POSITION_READBACK' WHERE symbol=?",(symbol,))
                            state.commit()
                    except (OrderRejected,UnknownSubmission,ValueError):pass
                    continue
                if held.get("side")!="long":raise OrderRejected("unexpected non-long PAPER position")
                current=Decimal(str(held.get("qty",0)))
                available=Decimal(str(held.get("qty_available",0)))
                if current!=available or current!=current.to_integral_value() or current<1 or int(current)>qty:
                    raise OrderRejected("position ownership / available shares mismatch")
                if not _exit_retry_allowed(state,daystr,symbol):
                    actions.append("AWAIT_EXACT_EXIT_ORDER_READBACK:"+symbol)
                    continue
                if local.time()<LAST_PREOPEN:
                    q=prices.get(symbol)
                    if q is None:
                        actions.append("NO_FRESH_EXIT_QUOTE:"+symbol)
                        continue
                    exit_price=(q[0]*Decimal(".9985")).quantize(Decimal(".01"),rounding=ROUND_DOWN)
                    if execute:_submit(state,now,daystr,symbol,"sell",int(current),exit_price)
                    actions.append("PREOPEN_EXIT_REQUEST:"+symbol)
                elif local.time()<=LAST_EXIT:
                    # Unfilled premarket exit: continue fail-closed broker readback,
                    # but do not abandon strategy-owned PAPER shares at 09:35.
                    # Market fallback requires broker clock OPEN and proof prior
                    # sell is terminal/unfilled. Acceptance is not a fill.
                    clock=paper_api("GET","/v2/clock")
                    if clock.get("is_open") is not True:
                        actions.append("AWAIT_REGULAR_OPEN:"+symbol);continue
                    if execute:_submit(state,now,daystr,symbol,"sell",int(current),market=True)
                    actions.append("FALLBACK_MARKET_EXIT_REQUEST:"+symbol)
                else:
                    _event(state,now,daystr,"MISSED_PREOPEN_EXIT",symbol,"operator reconciliation required")
            return {"status":"EXIT_MANAGEMENT","orders":actions,"strategy":ALERT_NAME}
        if not _entering_window(now):
            return {"status":"OUTSIDE_ENTRY_WINDOW","orders":[]}
        try:
            gate=holiday_gate(now)
        except (ValueError,TypeError,KeyError):
            gate=False
        if not gate:return {"status":"HOLIDAY_GATE_PAUSED","orders":[]}
        # Do not open a new position before validating a complete 5-day reference.
        completed=_fetch_daily(now,day)
        bars=_fetch_sector_bars(now)
        if bars is None:return {"status":"MARKET_FEED_CLOSED","orders":[]}
        decision=evaluate(completed,{s:completed[s][-1] for s in SYMBOLS},bars)
        if not decision.qualifies:
            return {"status":"WAIT","reason":decision.reason,"orders":[]}
        # Clear, independently timestamped adverse earnings/guidance news for
        # any of the three sector anchors invalidates the entire rebound buy
        # basket, because sector-wide sympathy losses were observed historically.
        news=_fetch_causal_news(decision.asof+timedelta(minutes=5))
        catalyst=screen_adverse_catalysts(news,decision.asof+timedelta(minutes=5))
        if catalyst["veto"]:
            if not state.execute("SELECT 1 FROM events WHERE trading_day=? AND type='CATALYST_VETO' LIMIT 1",(daystr,)).fetchone():
                _event(state,now,daystr,"CATALYST_VETO",
                       details="blocked_anchors="+",".join(catalyst["affected_anchors"]))
                _publish_monitor_signal(now,daystr,decision.asof,"CATALYST_VETO")
            return {"status":"CATALYST_VETO","affected_anchors":list(catalyst["affected_anchors"]),
                    "orders":[],"strategy":ALERT_NAME}
        # One signal alert per target trading day; no duplicate spam every minute.
        if not state.execute("SELECT 1 FROM events WHERE trading_day=? AND type='BULLISH_ALERT' LIMIT 1",(daystr,)).fetchone():
            _event(state,now,daystr,"BULLISH_ALERT",details="five_day_down_then_breakout "+decision.asof.isoformat())
            _publish_monitor_signal(now,daystr,decision.asof)
        q=_quotes(now)
        cash=Decimal(str(account.get("cash",0)))
        if cash<=0 or not cash.is_finite():raise OrderRejected("PAPER cash not valid")
        budget=MAX_TOTAL_USD
        for symbol in BASKET:
            if symbol in bypos or _open_orders(orders,symbol) or symbol in managed:
                continue
            if state.execute("SELECT 1 FROM attempts WHERE trading_day=? AND symbol=? AND side='buy' LIMIT 1",
                             (daystr,symbol)).fetchone():
                continue
            quotes=q.get(symbol)
            if quotes is None:continue
            bid,ask=quotes
            limit=ask.quantize(Decimal(".01"),rounding=ROUND_UP)
            qty=int(min(MAX_ORDER_USD,budget,cash)//limit)
            if qty<1:continue
            # Broker must permit extended-hours and overnight instrument before POST.
            asset=paper_api("GET","/v2/assets/"+symbol)
            if not isinstance(asset,dict) or asset.get("tradable") is not True:
                continue
            if trading_feed(now)=="boats" and asset.get("overnight_tradable") is not True:
                continue
            if execute:
                ref=_submit(state,now,daystr,symbol,"buy",qty,limit)
                if ref:
                    state.execute("INSERT INTO owned VALUES(?,?,?,?,?)",
                                  (daystr,symbol,ref,qty,"ENTRY_ACCEPTED_NOT_FILLED"))
                    state.commit()
                    actions.append("PAPER_BUY_ACCEPTED_NOT_FILLED:"+symbol)
                    account,positions,orders=_broker_inventory()
                    cash=Decimal(str(account.get("cash",0)))
            else:actions.append("SIMULATED_BUY:"+symbol)
            budget-=limit*qty
        return {"status":"BULLISH_SIGNAL","orders":actions,"strategy":ALERT_NAME,
                "prior_five":decision.prior_five,"asof":decision.asof.isoformat()}
    finally:
        state.close()


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--once",action="store_true",required=True)
    parser.add_argument("--execute",action="store_true")
    flags=parser.parse_args(argv)
    try:
        result=run(datetime.now(timezone.utc),execute=flags.execute)
        print(json.dumps(result,sort_keys=True))
        return 0
    except (OrderRejected,UnknownSubmission,ValueError,KeyError,sqlite3.Error,OSError) as exc:
        print(json.dumps({"status":"ERROR_NEEDS_RECONCILIATION","error_type":type(exc).__name__,"orders_may_be_uncertain":isinstance(exc,UnknownSubmission)}))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
