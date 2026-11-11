import unittest
from datetime import datetime, timedelta, timezone
from research.v2_post_flatten_broker_account_readback_20261111 import verify_post_flatten, _flat_id
from recommendation_paper_bridge.exit_guard import readback_flatten

T = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
RID = "TO-20261111-AMD-T1-DEMO"

class PostFlattenAccountReadbackTests(unittest.TestCase):
    def setUp(self):
        self.order = {"id": "paper-flat-id", "client_order_id": _flat_id(RID),
                      "side": "sell", "symbol": "AMD", "qty": "4",
                      "filled_qty": "4", "status": "filled"}
        self.data = dict(recommendation_id=RID, symbol="AMD",
                         expected_account_id="PAPER-SIM-ACCOUNT",
                         parent_sell_order=self.order,
                         account={"id": "PAPER-SIM-ACCOUNT"},
                         positions=[], open_orders=[],
                         sell_read_at=T-timedelta(seconds=3),
                         positions_read_at=T-timedelta(seconds=2),
                         orders_read_at=T-timedelta(seconds=1),
                         now=T, complete_positions=True, complete_orders=True,
                         exclusive_paper_account_lock_held=True)
    def test_original_order_only_returns_filled_without_position_readback(self):
        # Diagnostic reproduction of the disabled source's missing final-flat assertion.
        out=readback_flatten(RID,_flat_id(RID),"4",
                             lambda method,path:self.order)
        self.assertEqual(out["status"],"FLATTEN_FILLED")
    def run_shadow(self,**changes):
        args=dict(self.data);args.update(changes)
        result=verify_post_flatten(**args)
        self.assertFalse(result["order_authorized"])
        self.assertEqual(result["orders_submitted"],0)
        self.assertEqual(result["broker_calls"],0)
        return result["status"]
    def test_filled_no_position_no_open_orders(self):
        self.assertEqual(self.run_shadow(),"BOUNDED_RECEIVING_PAPER_ACCOUNT_FLAT_VERIFIED")
    def test_remaining_shares_reject_flat(self):
        self.assertEqual(self.run_shadow(positions=[{"symbol":"AMD","qty":"1"}]),
                         "FLATTEN_ORDER_FILLED_BUT_POSITION_STILL_REPORTED")
    def test_unrelated_symbol_does_not_impair_recommendation_flat(self):
        self.assertEqual(self.run_shadow(positions=[{"symbol":"CAT","qty":"2"}]),
                         "BOUNDED_RECEIVING_PAPER_ACCOUNT_FLAT_VERIFIED")
    def test_open_stop_reject_flat(self):
        self.assertEqual(self.run_shadow(open_orders=[{"id":"stop","symbol":"AMD","side":"sell"}]),
                         "FLATTEN_ORDER_FILLED_BUT_WORKING_ORDER_REMAINS")
    def test_open_buy_reject_flat(self):
        self.assertEqual(self.run_shadow(open_orders=[{"id":"buy","symbol":"AMD","side":"buy"}]),
                         "FLATTEN_ORDER_FILLED_BUT_WORKING_ORDER_REMAINS")
    def test_wrong_account(self):
        self.assertEqual(self.run_shadow(account={"id":"OTHER"}),"UNKNOWN_WRONG_ACCOUNT_OR_SOURCE")
    def test_missing_lock(self):
        self.assertEqual(self.run_shadow(exclusive_paper_account_lock_held=False),
                         "UNKNOWN_INCOMPLETE_OR_UNLOCKED_RECEIVING_INVENTORY")
    def test_incomplete_inventory(self):
        self.assertEqual(self.run_shadow(complete_orders=False),
                         "UNKNOWN_INCOMPLETE_OR_UNLOCKED_RECEIVING_INVENTORY")
    def test_pre_filled_order_snapshot_does_not_prove_flat(self):
        self.assertEqual(self.run_shadow(positions_read_at=T-timedelta(seconds=4)),
                         "UNKNOWN_STALE_OR_PRESELL_INVENTORY")
    def test_stale_inventory(self):
        self.assertEqual(self.run_shadow(orders_read_at=T-timedelta(seconds=30)),
                         "UNKNOWN_STALE_OR_PRESELL_INVENTORY")
    def test_partial_fill(self):
        self.assertEqual(self.run_shadow(parent_sell_order={**self.order,"filled_qty":"3"}),
                         "UNKNOWN_PARTIAL_OR_INVALID_FLATTEN_FILL")
    def test_invalid_nan_qty(self):
        self.assertEqual(self.run_shadow(parent_sell_order={**self.order,"qty":"NaN"}),
                         "UNKNOWN_INVALID_BROKER_READBACK")
    def test_unknown_sell_origin(self):
        self.assertEqual(self.run_shadow(parent_sell_order={**self.order,"client_order_id":"other"}),
                         "UNKNOWN_UNVERIFIED_FLATTEN_ORDER")
    def test_overfull_open_orders(self):
        self.assertEqual(self.run_shadow(open_orders=[{"id":str(i),"symbol":"X"} for i in range(500)]),
                         "UNKNOWN_INCOMPLETE_OR_UNLOCKED_RECEIVING_INVENTORY")
    def test_missing_order_id(self):
        self.assertEqual(self.run_shadow(open_orders=[{"symbol":"AMD"}]),
                         "UNKNOWN_MALFORMED_OPEN_ORDER_INVENTORY")

if __name__ == "__main__":
    unittest.main()
