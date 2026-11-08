"""PAPER-only CLI. Default is preview, never an order."""
from __future__ import annotations
import argparse
import json
import os
import sys
from .models import LimitOrder, OrderRejected, UnknownSubmission
from . import alpaca, ibkr, robinhood
from .ledger import connect, record, reserve, state_path

BROKERS={"alpaca":alpaca,"ibkr":ibkr,"robinhood":robinhood}

def execute(req: LimitOrder) -> dict:
    if req.broker=="robinhood":
        raise OrderRejected("Robinhood has no PAPER environment; LIVE orders are forbidden")
    if os.getenv("MULTI_BROKER_ALLOW_PAPER")!="1":
        raise OrderRejected("set MULTI_BROKER_ALLOW_PAPER=1 explicitly for broker PAPER execution")
    with connect(state_path()) as db:
        reserve(db, req)
        try:
            receipt=BROKERS[req.broker].submit(req)
        except OrderRejected:
            record(db,req,"REJECTED",None)
            raise
        except BaseException:
            # Includes network/timeout/interrupt: unknown is intentional.
            raise
        record(db,req,receipt.status,receipt.broker_order_id)
        return receipt.public()

def main(argv=None) -> int:
    p=argparse.ArgumentParser(description="PAPER-only minimal broker adapter; preview by default")
    p.add_argument("--broker",choices=tuple(BROKERS),required=True)
    p.add_argument("--check",action="store_true",help="read-only broker connectivity and capability check")
    p.add_argument("--readback",metavar="CLIENT_ID",help="read-only order lookup by client order ID (Alpaca PAPER)")
    p.add_argument("--execute",action="store_true",help="send an authorized PAPER order, never LIVE")
    p.add_argument("--symbol",help="uppercase US stock ticker")
    p.add_argument("--side",choices=("buy","sell"),default="buy")
    p.add_argument("--qty",type=int,default=1)
    p.add_argument("--limit",dest="limit_price",help="positive two-decimal limit price")
    p.add_argument("--client-order-id",help="unique 6-64 char id; NEVER reuse after unknown")
    args=p.parse_args(argv)
    try:
        if args.readback:
            if args.execute or args.check or args.broker!="alpaca":
                raise OrderRejected("readback only supports Alpaca PAPER without other actions")
            result=alpaca.readback(args.readback)
        elif args.check:
            if args.execute:
                raise OrderRejected("--check and --execute are mutually exclusive")
            result=BROKERS[args.broker].check()
        else:
            if not args.symbol or not args.limit_price or not args.client_order_id:
                raise OrderRejected("symbol, limit and client-order-id are required")
            req=LimitOrder.make(args.broker,args.symbol,args.side,args.qty,
                                args.limit_price,args.client_order_id)
            if args.execute:
                result=execute(req)
            else:
                result=(robinhood.shadow_preview(req) if args.broker=="robinhood" else
                        {**req.public(),"status":"PREVIEW_ONLY","broker_order_id":None,
                         "submitted_to_broker":False})
        print(json.dumps(result,sort_keys=True))
        return 0
    except (OrderRejected,UnknownSubmission) as exc:
        print(json.dumps({"ok":False,"broker":args.broker,"error_type":type(exc).__name__,
                          "message":str(exc),"broker_order_sent_not_verified":isinstance(exc,UnknownSubmission)},
                         sort_keys=True),file=sys.stderr)
        return 78 if isinstance(exc,OrderRejected) else 75

if __name__=="__main__":
    raise SystemExit(main())
