"""IBKR official API command construction without a broker connection."""
import sys
import types
import threading
import unittest
from unittest.mock import patch
from multi_broker_bridge import ibkr
from multi_broker_bridge.models import LimitOrder, OrderRejected

class Plain:
    pass

class FakeApp:
    def __init__(self):
        self.next_order_id=107
        self.order_state="Submitted"
        self.seen_order_ref=None
        self.broker_error=False
        self.order_event=threading.Event()
        self.order_event.set()
        self.positions_event=threading.Event()
        self.positions_event.set()
        self.position_rows=[("DU123456","SPY","STK",__import__("decimal").Decimal("3"))]
        self.position_malformed=False
        self.sent=[]
        self.disconnected=False
    def placeOrder(self,order_id,contract,order):
        self.sent.append((order_id,contract,order))
    def reqPositions(self):
        pass
    def cancelPositions(self):
        pass
    def disconnect(self):
        self.disconnected=True

class IBKROfflineTests(unittest.TestCase):
    def test_requires_exact_paper_account(self):
        for value in ("","U12345","DU!BAD"):
            with self.subTest(value=value),patch.dict(__import__("os").environ,{"IBKR_PAPER_ACCOUNT":value}):
                with self.assertRaises(OrderRejected):
                    ibkr._paper_account()
    def test_buy_constructs_paper_limit_order_with_no_extended_hours(self):
        app=FakeApp()
        mods={"ibapi":types.ModuleType("ibapi"),
              "ibapi.contract":types.ModuleType("ibapi.contract"),
              "ibapi.order":types.ModuleType("ibapi.order")}
        mods["ibapi.contract"].Contract=Plain
        mods["ibapi.order"].Order=Plain
        req=LimitOrder.make("ibkr","SPY","buy",1,"10.00","PAPER-ORDER-001")
        with patch.dict(sys.modules,mods),patch.dict(__import__("os").environ,{"IBKR_PAPER_ACCOUNT":"DU123456"}),patch.object(ibkr,"_connected",return_value=app):
            receipt=ibkr.submit(req)
        self.assertEqual(receipt.broker_order_id,"107")
        self.assertTrue(app.disconnected)
        self.assertEqual(len(app.sent),1)
        id_,contract,order=app.sent[0]
        self.assertEqual(order.account,"DU123456")
        self.assertEqual(order.orderType,"LMT")
        self.assertEqual(order.tif,"DAY")
        self.assertFalse(order.outsideRth)
        self.assertEqual(order.orderRef,req.client_order_id)
        self.assertEqual(contract.exchange,"SMART")
        self.assertEqual((ibkr.HOST,ibkr.PORT),("127.0.0.1",4002))
    def test_sell_refuses_unavailable_shares(self):
        app=FakeApp()
        app.position_rows=[]
        mods={"ibapi":types.ModuleType("ibapi"),
              "ibapi.contract":types.ModuleType("ibapi.contract"),
              "ibapi.order":types.ModuleType("ibapi.order")}
        mods["ibapi.contract"].Contract=Plain
        mods["ibapi.order"].Order=Plain
        req=LimitOrder.make("ibkr","SPY","sell",1,"10.00","PAPER-ORDER-002")
        with patch.dict(sys.modules,mods),patch.dict(__import__("os").environ,{"IBKR_PAPER_ACCOUNT":"DU123456"}),patch.object(ibkr,"_connected",return_value=app):
            with self.assertRaises(OrderRejected):
                ibkr.submit(req)
        self.assertFalse(app.sent)
        self.assertTrue(app.disconnected)

if __name__=="__main__":unittest.main()
