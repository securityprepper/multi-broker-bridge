import unittest

from v2_news_clearance_universe_gap_20261116 import audit


class CoverageAuditTests(unittest.TestCase):
    def test_repeated_watch_appearances_not_unique_orders(self):
        scans = [
            {"status": "SCAN_COMPLETE", "buy_watch_symbols": ["AMD", "AVGO"],
             "skipped_buy_reasons": [{"symbol": "AMD", "reason": "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE"},
                                     {"symbol": "AVGO", "reason": "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE"}]},
            {"status": "SCAN_COMPLETE", "buy_watch_symbols": ["AMD"],
             "skipped_buy_reasons": [{"symbol": "AMD", "reason": "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE"}]},
        ]
        v = audit(scans, ["AMD", "FROG"], ["FROG"])
        self.assertEqual(v["candidate_scans"], 2)
        self.assertEqual(v["buy_watch_appearances"], 3)
        self.assertEqual(v["distinct_buy_watch_symbols"], 2)
        self.assertEqual(v["source_covered_distinct"], 1)
        self.assertEqual(v["clear_intersection_distinct"], 0)
        self.assertEqual(v["skipped_reason_counts"]["NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE"], 3)

    def test_no_watch_does_not_become_clear(self):
        v = audit([{"status": "SCAN_COMPLETE", "buy_watch_symbols": [],
                    "skipped_buy_reasons": []}], ["AMD"], [])
        self.assertEqual(v["candidate_scans"], 0)
        self.assertEqual(v["clear_intersection_distinct"], 0)

    def test_clearance_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            audit([], ["AMD"], ["FOO"])

    def test_invalid_scans_fail_closed(self):
        with self.assertRaises(ValueError):
            audit([{"status": "SCAN_COMPLETE", "buy_watch_symbols": "AMD"}], ["AMD"], [])

    def test_ignore_unfinished_scans(self):
        v = audit([{"status": "INCOMPLETE", "buy_watch_symbols": ["AMD"]}], ["AMD"], ["AMD"])
        self.assertEqual(v["distinct_buy_watch_symbols"], 0)


if __name__ == "__main__":
    unittest.main()

