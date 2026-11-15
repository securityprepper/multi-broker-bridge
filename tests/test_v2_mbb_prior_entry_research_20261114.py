"""Synthetic tests: no broker/API/host state dependency."""
import datetime as dt
import json
import unittest
from zoneinfo import ZoneInfo
from research.v2_mbb_prior_entry_research_20261114 import classify, evaluate

CT = ZoneInfo("America/Chicago")
def record(day, hour, minute, skips, watches=None, orders=None, cursor=None, gate=True):
    when = dt.datetime.fromisoformat(f"{day}T{hour:02}:{minute:02}:00").replace(tzinfo=CT)
    return {
        "__REALTIME_TIMESTAMP": str(int(when.timestamp() * 1_000_000)),
        "__CURSOR": cursor,
        "MESSAGE": json.dumps({
            "status": "SCAN_COMPLETE", "mode": "PAPER_EXECUTION",
            "gate_allows_new_entries": gate,
            "buy_watch_symbols": watches if watches is not None else [x["symbol"] for x in skips],
            "skipped_buy_reasons": skips, "orders": orders if orders is not None else [],
        }),
    }
def skip(sym, reason):
    return {"symbol": sym, "reason": reason}

class AuditTests(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(classify("PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"), "PRIOR_TRACKED")
        self.assertEqual(classify("NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE"), "NEWS_UNKNOWN")
        self.assertEqual(classify("ENTRY_EXTENSION_BLOCKED_+3.2%_CAP_2.0%"), "EXTENSION")
    def test_day_and_cutoff(self):
        rows = [record("2026-11-12", 9, 0, [skip("AMD", "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")]),
                record("2026-11-13", 13, 15, [skip("AMD", "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")]),
                record("2026-11-13", 13, 14, [skip("AMD", "NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE")])]
        x = evaluate(rows, "2026-11-13")
        self.assertEqual(x["scan_count"], 1)
        self.assertEqual(x["buy_watch_appearances"], 1)
    def test_dedupe_journal_cursor(self):
        r = record("2026-11-13", 8, 0, [skip("AMD", "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")], cursor="once")
        x = evaluate([r, r], "2026-11-13")
        self.assertEqual(x["scan_count"], 1)
        self.assertEqual(x["skipped_appearances"]["PRIOR_TRACKED"], 1)
    def test_distinct_symbols_not_attempts(self):
        rows = [record("2026-11-13", 7, 0, [skip("AMD", "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")]),
                record("2026-11-13", 7, 1, [skip("AMD", "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")])]
        x = evaluate(rows, "2026-11-13")
        self.assertEqual(x["skipped_appearances"]["PRIOR_TRACKED"], 2)
        self.assertEqual(x["unique_symbols_by_reason"]["PRIOR_TRACKED"], 1)
    def test_nonempty_orders_are_not_fills(self):
        x = evaluate([record("2026-11-13", 9, 0, [], watches=[], orders=[{"status": "accepted"}])], "2026-11-13")
        self.assertEqual(x["order_intents_recorded"], 1)
        self.assertTrue(x["all_watch_appearances_accounted_for"])
    def test_unrelated_systemd_messages_are_not_incomplete(self):
        row = record("2026-11-13", 9, 0, [], watches=[])
        row["MESSAGE"] = "Starting service"
        x = evaluate([row], "2026-11-13")
        self.assertEqual(x["incomplete_records"], 0)
        self.assertEqual(x["scan_count"], 0)
    def test_missing_reason_fails_closed(self):
        x = evaluate([record("2026-11-13", 9, 0, [], watches=["AMD"])], "2026-11-13")
        self.assertFalse(x["all_watch_appearances_accounted_for"])

if __name__ == "__main__":
    unittest.main()