"""Independent RTH time-exit for strategy-managed PAPER positions.

Runs before quote/bar fetching, so a market-data outage cannot suppress the
13:40 CT liquidation attempt. It is deliberately restricted to Alpaca PAPER
and MBB-tagged orders/positions (never LIVE or manually owned positions).
No blind POST retry after an uncertain broker response.
"""
from __future__ import annotations

from datetime import datetime,time
from decimal import Decimal,InvalidOperation
import re
import sqlite3
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .models import OrderRejected, UnknownSubmission

CHICAGO=ZoneInfo("America/Chicago")
FLATTEN_START=time(13,40)
ESCALATE_START=time(13,50)
DEADLINE=time(14,0)
RTH_END=time(15,0)
START_CLIENT_PREFIX="MBB-"
FINAL_ORDER_STATUSES=frozenset({"filled","canceled","expired","rejected","done_for_day"})

def _broker_inventory(positions,orders):
    if not isinstance(positions,list) or not isinstance(orders,list) or len(orders)>=500:
        raise OrderRejected("Timed exit needs complete position/order inventory")
    pos={}
    for row in positions:
        if not isinstance(row,dict) or not isinstance(row.get("symbol"),str):
            raise OrderRejected("Invalid broker position inventory")
        if row["symbol"] in pos:
            raise OrderRejected("Duplicate broker position")
        pos[row["symbol"]]=row
    return pos

def _positive_whole_qty(position):
    if position.get("side")!="long":
        raise OrderRejected("Cannot flatten unidentified short/margin position")
    try:
        total=Decimal(str(position["qty"]))
        available=Decimal(str(position.get("qty_available",position["qty"])))
    except (InvalidOperation,ValueError,TypeError,KeyError) as exc:
        raise OrderRejected("Position quantity not verified") from exc
    if (not total.is_finite() or not available.is_finite()
        or total<=0 or available!=total or
        total!=total.to_integral_value()):
        raise OrderRejected("Held/partial/invalid shares need reconciliation")
    return int(total)

def _attempt(db,date,symbol,ref):
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO attempts (trade_date,symbol,side,client_id,state)"
                   " VALUES(?,?,?,?,?)",(date,symbol,"flatten",ref,"UNKNOWN"))
        db.commit()
        return True
    except sqlite3.IntegrityError:
        db.rollback()
        return False

def _state(db,date,symbol,status):
    db.execute("UPDATE attempts SET state=? WHERE trade_date=? AND symbol=? AND side='flatten'",
               (status,date,symbol))
    db.commit()

def timed_flatten(now,positions,orders,db,broker_api):
    """Return None outside exit window, or a verified PAPER exit status.

    Keep all orders scoped to confirmed strategy-held symbols. An Alpaca 204
    cancellation is NOT proof: stop after cancel request, read back next tick.
    Order POST is reserved before submission. Broker order acceptance != fill.
    """
    local=now.astimezone(CHICAGO)
    if local.weekday()>4 or not (FLATTEN_START<=local.time()<RTH_END):
        return None
    date=local.date().isoformat()
    overdue=local.time()>=DEADLINE
    urgent=local.time()>=ESCALATE_START
    holdings=_broker_inventory(positions,orders)
    tracked={str(s):(str(ref),int(qty)) for s,ref,qty in
             db.execute("SELECT symbol,entry_ref,entry_qty FROM tracked")}
    if not tracked:
        if any(str(row.get("client_order_id","")).startswith(START_CLIENT_PREFIX)
               for row in orders if isinstance(row,dict)):
            return {"status":"UNTRACKED_MBB_ORDERS_NEED_RECONCILIATION",
                    "flat_verified":False,"actions":[],"overdue":urgent}
        if holdings:
            return {"status":"UNTRACKED_BROKER_POSITIONS_NEED_RECONCILIATION",
                    "flat_verified":False,"actions":[],"overdue":urgent}
        return {"status":"NO_TRACKED_STRATEGY_SHARES","flat_verified":True,
                "actions":[],"overdue":False}
    clock=broker_api("GET","/v2/clock")
    if not isinstance(clock,dict) or clock.get("is_open") is not True:
        return {"status":"BROKER_CLOCK_BLOCKED","flat_verified":False,
                "actions":[],"overdue":urgent}
    own_open=[];other_open=[]
    for order in orders:
        if not isinstance(order,dict):
            raise OrderRejected("Bad open-order structure")
        symbol=order.get("symbol")
        if symbol not in tracked: continue
        if str(order.get("status","")).lower() in FINAL_ORDER_STATUSES:
            continue
        oid=str(order.get("id",""))
        cid=str(order.get("client_order_id",""))
        if not oid or not re.fullmatch(r"[a-zA-Z0-9_-]{3,128}",oid):
            raise OrderRejected("Missing/invalid order id in PAPER inventory")
        if cid.startswith(START_CLIENT_PREFIX):
            own_open.append(order)
        else:
            other_open.append(order)
    if other_open:
        return {"status":"UNMANAGED_ORDER_BLOCKED","flat_verified":False,
                "actions":["UNMANAGED_OPEN_ORDERS"],"overdue":urgent}
    if own_open:
        actions=[]
        for order in own_open:
            # Never repeat cancellation based on stale broker readback: a
            # second attempt may be safe but is not needed within one scan.
            broker_api("DELETE","/v2/orders/"+quote(str(order["id"]),safe=""))
            actions.append("CANCEL_REQUESTED:"+order["symbol"])
        return {"status":"AWAIT_BROKER_CANCEL_READBACK","flat_verified":False,
                "actions":actions,"overdue":urgent}
    actions=[];open_symbols=[]
    for symbol,(entry_ref,entry_qty) in tracked.items():
        if not re.fullmatch(r"[A-Z0-9.]{1,12}",symbol):
            raise OrderRejected("Untrusted symbol in strategy ledger")
        pos=holdings.get(symbol)
        if pos is None:
            # Already flat in an authoritative broker position snapshot;
            # do not delete tracked ledger until fill reconciliation.
            continue
        qty=_positive_whole_qty(pos)
        if entry_qty<1 or qty>entry_qty:
            raise OrderRejected("Broker holds more than tracked strategy quantity; possible manual shares")
        open_symbols.append(symbol)
        client_id=f"MBB-{local:%Y%m%d}-F-{symbol}"[:48]
        if not _attempt(db,date,symbol,client_id):
            actions.append("FLATTEN_PREVIOUSLY_RESERVED:"+symbol)
            continue
        payload={
            "symbol":symbol,"qty":str(qty),"side":"sell",
            "type":"market","time_in_force":"day",
            "extended_hours":False,"client_order_id":client_id,
        }
        try:
            receipt=broker_api("POST","/v2/orders",payload)
        except OrderRejected:
            _state(db,date,symbol,"REJECTED")
            actions.append("BROKER_REJECTED:"+symbol)
            continue
        # UnknownSubmission intentionally propagates with UNKNOWN reserved,
        # so the next minute only reconciles, never repeats the sell blindly.
        if not isinstance(receipt,dict) or not receipt.get("id") or receipt.get("client_order_id")!=client_id:
            raise UnknownSubmission("PAPER flatten receipt invalid; reconcile before retry")
        _state(db,date,symbol,str(receipt.get("status","accepted")))
        actions.append("MARKET_FLATTEN_ACCEPTED_NOT_FILLED:"+symbol)
    # Do not assume a POST receipt means flat; next run verifies positions.
    if not open_symbols:
        return {"status":"FLAT_IN_BROKER_SNAPSHOT","flat_verified":True,
                "actions":[],"overdue":False}
    return {"status":"FLATTEN_IN_PROGRESS" if not overdue else "PAST_2PM_DEADLINE",
            "flat_verified":False,"actions":actions,"overdue":urgent}
