import unittest
from decimal import Decimal
from recommendation_paper_bridge.reconcile import reconcile_one,Unsafe
from recommendation_paper_bridge.exit_guard import flat_id

ROW={"recommendation_id":"TO-20261110-AMD-T1-RUN42","symbol":"AMD",
     "broker_order_id":"parent-uuid","client_order_id":"TO-P-TEST",
     "limit_price":Decimal("100.10"),"profit_target":Decimal("101.60"),
     "stop_loss":Decimal("98.50"),"intended_qty":2,
     "flatten_order_id":"flat-order-uuid"}
def broker_client(correct=True):
    def call(method,path):
        if path.startswith("/v2/orders/parent-uuid"):
            return {"id":"parent-uuid","client_order_id":"TO-P-TEST","symbol":"AMD",
                    "side":"buy","order_class":"bracket","type":"limit",
                    "limit_price":"100.10","filled_qty":"2","status":"filled",
                    "legs":[{"id":"stop-uuid","symbol":"AMD","side":"sell","type":"stop",
                             "stop_price":"98.50","status":"canceled"},
                            {"id":"tp-uuid","symbol":"AMD","side":"sell","type":"limit",
                             "limit_price":"101.60","status":"canceled"}]}
        if path.startswith("/v2/orders/flat-order-uuid"):
            return {"id":"flat-order-uuid","client_order_id":flat_id(ROW["recommendation_id"]) if correct else "WRONG",
                    "symbol":"AMD","side":"sell","type":"market","filled_qty":"2","status":"filled"}
        if "order_id=parent-uuid" in path:return [{"activity_type":"FILL","id":"buy-activity",
              "order_id":"parent-uuid","side":"buy","symbol":"AMD",
              "qty":"2","price":"100","transaction_time":"2026-11-10T16:00:00Z"}]
        if "order_id=flat-order-uuid" in path:return [{"activity_type":"FILL","id":"sell-activity",
              "order_id":"flat-order-uuid","side":"sell","symbol":"AMD",
              "qty":"2","price":"99","transaction_time":"2026-11-10T19:40:00Z"}]
        if "order_id=tp-uuid" in path or "order_id=stop-uuid" in path:return []
        raise AssertionError(path)
    return call
class TestForcedExitReconciliation(unittest.TestCase):
 def test_forced_flat_fill_closes_recommendation(self):
    x=reconcile_one(ROW,broker_client())
    self.assertEqual(x["state"],"CLOSED_NEEDS_FEE_RECON")
    self.assertEqual(x["gross_pnl"],"-2")
    self.assertEqual(x["fill_activity_count"],2)
 def test_mismatched_forced_flat_client_id_refused(self):
    with self.assertRaises(Unsafe):reconcile_one(ROW,broker_client(False))
if __name__=="__main__":unittest.main()
