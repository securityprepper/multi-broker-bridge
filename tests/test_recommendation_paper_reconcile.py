import unittest
from decimal import Decimal
from unittest.mock import Mock
from recommendation_paper_bridge.reconcile import assess,fetch_all_activities,Unsafe,check_parent

ROW={"recommendation_id":"TO-20261110-AMD-T1-RUN42","symbol":"AMD",
     "broker_order_id":"parent-uuid","client_order_id":"TO-P-TEST",
     "limit_price":Decimal("100.10"),"profit_target":Decimal("101.60"),
     "stop_loss":Decimal("98.50"),"intended_qty":2}
def order(filled="2",legs=True):
    x={"id":"parent-uuid","client_order_id":"TO-P-TEST","symbol":"AMD",
       "side":"buy","order_class":"bracket","type":"limit",
       "limit_price":"100.10","status":"filled","filled_qty":filled}
    x["legs"]=[
       {"id":"target-uuid","symbol":"AMD","side":"sell","type":"limit",
        "limit_price":"101.60","status":"filled"},
       {"id":"stop-uuid","symbol":"AMD","side":"sell","type":"stop",
        "stop_price":"98.50","status":"canceled"}] if legs else []
    return x
def fill(i,oid,side,qty="2",price="100"):
    return {"activity_type":"FILL","id":i,"order_id":oid,"symbol":"AMD",
            "side":side,"qty":qty,"price":price,
            "transaction_time":"2026-11-10T16:00:00Z" if side=="buy" else "2026-11-10T16:10:00Z"}
class TestBrokerReconciliation(unittest.TestCase):
 def test_closed_with_verified_gross_only(self):
    r=assess(ROW,order(),[fill("a","parent-uuid","buy"),
                              fill("b","target-uuid","sell",price="101.60")])
    self.assertEqual(r["state"],"CLOSED_NEEDS_FEE_RECON")
    self.assertEqual(r["gross_pnl"],"3.20")
    self.assertIsNone(r["net_pnl"])
    self.assertFalse(r["fees_verified"])
 def test_open_with_active_legs(self):
    p=order()
    p["legs"][0]["status"]="new"
    p["legs"][1]["status"]="new"
    r=assess(ROW,p,[fill("a","parent-uuid","buy")])
    self.assertEqual(r["state"],"OPEN_WITH_BRACKET")
 def test_normal_broker_held_stop_is_protected(self):
    p=order()
    p["legs"][0]["status"]="new"
    p["legs"][1]["status"]="held"
    self.assertEqual(assess(ROW,p,[fill("a","parent-uuid","buy")])["state"],
                     "OPEN_WITH_BRACKET")
 def test_broker_held_target_is_not_active(self):
    p=order()
    p["legs"][0]["status"]="held"
    p["legs"][1]["status"]="held"
    self.assertEqual(assess(ROW,p,[fill("a","parent-uuid","buy")])["state"],
                     "PARTIAL_UNPROTECTED")
 def test_canceled_stop_cannot_be_treated_as_protected(self):
    p=order()
    p["legs"][0]["status"]="new"
    # Full BUY fill + live target + canceled STOP is UNPROTECTED.
    r=assess(ROW,p,[fill("a","parent-uuid","buy")])
    self.assertEqual(r["state"],"PARTIAL_UNPROTECTED")
 def test_nonworking_target_cannot_be_treated_as_protected(self):
    for state in ("rejected","pending_cancel",None):
        p=order()
        p["legs"][0]["status"]=state
        p["legs"][1]["status"]="new"
        with self.subTest(status=state):
            self.assertEqual(assess(ROW,p,[fill("a","parent-uuid","buy")])["state"],
                             "PARTIAL_UNPROTECTED")
 def test_partial_is_unprotected(self):
    r=assess(ROW,order(filled="1",legs=False),[fill("a","parent-uuid","buy","1")])
    self.assertEqual(r["state"],"PARTIAL_UNPROTECTED")
    self.assertTrue(r["unprotected_partial"])
 def test_mismatched_target(self):
    p=order();p["legs"][0]["limit_price"]="101.70"
    with self.assertRaises(Unsafe):assess(ROW,p,[fill("a","parent-uuid","buy")])
 def test_mismatched_stop(self):
    p=order();p["legs"][1]["stop_price"]="99"
    with self.assertRaises(Unsafe):assess(ROW,p,[fill("a","parent-uuid","buy")])
 def test_duplicate_activity_uuid(self):
    a=fill("same","parent-uuid","buy","1")
    with self.assertRaises(Unsafe):assess(ROW,order(),[a,a])
 def test_unknown_other_strategy_fill(self):
    with self.assertRaises(Unsafe):assess(ROW,order(),[fill("a","other-strategy-order","buy")])
 def test_incomplete_broker_fill_page(self):
    with self.assertRaises(Unsafe):assess(ROW,order(),[fill("a","parent-uuid","buy","1")])
 def test_wrong_parent(self):
    p=order();p["client_order_id"]="WRONG"
    with self.assertRaises(Unsafe):check_parent(ROW,p)
 def test_sell_more_than_buy(self):
    with self.assertRaises(Unsafe):assess(ROW,order(),[fill("a","parent-uuid","buy","1"),
                                                       fill("b","stop-uuid","sell","2")])
 def test_unfilled(self):
    p=order(filled="0",legs=False);p["status"]="new"
    self.assertEqual(assess(ROW,p,[])["state"],"UNFILLED")
 def test_specific_fill_order_id(self):
    def response(method,path):
        self.assertIn("order_id=parent-uuid",path)
        return [fill("a","parent-uuid","buy","1")]
    self.assertEqual(len(fetch_all_activities("parent-uuid",response)),1)
 def test_malformed_pages_fail_closed(self):
    with self.assertRaises(Unsafe):fetch_all_activities("parent-uuid",lambda *_:{"error":"oops"})
if __name__=="__main__":unittest.main()
