"""Webull official OpenAPI *SANDBOX ONLY* adapter.

No live endpoints, no arbitrary broker URL, no production credentials.
Requires user's own paperTrade sandbox App Key/Secret and account ID.
The official SDK supplies signing and authentication.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import os
from .models import LimitOrder, OrderRejected, UnknownSubmission, Receipt

SANDBOX_ENDPOINT = "api.sandbox.webull.com"

def _credentials() -> tuple[str, str, str]:
    key = os.getenv("WEBULL_SANDBOX_APP_KEY", "").strip()
    secret = os.getenv("WEBULL_SANDBOX_APP_SECRET", "").strip()
    account = os.getenv("WEBULL_SANDBOX_ACCOUNT_ID", "").strip()
    if not key or not secret or not account:
        raise OrderRejected("Webull paperTrade sandbox API credentials/account not configured")
    return key, secret, account

def _client():
    key, secret, account = _credentials()
    try:
        from webull.core.client import ApiClient
        from webull.trade.trade_client import TradeClient
    except ImportError as exc:
        raise OrderRejected("install official webull-openapi-python-sdk into an isolated venv") from exc
    api = ApiClient(key, secret, "us")
    api.add_endpoint("us", SANDBOX_ENDPOINT)
    return TradeClient(api), account

def _json_response(res) -> dict:
    if getattr(res, "status_code", None) != 200:
        raise UnknownSubmission("Webull SANDBOX response failed; reconcile before retry")
    try:
        data = res.json()
    except (ValueError, TypeError) as exc:
        raise UnknownSubmission("Webull SANDBOX returned invalid response") from exc
    if not isinstance(data, dict):
        raise UnknownSubmission("Webull SANDBOX response format unverified")
    return data

def _accounts(trade, account):
    data = _json_response(trade.account_v2.get_account_list())
    rows = data.get("data")
    if not isinstance(rows, list):
        raise OrderRejected("Webull SANDBOX account list format unverified")
    if not any(isinstance(row,dict) and row.get("account_id") == account for row in rows):
        raise OrderRejected("Webull SANDBOX requested account ID not present")
    return rows

def check() -> dict:
    trade, account = _client()
    _accounts(trade,account)
    return {"broker":"webull","environment":"SANDBOX_PAPER",
            "account_verified":True,"endpoint":SANDBOX_ENDPOINT,
            "live_trading_enabled":False}

def _sell_available(trade, account: str, symbol: str, qty: int):
    payload = _json_response(trade.account_v2.get_account_position(account))
    # Refuse unknown shapes instead of risking an unintended short sale.
    rows = payload.get("data")
    if isinstance(rows, dict):
        rows = rows.get("positions")
    if not isinstance(rows, list):
        raise OrderRejected("Webull SANDBOX positions cannot be confirmed")
    held=Decimal("0")
    for row in rows:
        if not isinstance(row,dict):
            raise OrderRejected("Webull SANDBOX malformed position row")
        if row.get("symbol")==symbol:
            try: held += Decimal(str(row.get("quantity")))
            except (InvalidOperation,ValueError,TypeError) as exc:
                raise OrderRejected("Webull SANDBOX position quantity unverified") from exc
    if not held.is_finite() or held < qty:
        raise OrderRejected("Webull SANDBOX SELL exceeds verified long position")

def order_payload(req: LimitOrder) -> dict:
    if req.broker!="webull":
        raise OrderRejected("wrong broker adapter")
    if len(req.client_order_id)>32:
        raise OrderRejected("Webull client order ID maximum length is 32")
    return {"client_order_id":req.client_order_id,"combo_type":"NORMAL",
            "symbol":req.symbol,"instrument_type":"EQUITY","market":"US",
            "order_type":"LIMIT","limit_price":str(req.limit_price),
            "quantity":str(req.qty),"side":req.side.upper(),
            "support_trading_session":"CORE","time_in_force":"DAY",
            "entrust_type":"QTY"}

def submit(req: LimitOrder) -> Receipt:
    order=order_payload(req)
    trade, account = _client()
    _accounts(trade,account)
    if req.side=="sell":
        _sell_available(trade,account,req.symbol,req.qty)
    response=_json_response(trade.order_v3.place_order(account,[order]))
    # HTTP 200 only acknowledges API submission, not necessarily fill.
    if response.get("error_code"):
        raise UnknownSubmission("Webull SANDBOX returned order error")
    return Receipt("webull",req.client_order_id,"SUBMITTED",None,
                   "HTTP response accepted; query order detail to verify broker order and fill")

def readback(client_order_id: str) -> dict:
    if not isinstance(client_order_id,str) or not 6<=len(client_order_id)<=32 or not client_order_id.replace("_","").replace("-","").isalnum():
        raise OrderRejected("invalid Webull client order ID")
    trade,account=_client()
    _accounts(trade,account)
    details=_json_response(trade.order_v3.get_order_detail(account,client_order_id))
    orders=details.get("orders")
    if not isinstance(orders,list):
        raise UnknownSubmission("Webull SANDBOX detailed order list unavailable")
    exact=[x for x in orders if isinstance(x,dict) and x.get("client_order_id")==client_order_id]
    if len(exact)!=1:
        raise UnknownSubmission("Webull SANDBOX order client ID not uniquely verified")
    item=exact[0]
    return {"broker":"webull","environment":"SANDBOX_PAPER",
            "client_order_id":client_order_id,
            "broker_order_id":item.get("order_id"),"status":item.get("status"),
            "filled_qty":item.get("filled_quantity")}
