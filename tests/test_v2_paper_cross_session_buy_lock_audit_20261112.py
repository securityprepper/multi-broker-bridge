"""Offline synthetic tests: no host/broker access."""
import importlib.util
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"research"/"v2_paper_cross_session_buy_lock_audit_20261112.py"
spec=importlib.util.spec_from_file_location("audit",P)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
SRC = 'if symbol in tracked:\n note_skip(symbol,"PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY")\n' + \
      'DELETE FROM tracked WHERE symbol=?\nDecimal(str(status.get("filled_qty",0)))==0'
def event(watch, skips, orders=None):
    return {"status":"SCAN_COMPLETE","buy_watch_symbols":watch,
            "skipped_buy_reasons":skips,"orders":orders or []}
def skip(symbol,reason="PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"):
    return {"symbol":symbol,"reason":reason}

class Audit(unittest.TestCase):
    def test_old_session_confirmed(self):
        x=module.summarize("2026-11-12",{"MU":"2026-11-09"},
                           [event(["MU"],[skip("MU")])],SRC)
        self.assertEqual(x["cross_session_prior_entry_unique_symbols"],1)
        self.assertEqual(x["conclusion"],"CROSS_SESSION_ENTRY_LOCKOUT_CONFIRMED")
    def test_same_day_not_cross_session(self):
        x=module.summarize("2026-11-12",{"MU":"2026-11-12"},
                           [event(["MU"],[skip("MU")])],SRC)
        self.assertEqual(x["cross_session_prior_entry_unique_symbols"],0)
    def test_duplicate_scans_are_appearances_not_unique_stocks(self):
        x=module.summarize("2026-11-12",{"MU":"2026-11-09"},
                           [event(["MU"],[skip("MU")])]*3,SRC)
        self.assertEqual(x["cross_session_prior_entry_skip_appearances"],3)
        self.assertEqual(x["cross_session_prior_entry_unique_symbols"],1)
    def test_not_tracked_is_not_confirmed(self):
        x=module.summarize("2026-11-12",{},
                           [event(["MU"],[skip("MU")])],SRC)
        self.assertEqual(x["conclusion"],"INSUFFICIENT_EVIDENCE")
    def test_extension_is_separate(self):
        x=module.summarize("2026-11-12",{"AMD":"2026-11-09"},
                           [event(["AMD"],[skip("AMD","ENTRY_EXTENSION_BLOCKED_+3.00%_CAP_2.0%")])],SRC)
        self.assertEqual(x["cross_session_prior_entry_skip_appearances"],0)
        self.assertEqual(x["skip_reasons"]["ENTRY_EXTENSION_BLOCKED"],1)
    def test_orders_are_acceptances_not_fills(self):
        x=module.summarize("2026-11-12",{},
                           [event(["X"],[],[{"symbol":"X","side":"buy","status":"pending_new"}])],SRC)
        self.assertEqual(x["logged_order_replies_by_side_status"]["buy:pending_new"],1)
        self.assertEqual(x["orders_placed_by_audit"],0)
    def test_static_news_gap(self):
        x=module.summarize("2026-11-12",{},[],SRC)
        self.assertFalse(x["static_source_direct_news_clearance_found"])
    def test_source_gate_keyword(self):
        x=module.summarize("2026-11-12",{},[],SRC+"\nNEWS_CLEAR_ASOF")
        self.assertTrue(x["static_source_direct_news_clearance_found"])
    def test_missing_source_branch_does_not_claim_confirmed(self):
        x=module.summarize("2026-11-12",{"MU":"2026-11-09"},
                           [event(["MU"],[skip("MU")])],"ordinary code")
        self.assertEqual(x["conclusion"],"INSUFFICIENT_EVIDENCE")
    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            module.summarize("",{},[],SRC)

if __name__=="__main__":unittest.main()