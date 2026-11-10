import unittest
from datetime import datetime,timezone
from decimal import Decimal
from unittest.mock import patch
from recommendation_paper_bridge.exit_guard import (
    plan,exclusively_owned,readback_flatten,flat_id,cancel_verified,Unsafe
)

ROW={"recommendation_id":"TO-20261110-AMD-T1-RUN42","symbol":"AMD",
     "broker_order_id":"parent-uuid","client_order_id":"TO-P-TEST",
     "limit_price":Decimal("100.10"),"profit_target":Decimal("101.60"),
     "stop_loss":Decimal("98.50"),"intended_qty":2}
def order(filled="2",status="filled",legs=True):
    p={"id":"parent-uuid","client_order_id":"TO-P-TEST","symbol":"AMD",
       "side":"buy","order_class":"bracket","type":"limit",
       "limit_price":"100.10","status":status,"filled_qty":filled}
    p["legs"]=([
       {"id":"take-profit-uuid","symbol":"AMD","side":"sell","type":"limit",
        "limit_price":"101.60","status":"new"},
       {"id":"stop-loss-uuid","symbol":"AMD","side":"sell","type":"stop",
        "stop_price":"98.50","status":"new"}] if legs else [])
    return p
def activity(id="fill1",q="2"):
    return [{"activity_type":"FILL","id":id,"order_id":"parent-uuid",
             "symbol":"AMD","side":"buy","qty":q,"price":"100",
             "transaction_time":"2026-11-10T15:00:00Z"}]
def when(hour,minute):
    # November standard-time UTC 19:40 = Chicago 13:40.
    return datetime(2026,11,10,hour,minute,tzinfo=timezone.utc)
def positions(q):
    return [{"symbol":"AMD","qty":q,"side":"long"}]
class TestExit(unittest.TestCase):
 def test_hold_while_protected_pre_cutoff(self):
    x=plan(ROW,order(),activity(),positions("2"),[],when(18,30))
    self.assertEqual(x["action"],"NONE")
 def test_unfilled_cancel_after_1315(self):
    x=plan(ROW,order("0","new",False),[],[],[],when(19,16))
    self.assertEqual(x["action"],"CANCEL_UNFILLED_PARENT")
 def test_exclusive_1340_flat(self):
    p=order()
    x=plan(ROW,p,activity(),positions("2"),p["legs"],when(19,40))
    self.assertEqual(x["action"],"FLATTEN_EXCLUSIVE_PAPER")
    self.assertEqual(x["quantity"],"2")
    self.assertEqual(len(x["stop_bracket_child_ids"]),2)
 def test_partial_requires_early_exit(self):
    x=plan(ROW,order("1","partially_filled",False),activity(q="1"),
           positions("1"),[],when(17,30))
    self.assertEqual(x["action"],"FLATTEN_EXCLUSIVE_PAPER")
    self.assertEqual(x["reason"],"PARTIAL_UNPROTECTED")
 def test_shared_ownership_fails(self):
    with self.assertRaises(Unsafe):
        plan(ROW,order(),activity(),positions("4"),order()["legs"],when(19,40))
 def test_foreign_open_order_fails(self):
    foreign={"id":"other-uuid","symbol":"AMD","status":"new"}
    with self.assertRaises(Unsafe):
        plan(ROW,order(),activity(),positions("2"),[foreign],when(19,40))
 def test_stop_after_market_closed(self):
    x=plan(ROW,order(),activity(),positions("2"),order()["legs"],when(22,30))
    self.assertEqual(x["action"],"SAFETY_ESCALATE")
 def test_done_exit_never_sells_again(self):
    p=order()
    a=activity()+[{"activity_type":"FILL","id":"exit1","order_id":"take-profit-uuid",
                    "symbol":"AMD","side":"sell","qty":"2","price":"101.60",
                    "transaction_time":"2026-11-10T19:30:00Z"}]
    self.assertEqual(plan(ROW,p,a,[],[],when(19,40))["action"],"NONE")
 def test_flat_readback_filled(self):
    id=flat_id(ROW["recommendation_id"])
    def remote(method,path):
        if path=="/v2/account":return {"id":"EXPECTED","trading_blocked":False}
        return {"id":"ORDERID","client_order_id":id,"status":"filled","filled_qty":"2"}
    with patch.dict("os.environ",{"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"EXPECTED"}):
        self.assertEqual(readback_flatten(ROW["recommendation_id"],id,"2",remote)["status"],
                         "FLATTEN_FILLED")
 def test_flat_readback_unfilled(self):
    id=flat_id(ROW["recommendation_id"])
    def remote(method,path):
        if path=="/v2/account":return {"id":"EXPECTED","trading_blocked":False}
        return {"id":"ORDERID","client_order_id":id,"status":"new","filled_qty":"0"}
    with patch.dict("os.environ",{"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"EXPECTED"}):
        self.assertEqual(readback_flatten(ROW["recommendation_id"],id,"2",remote)["status"],
                         "FLATTEN_UNCONFIRMED")
 def test_flat_wrong_client_id(self):
    with self.assertRaises(Unsafe):
        readback_flatten(ROW["recommendation_id"],"WRONG","2",lambda *_:self.fail())
 def test_cancel_requires_broker_readback(self):
    oid="11111111-1111-1111-1111-111111111111"
    def remote(method,path):
        return {} if method=="DELETE" else {"id":oid,"status":"canceled"}
    self.assertEqual(cancel_verified(oid,remote)["status"],"canceled")
 def test_cancel_rejects_non_uuid(self):
    with self.assertRaises(Unsafe):cancel_verified("notuuid",lambda *_:self.fail())
if __name__=="__main__": unittest.main()
