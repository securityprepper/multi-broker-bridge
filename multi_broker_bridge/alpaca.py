"""Alpaca official PAPER REST adapter. Never accepts a caller-provided URL."""
from __future__ import annotations
import json
import os
from urllib import request, error, parse
from .models import LimitOrder, OrderRejected, UnknownSubmission, Receipt

BASE = "https://paper-api.alpaca.markets"
MAX_BYTES = 64 * 1024

class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OrderRejected("unexpected broker redirect refused")

def _headers() -> dict[str,str]:
    key = os.getenv("ALPACA_PAPER_KEY_ID") or ""
    secret = os.getenv("ALPACA_PAPER_SECRET_KEY") or ""
    if not key or not secret:
        raise OrderRejected("Alpaca PAPER credentials are not configured")
    return {"APCA-API-KEY-ID":key, "APCA-API-SECRET-KEY":secret,
            "Accept":"application/json", "Content-Type":"application/json"}

def _http(method: str, path: str, payload: dict | None = None) -> dict:
    if not path.startswith("/v2/") or path.startswith("//") or "://" in path:
        raise OrderRejected("unexpected broker path")
    raw = None if payload is None else json.dumps(payload, separators=(",",":")).encode()
    req = request.Request(BASE+path, data=raw, headers=_headers(), method=method)
    try:
        with request.build_opener(_NoRedirect()).open(req, timeout=8) as response:
            if response.status not in (200,201):
                raise UnknownSubmission("unexpected Alpaca PAPER response")
            contents = response.read(MAX_BYTES + 1)
    except error.HTTPError as exc:
        # A known HTTP rejection is not necessarily safe to retry; preserve receipt.
        if exc.code in (400,401,403,404,422):
            raise OrderRejected("Alpaca PAPER rejected request (HTTP "+str(exc.code)+")") from exc
        raise UnknownSubmission("Alpaca PAPER returned uncertain HTTP status") from exc
    except (error.URLError, OSError, TimeoutError) as exc:
        raise UnknownSubmission("Alpaca PAPER transport uncertainty; reconcile first") from exc
    if len(contents)>MAX_BYTES:
        raise UnknownSubmission("oversized broker response")
    try:
        body=json.loads(contents)
    except (ValueError, UnicodeError) as exc:
        raise UnknownSubmission("non-JSON broker response") from exc
    if not isinstance(body, dict):
        raise UnknownSubmission("unexpected broker response object")
    return body

def check() -> dict:
    data=_http("GET","/v2/account")
    if data.get("trading_blocked") is not False or data.get("account_blocked") is True:
        raise OrderRejected("Alpaca PAPER account blocked or unverified")
    expected=os.getenv("ALPACA_PAPER_ACCOUNT_ID")
    if expected and data.get("id") != expected:
        raise OrderRejected("Alpaca PAPER account identity mismatch")
    if not data.get("id"):
        raise OrderRejected("Alpaca PAPER account identity missing")
    return {"broker":"alpaca","environment":"PAPER","account_verified":True,
            "trading_blocked":False}

def submit(req: LimitOrder) -> Receipt:
    if req.broker!="alpaca":
        raise OrderRejected("wrong broker adapter")
    check()
    payload={"symbol":req.symbol,"qty":str(req.qty),
             "side":req.side,"type":"limit",
             "limit_price":str(req.limit_price),"time_in_force":"day",
             "extended_hours":False,
             "client_order_id":req.client_order_id}
    order=_http("POST","/v2/orders",payload)
    order_id=order.get("id")
    if not isinstance(order_id,str) or not order_id:
        raise UnknownSubmission("Alpaca PAPER order ID missing; reconcile first")
    if order.get("client_order_id")!=req.client_order_id:
        raise UnknownSubmission("Alpaca PAPER client order identity mismatch")
    return Receipt(req.broker,req.client_order_id,"ACCEPTED",order_id,
                   "Broker accepted order request, fill not yet verified")

def readback(client_order_id: str) -> dict:
    if not client_order_id.isascii() or len(client_order_id)>64:
        raise OrderRejected("invalid client order ID")
    path="/v2/orders:by_client_order_id?client_order_id="+parse.quote(client_order_id,safe="")
    data=_http("GET",path)
    if data.get("client_order_id")!=client_order_id:
        raise UnknownSubmission("broker readback ID mismatch")
    return {"broker":"alpaca","client_order_id":client_order_id,
            "broker_order_id":data.get("id"),"status":data.get("status"),
            "filled_qty":data.get("filled_qty")}
