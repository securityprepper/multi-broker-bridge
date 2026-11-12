import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"research"))
from v2_sip_quote_width_getonly_20261112 import classify_rows,parse

END=datetime(2026,11,9,15,0,0,tzinfo=timezone.utc)
def quote(age, bid="99.9", ask="100", bid_size="4", ask_size="4"):
    return {"t":(END-timedelta(seconds=age)).isoformat(),
            "bp":bid,"ap":ask,"bs":bid_size,"as":ask_size}

class QuoteWidthTests(unittest.TestCase):
    def test_timezone_aware_timestamp_only(self):
        with self.assertRaises(ValueError): parse("2026-11-09T09:30:00")
    def test_no_rows_is_unknown_not_zero_liquidity(self):
        self.assertEqual(classify_rows([],END,4,"entry")["status"],"NO_VALID_DISPLAYED_QUOTES")
    def test_asof_quote_six_seconds_old_is_not_executable(self):
        p=classify_rows([quote(6.7)],END,4,"entry")
        self.assertEqual(p["status"],"STALE_ASOF_QUOTE")
        self.assertEqual(p["last_valid_quote_age_s"],6.7)
    def test_quote_current_and_sized_is_display_only(self):
        self.assertEqual(classify_rows([quote(1)],END,4,"exit")["status"],"FRESH_ASOF_QUOTE")
    def test_under_sized_fresh_display_fails(self):
        self.assertEqual(classify_rows([quote(1,bid_size="2")],END,4,"exit")["status"],
                         "DISPLAYED_SIZE_INSUFFICIENT")
    def test_excludes_future_asof_quotes(self):
        p=classify_rows([quote(-0.5),quote(9)],END,4,"entry")
        self.assertEqual(p["status"],"STALE_ASOF_QUOTE")
        self.assertEqual(p["last_valid_quote_age_s"],9)
    def test_invalid_crossed_quote_excluded(self):
        p=classify_rows([quote(0.3,bid="100.1"),quote(12)],END,4,"entry")
        self.assertEqual(p["last_valid_quote_age_s"],12)
        self.assertIn("bad_cross_or_size",p["invalid"])
    def test_invalid_spread_excluded(self):
        p=classify_rows([quote(0.3,bid="95"),quote(9)],END,4,"entry")
        self.assertEqual(p["last_valid_quote_age_s"],9)
        self.assertIn("spread_over_1pct",p["invalid"])
    def test_rejects_malformed_numeric_price(self):
        p=classify_rows([quote(1,ask="n/a")],END,4,"entry")
        self.assertEqual(p["status"],"NO_VALID_DISPLAYED_QUOTES")
        self.assertIn("parse_error",p["invalid"])
    def test_chooses_latest_valid_asof_not_highest_price(self):
        p=classify_rows([quote(30,bid="110",ask="110.1"),quote(8,bid="90",ask="90.1")],
                        END,4,"entry")
        self.assertEqual(p["last_valid_quote_age_s"],8)
    def test_age_boundary(self):
        self.assertEqual(classify_rows([quote(1.5)],END,4,"entry")["status"],"FRESH_ASOF_QUOTE")
        self.assertEqual(classify_rows([quote(1.501)],END,4,"entry")["status"],"STALE_ASOF_QUOTE")
if __name__=="__main__":unittest.main()
