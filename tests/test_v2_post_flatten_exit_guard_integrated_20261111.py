"""Pure fake-broker integration tests, no network/order API."""
import unittest
from unittest.mock import patch
from recommendation_paper_bridge.exit_guard import readback_flatten,flat_id,Unsafe,SubmissionUnknown

REC="TO-20261110-AMD-T1-RUN42"
CID=flat_id(REC)
BASE={"id":"11111111-1111-1111-1111-111111111111","client_order_id":CID,
      "symbol":"AMD","side":"sell","status":"filled","qty":"2","filled_qty":"2"}

class Broker:
    def __init__(self,order=None,positions=None,working=None,acct=None):
        self.order=BASE.copy() if order is None else order
        self.positions=[] if positions is None else positions
        self.working=[] if working is None else working
        self.acct={"id":"PAPER_EXPECTED","trading_blocked":False} if acct is None else acct
        self.calls=[]
    def __call__(self,method,path):
        self.calls.append((method,path))
        if method!="GET":raise AssertionError("a readback must never submit or cancel")
        if path=="/v2/account":return self.acct
        if path.startswith("/v2/orders:by_client_order_id"):return self.order
        if path=="/v2/positions":return self.positions
        if path=="/v2/orders?status=open&limit=500":return self.working
        raise AssertionError(path)

class Tests(unittest.TestCase):
    def read(self,broker,symbol="AMD"):
        with patch.dict("os.environ",{"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"PAPER_EXPECTED"}):
            return readback_flatten(REC,CID,"2",symbol,broker)
    def test_flat_snapshot_does_not_claim_broker_certified_flat(self):
        b=Broker()
        self.assertEqual(self.read(b)["status"],"FLATTEN_SELL_FILLED_FLAT_SNAPSHOT_UNLOCKED")
        self.assertEqual(len(b.calls),4)
        self.assertTrue(all(m=="GET" for m,_ in b.calls))
    def test_residual_position_is_critical(self):
        x=self.read(Broker(positions=[{"symbol":"AMD","qty":"1","side":"long"}]))
        self.assertEqual(x["status"],"CRITICAL_FLATTEN_RESIDUAL_POSITION")
    def test_residual_working_order_is_critical(self):
        x=self.read(Broker(working=[{"id":"O1","symbol":"AMD","side":"buy"}]))
        self.assertEqual(x["status"],"CRITICAL_FLATTEN_WORKING_ORDER")
    def test_other_symbols_do_not_override_flat_snapshot(self):
        b=Broker(positions=[{"symbol":"CAT","qty":"4","side":"long"}],
                 working=[{"id":"O2","symbol":"GS"}])
        self.assertEqual(self.read(b)["status"],"FLATTEN_SELL_FILLED_FLAT_SNAPSHOT_UNLOCKED")
    def test_500_orders_incomplete(self):
        with self.assertRaises(SubmissionUnknown):
            self.read(Broker(working=[{"id":"O"+str(i),"symbol":"GS"} for i in range(500)]))
    def test_bad_position_inventory_fails(self):
        with self.assertRaises(SubmissionUnknown):
            self.read(Broker(positions=[{"symbol":"AMD"}]))
    def test_bad_order_inventory_fails(self):
        with self.assertRaises(SubmissionUnknown):
            self.read(Broker(working=[{"symbol":"AMD"}]))
    def test_wrong_account_fails(self):
        with self.assertRaises(Unsafe):
            self.read(Broker(acct={"id":"OTHER","trading_blocked":False}))
    def test_wrong_symbol_fails(self):
        with self.assertRaises(SubmissionUnknown):
            self.read(Broker(),symbol="MU")
    def test_partial_order_does_not_claim_flat(self):
        b=Broker(order=dict(BASE,status="partially_filled",filled_qty="1"))
        self.assertEqual(self.read(b)["status"],"FLATTEN_UNCONFIRMED")
        self.assertEqual(len(b.calls),2)
    def test_nonnumeric_quantity_fails_closed(self):
        with self.assertRaises(Unsafe):
            self.read(Broker(order=dict(BASE,filled_qty="NaN")))
    def test_broker_order_qty_conflict_fails(self):
        with self.assertRaises(Unsafe):
            self.read(Broker(order=dict(BASE,qty="3")))
    def test_cancel_terminal_sell_does_not_claim_flat(self):
        b=Broker(order=dict(BASE,status="canceled",filled_qty="1"))
        self.assertEqual(self.read(b)["status"],"CRITICAL_FLATTEN_FAILED")
    def test_bad_side_blocks(self):
        with self.assertRaises(SubmissionUnknown):
            self.read(Broker(order=dict(BASE,side="buy")))

if __name__=="__main__":unittest.main()
