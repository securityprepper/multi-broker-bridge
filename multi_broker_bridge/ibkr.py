"""Official IBKR TWS API adapter for SIMPLE PAPER limit orders only.

Uses an already authenticated IB Gateway, no root service changes, no LIVE port,
no auto-retry and no bracket/stop claims. Import ibapi only when used.
"""
from __future__ import annotations
import os
import threading
from .models import LimitOrder, OrderRejected, UnknownSubmission, Receipt

HOST="127.0.0.1"
PORT=4002
CLIENT_ID=88
TIMEOUT=12.0
GOOD_STATUSES={"ApiPending","PendingSubmit","PreSubmitted","Submitted","Filled"}

def _paper_account() -> str:
    account=(os.getenv("IBKR_PAPER_ACCOUNT") or "").strip()
    if not account.startswith("DU") or len(account)<5 or not account.isalnum():
        raise OrderRejected("exact IBKR DU-prefixed PAPER account required")
    return account

def _new_app():
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
    except ImportError as exc:
        raise OrderRejected("official IBKR ibapi package is not installed") from exc

    class App(EWrapper,EClient):
        def __init__(self):
            EWrapper.__init__(self)
            EClient.__init__(self,self)
            self.ready=threading.Event()
            self.accounts_event=threading.Event()
            self.positions_event=threading.Event()
            self.position_rows=[]
            self.position_malformed=False
            self.order_event=threading.Event()
            self.managed_accounts=[]
            self.next_order_id=None
            self.target_order_id=None
            self.order_state=None
            self.seen_order_ref=None
            self.broker_error=False

        def nextValidId(self, orderId):
            try:
                if type(orderId) is int and orderId>0:
                    self.next_order_id=orderId
            finally:
                self.ready.set()

        def managedAccounts(self, accountsList):
            self.managed_accounts=[a.strip() for a in accountsList.split(",") if a.strip()]
            self.accounts_event.set()

        def position(self, account, contract, pos, avgCost):
            try:
                from decimal import Decimal
                quantity=Decimal(str(pos))
                if not quantity.is_finite():
                    raise ValueError("nonfinite position")
                self.position_rows.append((account, getattr(contract,"symbol",None),
                                           getattr(contract,"secType",None), quantity))
            except (TypeError,ValueError):
                self.position_malformed=True

        def positionEnd(self):
            self.positions_event.set()

        def openOrder(self, orderId, contract, order, orderState):
            if orderId==self.target_order_id:
                self.seen_order_ref=getattr(order,"orderRef",None)
                self.order_state=getattr(orderState,"status",None) or "OPEN_ORDER"
                self.order_event.set()

        def orderStatus(self, orderId, status, *args):
            if orderId==self.target_order_id:
                self.order_state=status
                self.order_event.set()

        def error(self, reqId, *args):
            # IB API variants include errorTime ahead of errorCode.
            try:
                if len(args)>=3 and isinstance(args[0],int) and isinstance(args[1],int):
                    code=int(args[1])
                elif len(args)>=2:
                    code=int(args[0])
                else:
                    return
            except (TypeError, ValueError):
                self.broker_error=True
                return
            if code in (2104,2106,2107,2108,2158):
                return
            if reqId in (-1,self.target_order_id):
                self.broker_error=True
                self.order_event.set()

    return App()

def _connected(account: str):
    app=_new_app()
    try:
        app.connect(HOST,PORT,CLIENT_ID)
        if not app.isConnected():
            raise UnknownSubmission("IBKR PAPER gateway not connected")
        runner=threading.Thread(target=app.run,daemon=True)
        runner.start()
        if not app.ready.wait(TIMEOUT) or app.next_order_id is None:
            raise UnknownSubmission("IBKR did not provide nextValidId")
        app.reqManagedAccts()
        if not app.accounts_event.wait(TIMEOUT):
            raise UnknownSubmission("IBKR managed accounts callback missing")
        if app.managed_accounts != [account]:
            raise OrderRejected("IBKR PAPER account mismatch or additional account present")
        if app.broker_error:
            raise UnknownSubmission("IBKR broker error during account verification")
        return app
    except BaseException:
        try:
            app.disconnect()
        except OSError:
            pass
        raise

def check() -> dict:
    account=_paper_account()
    app=_connected(account)
    try:
        return {"broker":"ibkr","environment":"PAPER","account_verified":True,
                "gateway":"localhost:4002","next_order_id_observed":True}
    finally:
        app.disconnect()

def submit(req: LimitOrder) -> Receipt:
    if req.broker!="ibkr":
        raise OrderRejected("wrong broker adapter")
    account=_paper_account()
    app=_connected(account)
    try:
        if req.side=="sell":
            # Complete broker position inventory: never create an accidental short.
            app.reqPositions()
            try:
                if not app.positions_event.wait(TIMEOUT) or app.position_malformed or app.broker_error:
                    raise UnknownSubmission("IBKR position inventory incomplete; SELL refused")
                for row in app.position_rows:
                    if row[0] != account:
                        raise OrderRejected("additional IBKR account in position stream")
                available=sum((row[3] for row in app.position_rows
                               if row[1]==req.symbol and row[2]=="STK"),
                              start=__import__("decimal").Decimal("0"))
                if available<req.qty:
                    raise OrderRejected("SELL exceeds verified IBKR PAPER long position")
            finally:
                app.cancelPositions()
        from ibapi.contract import Contract
        from ibapi.order import Order
        oid=app.next_order_id
        if type(oid) is not int or oid<=0:
            raise UnknownSubmission("IBKR order identifier unverified")
        contract=Contract()
        contract.symbol=req.symbol
        contract.secType="STK"
        contract.exchange="SMART"
        contract.currency="USD"
        order=Order()
        order.account=account
        order.action=req.side.upper()
        order.orderType="LMT"
        order.totalQuantity=req.qty
        order.lmtPrice=float(req.limit_price)
        order.tif="DAY"
        order.outsideRth=False
        order.transmit=True
        order.orderRef=req.client_order_id
        app.target_order_id=oid
        # If the broker session closes after the following call, the ledger
        # reservation is UNKNOWN and this command MUST NEVER auto-retry.
        app.placeOrder(oid,contract,order)
        if not app.order_event.wait(TIMEOUT):
            raise UnknownSubmission("IBKR PAPER acknowledgment timed out; reconcile first")
        if app.broker_error:
            raise UnknownSubmission("IBKR reported order error; check broker state")
        if app.seen_order_ref is not None and app.seen_order_ref!=req.client_order_id:
            raise UnknownSubmission("IBKR orderRef mismatch")
        if app.order_state not in GOOD_STATUSES and app.order_state!="OPEN_ORDER":
            raise UnknownSubmission("IBKR returned unverified order state")
        return Receipt("ibkr",req.client_order_id,"ACCEPTED",str(oid),
                       "Broker callback received; fill and protection not verified")
    finally:
        try:
            app.disconnect()
        except OSError:
            pass
