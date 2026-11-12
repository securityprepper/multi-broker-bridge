"""Synthetic offline tests: all identifiers are fabricated."""
import unittest
from copy import deepcopy
from research.v2_exact_exit_reason_fill_join_20261112 import attribute_exit

D={"account_id":"PAPER_FAKE","broker_order_id":"SELL-UUID","symbol":"OXY",
   "decision_at":"2026-11-12T15:33:50Z","exit_signal_reason":"trailing peak reversal",
   "strategy_version":"unit-test"}
O={"id":"SELL-UUID","account_id":"PAPER_FAKE","symbol":"OXY","side":"sell",
   "status":"filled","qty":"34","filled_qty":"34",
   "filled_at":"2026-11-12T15:33:50.713050306Z"}
F=[
 {"id":"F1","order_id":"SELL-UUID","account_id":"PAPER_FAKE","symbol":"OXY",
  "side":"sell","qty":"20","transaction_time":"2026-11-12T15:33:50.5Z"},
 {"id":"F2","order_id":"SELL-UUID","account_id":"PAPER_FAKE","symbol":"OXY",
  "side":"sell","qty":"14","transaction_time":"2026-11-12T15:33:50.7Z"}
]

class ExitJoinTests(unittest.TestCase):
    def check(self, modify=None):
        d,o,f=deepcopy(D),deepcopy(O),deepcopy(F)
        if modify: modify(d,o,f)
        return attribute_exit(d,o,f)
    def test_exact_verified(self):
        self.assertEqual(self.check()["status"],"VERIFIED_RECORDED_REASON")
    def test_partials_count_once(self):
        self.assertEqual(self.check()["fill_count"],2)
    def test_accepted_not_filled(self):
        self.assertEqual(self.check(lambda d,o,f:o.update(status="accepted"))["status"],"UNKNOWN")
    def test_order_uuid_mismatch(self):
        self.assertEqual(self.check(lambda d,o,f:d.update(broker_order_id="WRONG"))["status"],"UNKNOWN")
    def test_account_mismatch(self):
        self.assertEqual(self.check(lambda d,o,f:d.update(account_id="OTHER"))["status"],"UNKNOWN")
    def test_missing_activities(self):
        self.assertEqual(self.check(lambda d,o,f:f.clear())["status"],"UNKNOWN")
    def test_duplicate_fill_activity(self):
        self.assertEqual(self.check(lambda d,o,f:f[1].update(id="F1"))["status"],"UNKNOWN")
    def test_partial_order(self):
        self.assertEqual(self.check(lambda d,o,f:o.update(filled_qty="30"))["status"],"UNKNOWN")
    def test_sum_mismatch(self):
        self.assertEqual(self.check(lambda d,o,f:f[1].update(qty="12"))["status"],"UNKNOWN")
    def test_wrong_side(self):
        self.assertEqual(self.check(lambda d,o,f:o.update(side="buy"))["status"],"UNKNOWN")
    def test_future_decision(self):
        self.assertEqual(self.check(lambda d,o,f:d.update(decision_at="2026-11-12T15:40:00Z"))["status"],"UNKNOWN")
    def test_unrecorded_reason(self):
        self.assertEqual(self.check(lambda d,o,f:d.update(exit_signal_reason=None))["status"],"UNKNOWN")

if __name__=="__main__":
    unittest.main()
