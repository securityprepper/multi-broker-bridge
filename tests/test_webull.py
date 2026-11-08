"""Webull official SANDBOX adapter offline tests: no real credentials or trading."""
import os
import unittest
from unittest.mock import patch
from multi_broker_bridge import webull
from multi_broker_bridge.models import LimitOrder, OrderRejected, UnknownSubmission

class FakeResponse:
    status_code=200
    def __init__(self,payload):self.payload=payload
    def json(self):return self.payload

class FakeAccounts:
    def get_account_list(self):
        return FakeResponse({"data":[{"account_id":"SANDBOX-ACCOUNT"}]})
    def get_account_position(self,account):
        return FakeResponse({"data":[{"symbol":"AMD","quantity":"2"}]})

class FakeOrders:
    def __init__(self):self.orders=[]
    def place_order(self,account,orders):
        self.orders.append((account,orders))
        return FakeResponse({"client_order_id":orders[0]["client_order_id"]})
    def get_order_detail(self,account,client_order_id):
        return FakeResponse({"orders":[{"client_order_id":client_order_id,
                 "order_id":"PAPER-ID-123","status":"SUBMITTED","filled_quantity":"0"}]})

class FakeTrade:
    def __init__(self):
        self.account_v2=FakeAccounts()
        self.order_v3=FakeOrders()

def req(side="buy",qty=1,price="400.00"):
    return LimitOrder.make("webull","AMD",side,qty,price,"WEBULL-TEST-001")

class SandboxTests(unittest.TestCase):
    def test_sandbox_fixed_host_and_paper_core_day_limit(self):
        r=webull.order_payload(req())
        self.assertEqual(webull.SANDBOX_ENDPOINT,"api.sandbox.webull.com")
        self.assertEqual((r["support_trading_session"],r["order_type"],r["combo_type"]),
                         ("CORE","LIMIT","NORMAL"))
        self.assertEqual((r["side"],r["time_in_force"],r["entrust_type"]),("BUY","DAY","QTY"))
    def test_order_no_production_env_and_id_checked(self):
        trade=FakeTrade()
        with patch.object(webull,"_client",return_value=(trade,"SANDBOX-ACCOUNT")):
            receipt=webull.submit(req())
            detail=webull.readback("WEBULL-TEST-001")
        self.assertEqual(receipt.status,"SUBMITTED")
        self.assertEqual(trade.order_v3.orders[0][0],"SANDBOX-ACCOUNT")
        self.assertEqual(detail["broker_order_id"],"PAPER-ID-123")
    def test_missing_sandbox_keys_fail_closed(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(OrderRejected):
                webull.check()
    def test_stock_shorting_is_refused(self):
        trade=FakeTrade()
        with patch.object(webull,"_client",return_value=(trade,"SANDBOX-ACCOUNT")):
            with self.assertRaisesRegex(OrderRejected,"exceeds"):
                webull.submit(req(side="sell",qty=4))
        self.assertFalse(trade.order_v3.orders)
    def test_bad_response_is_unknown_not_success(self):
        trade=FakeTrade()
        trade.order_v3.place_order=lambda *_: FakeResponse({"error_code":"DECLINED"})
        with patch.object(webull,"_client",return_value=(trade,"SANDBOX-ACCOUNT")):
            with self.assertRaises(UnknownSubmission):
                webull.submit(req())
    def test_long_client_id_refused(self):
        long_id="X"*40
        r=LimitOrder.make("webull","AMD","buy",1,"5.00",long_id)
        with self.assertRaises(OrderRejected):
            webull.order_payload(r)

if __name__=="__main__":unittest.main()
