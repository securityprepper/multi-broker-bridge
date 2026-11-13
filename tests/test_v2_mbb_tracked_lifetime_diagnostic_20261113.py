"""Synthetic offline tests for MBB tracked-ledger lifetime diagnostic."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from research.v2_mbb_tracked_lifetime_diagnostic_20261113 import (
    diagnose, read_snapshot,
)


class TrackedLifetimeTests(unittest.TestCase):
    def test_prior_session_is_age_flag_not_fill_proof(self):
        rows = [{"symbol": "AMD", "trade_date": "2026-11-09"}]
        result = diagnose(rows, "2026-11-13")
        self.assertEqual(result["prior_session_tracked_count"], 1)
        self.assertFalse(result["broker_exit_fill_verified_by_this_script"])

    def test_same_session_remains_tracked(self):
        result = diagnose([{"symbol": "NVDA", "trade_date": "2026-11-13"}],
                          "2026-11-13")
        self.assertEqual(result["prior_session_tracked_count"], 0)
        self.assertEqual(result["same_session_tracked_count"], 1)

    def test_missing_attempt_session_is_unknown(self):
        result = diagnose([{"symbol": "MU", "trade_date": None}],
                          "2026-11-13")
        self.assertEqual(result["unmatched_entry_ref_count"], 1)
        self.assertEqual(result["prior_session_tracked_count"], 0)

    def test_future_session_rejected(self):
        with self.assertRaises(ValueError):
            diagnose([{"symbol": "MU", "trade_date": "2026-11-14"}],
                     "2026-11-13")

    def test_readonly_database_and_source_attempt_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "strategy.sqlite3"
            with sqlite3.connect(p) as db:
                db.execute("CREATE TABLE tracked(symbol TEXT, entry_ref TEXT, entry_time TEXT)")
                db.execute("CREATE TABLE attempts(trade_date TEXT,side TEXT,client_id TEXT)")
                db.execute("INSERT INTO tracked VALUES('AMD','MBB-20261109-B-AMD','2026-11-09T13:35:00Z')")
                db.execute("INSERT INTO attempts VALUES('2026-11-09','buy','MBB-20261109-B-AMD')")
            before = p.read_bytes()
            rows = read_snapshot(str(p))
            self.assertEqual(diagnose(rows, "2026-11-13")["prior_session_tracked_count"], 1)
            self.assertEqual(p.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
