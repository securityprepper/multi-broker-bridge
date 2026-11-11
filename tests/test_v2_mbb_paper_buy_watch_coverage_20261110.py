"""Offline tests for read-only MBB journal audit."""
import importlib.util
import json
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(\n    "v2_mbb_coverage", str(Path(__file__).resolve().parents[1] / "research" /\n                           "v2_mbb_paper_buy_watch_coverage_20261110.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(candidates, skips, timestamp="1794338700000000", extra=None):
    data = {"buy_watch_symbols": candidates, "skipped_buy_reasons": skips,
            "api_key": "must-not-leak", "cash": 123456789}
    data.update(extra or {})
    return json.dumps({"MESSAGE": json.dumps(data), "__REALTIME_TIMESTAMP": timestamp})


class AuditTests(unittest.TestCase):
    def test_no_raw_sensitive_field_emitted(self):
        o = module.audit([row(["AMD"], [{"symbol": "AMD", "reason": "NO_FRESH_BID_ASK"}])])
        self.assertEqual(o["skipped_by_reason"]["NO_FRESH_BID_ASK"], 1)
        self.assertNotIn("must-not-leak", json.dumps(o))
        self.assertNotIn("123456789", json.dumps(o))

    def test_unrelated_skipped_symbol_not_attributed(self):
        o = module.audit([row(["AMD"], [{"symbol": "MU", "reason": "NO_FRESH_BID_ASK"}])])
        self.assertEqual(o["unexplained_candidate_mentions"], 1)
        self.assertEqual(o["skipped_by_reason"], {})

    def test_bounded_unknown_reason(self):
        o = module.audit([row(["AMD"], [{"symbol": "AMD", "reason": "broker secret 111"}])])
        self.assertEqual(o["skipped_by_reason"], {"OTHER_OR_UNKNOWN": 1})
        self.assertNotIn("secret", json.dumps(o))

    def test_duplicates_in_single_scan_not_double_counted(self):
        e = {"symbol": "AMD", "reason": "NO_FRESH_BID_ASK"}
        o = module.audit([row(["AMD", "AMD"], [e, e])])
        self.assertEqual(o["candidate_mentions"], 1)
        self.assertEqual(o["duplicate_skip_symbol_same_scan"], 1)
        self.assertEqual(o["skipped_by_reason"]["NO_FRESH_BID_ASK"], 1)

    def test_malformed_and_irrelevant_records_ignored(self):
        o = module.audit(["not-json", "{}", json.dumps({"MESSAGE": "{}"}),
                         row(["bad-symbol", "MU"], [])])
        self.assertEqual(o["diagnostic_scans"], 1)
        self.assertEqual(o["candidate_mentions"], 1)
        self.assertEqual(o["unexplained_candidate_mentions"], 1)

    def test_near_limit_flags_truncation(self):
        names=["S"+str(x) for x in range(48)]
        o = module.audit([row(names, [])])
        self.assertEqual(o["potentially_truncated_scans"], 1)

    def test_distinct_symbol_minutes_deduplicates_dual_scans(self):
        x=row(["AMD"], [])
        o = module.audit([x, x])
        self.assertEqual(o["candidate_mentions"], 2)
        self.assertEqual(o["distinct_symbol_minutes"], 1)


if __name__ == "__main__":
    unittest.main()