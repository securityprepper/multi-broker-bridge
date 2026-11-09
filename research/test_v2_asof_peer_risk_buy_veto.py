"""Causal checks for V2 peer confirmation and risk-first admissions."""
import unittest
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from research.v2_asof_peer_risk_buy_veto import (
    ET, byday_warnings, peer_confirmation, entry_admitted, asof_active,
    summarize_entry, period_tag, OPEN,
)


class V2RiskVetoTests(unittest.TestCase):
    def at(self, hour, minute, day=9):
        return datetime(2026, 11, day, hour, minute, tzinfo=ET)

    def test_baseline_immediate(self):
        first = self.at(8, 5)
        self.assertEqual(first, peer_confirmation(first, {}, "AMD", date(2026, 11, 9), 0, "sticky"))

    def test_future_peer_is_never_early_input(self):
        first = self.at(8, 5)
        later = self.at(9, 15)
        self.assertEqual(later, peer_confirmation(first, {"MU": later}, "AMD", date(2026, 11, 9), 1, "sticky"))
        self.assertNotEqual(first, peer_confirmation(first, {"MU": later}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_ignores_peer_after_open(self):
        first = self.at(8, 5)
        self.assertIsNone(peer_confirmation(first, {"MU": self.at(9, 31)}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_prior_evening_confirmation_retains_actual_timestamp(self):
        first = self.at(17, 0, day=8)
        peer = self.at(17, 20, day=8)
        self.assertEqual(peer, peer_confirmation(first, {"MU": peer}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_previous_evening_stale_under_fresh30(self):
        first = self.at(17, 0, day=8)
        peer = self.at(8, 30, day=9)
        self.assertIsNone(peer_confirmation(first, {"MU": peer}, "AMD", date(2026, 11, 9), 1, "fresh30"))
        self.assertEqual(peer, peer_confirmation(first, {"MU": peer}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_target_after_open_not_preopen(self):
        self.assertIsNone(peer_confirmation(self.at(9, 35), {"MU": self.at(8, 0)}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_missing_target_never_confirmed_by_peers(self):
        self.assertIsNone(peer_confirmation(None, {"MU": self.at(8, 0)}, "AMD", date(2026, 11, 9), 1, "sticky"))

    def test_peer_threshold_rechecks_as_more_warnings_arrive(self):
        first = self.at(8, 0)
        signals = {"MU": self.at(8, 5), "WDC": self.at(8, 15), "INTC": self.at(8, 35)}
        self.assertEqual(self.at(8, 15), peer_confirmation(first, signals, "AMD", date(2026, 11, 9), 2, "sticky"))
        self.assertEqual(self.at(8, 35), peer_confirmation(first, signals, "AMD", date(2026, 11, 9), 3, "sticky"))

    def test_fresh30_requires_current_peer_and_target(self):
        first = self.at(8, 0)
        signals = {"MU": self.at(8, 5), "WDC": self.at(8, 35)}
        self.assertIsNone(peer_confirmation(first, signals, "AMD", date(2026, 11, 9), 2, "fresh30"))

    def test_no_future_same_day_alert_affects_buy(self):
        at = self.at(9, 40)
        active = asof_active({"AMD": self.at(9, 35), "MU": self.at(9, 45), "SOXX": self.at(9, 40)}, at, "AMD")
        self.assertEqual(active, {"own_risk": True, "other_risks": 1, "soxx_risk": True})

    def test_risk_admission_policy_shapes(self):
        self.assertTrue(entry_admitted("first_only", True, 4, True))
        self.assertFalse(entry_admitted("own_risk_clear", True, 0, False))
        self.assertTrue(entry_admitted("own_risk_clear", False, 4, True))
        self.assertFalse(entry_admitted("zero_other_risks", False, 2, False))
        self.assertTrue(entry_admitted("fewer_than_three_other_risks", False, 2, True))
        self.assertFalse(entry_admitted("fewer_than_two_other_risks", False, 2, True))
        self.assertFalse(entry_admitted("soxx_risk_clear", False, 1, True))
        with self.assertRaises(ValueError):
            entry_admitted("unknown", False, 0, False)

    def test_date_split_is_fixed_not_future_fit(self):
        self.assertEqual(period_tag("2026-08-31"), "earlier")
        self.assertEqual(period_tag("2026-09-01"), "later")

    def test_day_equal_counts_skipped_day_as_zero(self):
        rows = [
            {"period": "later", "net_pct": 1.0, "major_up": True, "major_down": False, "allow": {"own_risk_clear": True}},
            {"period": "later", "net_pct": -2.0, "major_up": False, "major_down": True, "allow": {"own_risk_clear": False}},
        ]
        result = summarize_entry(rows, "own_risk_clear", "later")
        self.assertEqual(result["baseline_signal_days"], 2)
        self.assertEqual(result["admitted"], 1)
        self.assertEqual(result["day_equal_net_pct"], 0.5)
        self.assertEqual(result["skipped_major_losers"], 1)
        self.assertEqual(result["avoided_negative_trade_proxy_pct_points"], 2.0)

    def test_ledger_ignores_no_warning_and_rejects_naive(self):
        rows = [
            {"day": "2026-11-09", "sym": "AMD", "preopen_union": None},
            {"day": "2026-11-09", "sym": "MU", "preopen_union": {"asof": self.at(8, 0).isoformat()}}
        ]
        ledger = byday_warnings(rows, "preopen_union")
        self.assertEqual(set(ledger["2026-11-09"]), {"MU"})
        rows[1]["preopen_union"]["asof"] = "2026-11-09T08:00:00"
        with self.assertRaises(ValueError):
            byday_warnings(rows, "preopen_union")


if __name__ == "__main__":
    unittest.main()
