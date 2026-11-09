"""Read-only Alpaca PAPER fill audit. No broker mutations, no account identity output.

Run with the same restricted systemd LoadCredential pair as existing PAPER
executor, not with keys in command arguments. Match paper fill IDs against
MBB-tagged orders before attributing returns. This is an audit, not a strategy.
"""
from __future__ import annotations
from collections import defaultdict,deque,Counter
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
import json,os,sys
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

from .auto_paper import _credentials

PAPER="https://paper-api.alpaca.markets"
DAY="2026-11-09"
MAX_PAGES=15
PAGE_SIZE=100


def safe_get(path):
    if not path.startswith("/v2/account/activities") and not path.startswith("/v2/orders"):
        raise ValueError("Read-only endpoint not allowed")
    key,secret=_credentials()
    req=Request(PAPER+path,method="GET",headers={
        "APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,
        "Accept":"application/json"
    })
    try:
        with urlopen(req,timeout=12) as res:
            if res.status!=200:raise ValueError("Bad status from paper account")
            data=json.loads(res.read(2_000_000))
    except (HTTPError,URLError,OSError,ValueError,TimeoutError) as e:
        raise ValueError("PAPER_READ_FAILURE_"+type(e).__name__) from None
    if not isinstance(data,list):
        raise ValueError("Expected list from read-only paper API")
    return data


def paged_fills():
    allrows=[];token=None
    for p in range(MAX_PAGES):
        params={"activity_types":"FILL","after":DAY+"T00:00:00Z",
                "direction":"asc","page_size":str(PAGE_SIZE)}
        if token:params["page_token"]=token
        rows=safe_get("/v2/account/activities?"+urlencode(params))
        if any(x.get("activity_type")!="FILL" or not isinstance(x,dict) for x in rows):
            raise ValueError("Unexpected account activity")
        allrows.extend(rows)
        if len(rows)<PAGE_SIZE:
            return allrows
        token=rows[-1].get("id")
        if not token:raise ValueError("Missing pagination cursor")
    raise ValueError("PAPER_FILL_HISTORY_INCOMPLETE")


def order_map():
    rows=safe_get("/v2/orders?"+urlencode({
        "status":"all","after":DAY+"T00:00:00Z",
        "limit":"500","direction":"asc"
    }))
    if len(rows)>=500:
        raise ValueError("Order history truncated")
    result={}
    for x in rows:
        if not isinstance(x,dict) or not x.get("id"):
            raise ValueError("Malformed order response")
        result[str(x["id"])]=x
    return result


def main():
    try:
        fills=paged_fills()
        orders=order_map()
        matched=[];unmatched=0
        for row in fills:
            order=orders.get(str(row.get("order_id","")))
            if not order or not str(order.get("client_order_id","")).startswith("MBB-"):
                unmatched+=1
                continue
            try:
                time=datetime.fromisoformat(row["transaction_time"].replace("Z","+00:00"))
                quantity=Decimal(str(row["qty"]))
                price=Decimal(str(row["price"]))
            except (ValueError,TypeError,KeyError,InvalidOperation):
                raise ValueError("Invalid fill")
            if (time.tzinfo is None or quantity<=0 or price<=0
                or not quantity.is_finite() or not price.is_finite()):
                raise ValueError("Invalid fill economics")
            matched.append((time,str(row["symbol"]),str(row["side"]),quantity,price))
        matched.sort()
        fifo=defaultdict(deque);pnl=defaultdict(lambda:Decimal("0"))
        buys=Counter();sells=Counter()
        first=defaultdict(lambda:None)
        last=defaultdict(lambda:None)
        gross_buy=Decimal("0");gross_sell=Decimal("0")
        for time,sym,side,qty,price in matched:
            if first[sym] is None:first[sym]=time
            last[sym]=time
            if side=="buy":
                buys[sym]+=1;fifo[sym].append([qty,price,time]);gross_buy+=qty*price
            elif side=="sell":
                sells[sym]+=1;gross_sell+=qty*price
                remaining=qty
                while remaining>0:
                    if not fifo[sym]:
                        raise ValueError("MBB sells not matched by same-day MBB buys for "+sym)
                    lot=fifo[sym][0]
                    take=min(remaining,lot[0])
                    pnl[sym]+=(price-lot[1])*take
                    lot[0]-=take;remaining-=take
                    if lot[0]==0:fifo[sym].popleft()
            else:
                raise ValueError("Unknown side")
        open_qty={s:str(sum((lot[0] for lot in q),Decimal("0"))) for s,q in fifo.items() if q}
        combined=sorted(set(buys)|set(sells))
        print(json.dumps({
            "status":"READ_ONLY_PAPER_FILLED_TRADES",
            "date_utc_from":DAY+"T00:00:00Z",
            "total_broker_fill_activities":len(fills),
            "matched_MBB_fills":len(matched),
            "unmatched_fill_activities":unmatched,
            "gross_buy_notional_usd":str(gross_buy.quantize(Decimal(".01"))),
            "gross_sell_notional_usd":str(gross_sell.quantize(Decimal(".01"))),
            "gross_realized_paper_profit_usd":str(sum(pnl.values(),Decimal("0")).quantize(Decimal(".01"))),
            "open_MBB_fill_quantities":open_qty,
            "by_symbol":[{
                "symbol":s,"buys":buys[s],"sells":sells[s],
                "realized_paper_profit_usd":str(pnl[s].quantize(Decimal(".01"))),
                "first_fill_ct":first[s].astimezone(__import__("zoneinfo").ZoneInfo("America/Chicago")).strftime("%H:%M"),
                "last_fill_ct":last[s].astimezone(__import__("zoneinfo").ZoneInfo("America/Chicago")).strftime("%H:%M")
            } for s in combined],
            "broker_orders_retrieved":len(orders),
            "orders_submitted":0
        },sort_keys=True))
        return 0
    except (ValueError,KeyError,TypeError) as e:
        print(json.dumps({"status":"READ_ONLY_AUDIT_INCOMPLETE",
                          "reason":str(e)[:110] if str(e).startswith(("PAPER_","MBB","Invalid","Order history","Unknown","Expected","Missing","Malformed","Broker")) else type(e).__name__,
                          "orders_submitted":0}))
        return 2

if __name__=="__main__":
    sys.exit(main())
