"""Offline synthetic tests for entry timestamp and high-water provenance."""
import unittest
from research.v2_prefill_highwater_and_bar_peak_audit_20261112 import (
    prefill_eligible_minute_starts, trade_print_peak_boundary
)

class ProvenanceTests(unittest.TestCase):
    def test_panw_crosses_bar_start(self):
        self.assertEqual(prefill_eligible_minute_starts(
            "2026-11-09T16:49:40.187293+00:00",
            "2026-11-09T16:50:43.110397Z"), ["2026-11-09T16:50:00+00:00"])
    def test_s_crosses_bar_start(self):
        self.assertEqual(len(prefill_eligible_minute_starts(
            "2026-11-11T15:10:30.197146+00:00",
            "2026-11-11T15:11:16.906916Z")), 1)
    def test_oxy_no_prefill_exposure(self):
        self.assertEqual(prefill_eligible_minute_starts(
            "2026-11-12T14:48:40.183048+00:00",
            "2026-11-12T14:48:53.801367Z"), [])
    def test_exact_boundary_excluded(self):
        self.assertEqual(prefill_eligible_minute_starts(
            "2026-11-12T14:48:40Z", "2026-11-12T14:49:00Z"), [])
    def test_multiple_prefill_bar_starts(self):
        self.assertEqual(len(prefill_eligible_minute_starts(
            "2026-11-12T14:48:40Z", "2026-11-12T14:50:30Z")), 2)
    def test_ordering_fails_closed(self):
        with self.assertRaises(ValueError):
            prefill_eligible_minute_starts(
                "2026-11-12T14:49:00Z", "2026-11-12T14:48:00Z")
    def test_oxy_boundary_not_proof_of_signal(self):
        r=trade_print_peak_boundary("57.64","58.175")
        self.assertTrue(r["trade_high_armed"])
        self.assertEqual(r["trade_high_close_boundary"],"57.884125")
        self.assertIsNone(r["signal_close_condition"])
        self.assertFalse(r["bid_peak_confirmed"])
        self.assertFalse(r["fill_inference_permitted"])
    def test_trade_high_signal_condition_separate(self):
        r=trade_print_peak_boundary("57.64","58.175","57.88")
        self.assertTrue(r["signal_close_condition"])
        self.assertFalse(r["bid_peak_confirmed"])
    def test_no_trigger_from_higher_close(self):
        r=trade_print_peak_boundary("57.64","58.175","58.00")
        self.assertFalse(r["signal_close_condition"])
    def test_bid_peak_requires_independent_data(self):
        self.assertFalse(trade_print_peak_boundary(
            "57.64","58.175","57.81","57.80")["bid_peak_confirmed"])
        self.assertTrue(trade_print_peak_boundary(
            "57.64","58.175","57.81","58.10")["bid_peak_confirmed"])
    def test_nonpositive_price_rejected(self):
        with self.assertRaises(ValueError):
            trade_print_peak_boundary("57.64","0")
    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            prefill_eligible_minute_starts("2026-11-12T14:48:40","2026-11-12T14:49:00Z")

if __name__=="__main__":
    unittest.main()


[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]