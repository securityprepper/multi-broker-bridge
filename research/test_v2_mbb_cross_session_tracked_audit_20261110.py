"""Synthetic regression tests; no real broker, DB writes or credentials."""
import importlib.util
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from v2_mbb_cross_session_tracked_audit_20261110 import (
    CROSS_SESSION_SKIP, observed_skips, read_state_readonly, session_day, tracked_state
)


class CrossSessionAuditTests(unittest.TestCase):
    def test_session_overnight_maps_to_next_day(self):
        self.assertEqual(session_day(datetime.fromisoformat("2026-11-09T20:15:00-06:00")), "2026-11-10")

    def test_morning_is_current_day(self):
        self.assertEqual(session_day(datetime.fromisoformat("2026-11-10T00:20:00-06:00")), "2026-11-10")

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):
            session_day(datetime(2026, 11, 10))

    def test_prev_session_entry_carries_over(self):
        st = tracked_state([("AMD", "2026-11-09T07:35:00-06:00")],
                           datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        self.assertEqual(st["prior_session_count"], 1)
        self.assertEqual(st["same_session_count"], 0)
        self.assertFalse(st["broker_flatness_verified"])

    def test_previous_evening_is_same_session(self):
        st = tracked_state([("AMD", "2026-11-09T20:15:00-06:00")],
                           datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        self.assertEqual(st["prior_session_count"], 0)
        self.assertEqual(st["same_session_count"], 1)

    def test_exact_logged_skip_evidence(self):
        st = tracked_state([("MU", "2026-11-09T00:40:00-06:00")],
                           datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        ev = [{"candidate_count": 1, "skipped_buy_reasons": [
            {"symbol": "MU", "reason": CROSS_SESSION_SKIP}]}]
        r = observed_skips(ev, st)
        self.assertEqual(r["observed_prior_session_lockout_symbols"], ["MU"])
        self.assertFalse(r["safe_to_clear_tracking_without_broker_readback"])

    def test_unrelated_quotes_not_misclassified(self):
        st = tracked_state([("MU", "2026-11-09T00:40:00-06:00")],
                           datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        r = observed_skips([{"candidate_count": 1, "skipped_buy_reasons": [
            {"symbol": "MU", "reason": "NO_FRESH_BID_ASK"}]}], st)
        self.assertEqual(r["observed_prior_session_lockout_count"], 0)
        self.assertEqual(r["other_skip_reason_counts"]["NO_FRESH_BID_ASK"], 1)

    def test_no_claim_from_unlogged_skip(self):
        st = tracked_state([("MU", "2026-11-09T00:40:00-06:00")],
                           datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        self.assertEqual(observed_skips([], st)["observed_prior_session_lockout_count"], 0)

    def test_query_only_database(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "strategy.sqlite3"
            conn = sqlite3.connect(path)
            conn.executescript("CREATE TABLE tracked(symbol TEXT, entry_time TEXT);"
                               "CREATE TABLE attempts(trade_date TEXT, side TEXT);")
            conn.execute("INSERT INTO tracked VALUES(?,?)",
                         ("NVDA", "2026-11-09T01:00:00-06:00"))
            conn.commit()
            conn.close()
            result = read_state_readonly(str(path), datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
            self.assertEqual(result["prior_session_count"], 1)
            self.assertEqual(result["current_session_attempts"], 0)
            self.assertEqual(sqlite3.connect(path).execute("SELECT COUNT(*) FROM tracked").fetchone()[0], 1)

    def test_future_invalid_records_are_not_old(self):
        st = tracked_state([("FUT", "2026-11-11T10:00:00-06:00"),
                            ("BAD", "badtime")], datetime.fromisoformat("2026-11-10T00:20:00-06:00"))
        self.assertEqual(st["prior_session_count"], 0)
        self.assertEqual(st["future_or_invalid_count"], 2)


if __name__ == "__main__":
    unittest.main()
