"""No-network contract tests for the minimal multi-broker bridge."""
from decimal import Decimal
import os
import tempfile
import unittest
from unittest.mock import patch
from multi_broker_bridge.models import LimitOrder, OrderRejected, UnknownSubmission
from multi_broker_bridge import alpaca, robinhood
from multi_broker_bridge.ledger import connect, reserve, DuplicateOrder

def order(broker="alpaca",side="buy",price="10.00",client="PAPER-001"):
    return LimitOrder.make(broker,"SPY",side,1,price,client)

class OrderSafetyTests(unittest.TestCase):
    def test_basic_preview_request(self):
        self.assertEqual(order().public()["environment"],"PAPER_ONLY")
    def test_invalid_quantity_price_ticker_and_duplicate_id(self):
        for arguments in (dict(price="0"),dict(price="NaN"),dict(price="300.00"),
                          dict(price="1.234")):
            with self.subTest(arguments=arguments),self.assertRaises(OrderRejected):
                order(**arguments)
        with self.assertRaises(OrderRejected):
            LimitOrder.make("alpaca","$FAKE","buy",1,"1.00","PAPER-123")
        with self.assertRaises(OrderRejected):
            LimitOrder.make("alpaca","SPY","buy",-1,"1.00","PAPER-123")
        with self.assertRaises(OrderRejected):
            LimitOrder.make("alpaca","SPY","buy",True,"1.00","PAPER-123")
    def test_ledger_reservation_never_retries(self):
        with tempfile.TemporaryDirectory() as d:
            path=__import__("pathlib").Path(d)/"paper.sqlite3"
            with connect(path) as db:
                reserve(db,order())
                with self.assertRaises(DuplicateOrder):reserve(db,order())
    def test_ledger_rejects_broad_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            path=__import__("pathlib").Path(d)/"paper.sqlite3"
            path.touch()
            path.chmod(0o644)
            with self.assertRaises(OrderRejected):
                with connect(path):pass

class AlpacaTests(unittest.TestCase):
    def test_submit_uses_paper_limit_only(self):
        calls=[]
        def fake(method,path,payload=None):
            calls.append((method,path,payload))
            if path=="/v2/account":
                return {"id":"paperid","trading_blocked":False}
            return {"id":"broker-123","client_order_id":"PAPER-001","status":"accepted"}
        with patch.object(alpaca,"_http",side_effect=fake):
            receipt=alpaca.submit(order())
        self.assertEqual(receipt.broker_order_id,"broker-123")
        self.assertEqual(calls[1][1],"/v2/orders")
        self.assertEqual(calls[1][2]["type"],"limit")
        self.assertFalse(calls[1][2]["extended_hours"])
        self.assertEqual(alpaca.BASE,"https://paper-api.alpaca.markets")
    def test_sell_refused_without_long_position(self):
        calls=[]
        def fake(method,path,payload=None):
            calls.append(path)
            if path=="/v2/account":
                return {"id":"paperid","trading_blocked":False}
            return {"symbol":"SPY","side":"long","qty":"0"}
        with patch.object(alpaca,"_http",side_effect=fake):
            with self.assertRaisesRegex(OrderRejected,"SELL exceeds"):
                alpaca.submit(order(side="sell"))
        self.assertNotIn("/v2/orders",calls)
    def test_account_identity_mismatch_blocks_submission(self):
        with patch.dict(os.environ,{"ALPACA_PAPER_ACCOUNT_ID":"expected"}),patch.object(
                alpaca,"_http",return_value={"id":"other","trading_blocked":False}):
            with self.assertRaisesRegex(OrderRejected,"identity mismatch"):
                alpaca.submit(order())

class RobinhoodTests(unittest.TestCase):
    def test_no_robinhood_paper_order_fabricated(self):
        self.assertFalse(robinhood.check()["paper_trading_available"])
        self.assertFalse(robinhood.shadow_preview(order("robinhood"))["submitted_to_robinhood"])
        with self.assertRaises(OrderRejected):
            robinhood.submit(order("robinhood"))

if __name__=="__main__":unittest.main()
