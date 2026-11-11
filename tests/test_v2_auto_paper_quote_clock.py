"""Offline regression against real V2 fetch_bars_and_quotes, no broker/data network."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from multi_broker_bridge import auto_paper

class V2LatestQuoteClock(unittest.TestCase):
    def fetch(self, quote):
        original_scan_time=datetime.now(timezone.utc)-timedelta(seconds=6)
        calls=[]
        def fake_get(url,**kw):
            calls.append(url)
            if "/v2/stocks/bars?" in url:return {"bars":{}}
            if "/v2/stocks/quotes/latest?" in url:return {"quotes":{"AMD":quote}}
            raise AssertionError("unexpected network path")
        with patch.object(auto_paper,"_fetch_json",side_effect=fake_get),patch.object(
            auto_paper,"market_headers",return_value={"Accept":"test/mock"}):
            bars,quotes=auto_paper.fetch_bars_and_quotes(original_scan_time,["AMD"],"sip")
        self.assertEqual(len(calls),2)
        return quotes
    def quote(self,seconds_before_receipt=1,bid="100.00",ask="100.05"):
        return {"t":(datetime.now(timezone.utc)-timedelta(seconds=seconds_before_receipt)).isoformat(),
                "bp":bid,"ap":ask}
    def test_after_scan_before_receipt_now_accepted(self):
        # Was always rejected against fixed scan-start because negative age.
        self.assertIn("AMD",self.fetch(self.quote(seconds_before_receipt=1)))
    def test_actually_future_relative_to_receipt_rejected(self):
        self.assertNotIn("AMD",self.fetch(self.quote(seconds_before_receipt=-10)))
    def test_stale_100s_still_rejected(self):
        self.assertNotIn("AMD",self.fetch(self.quote(seconds_before_receipt=120)))
    def test_wide_spread_still_rejected(self):
        self.assertNotIn("AMD",self.fetch(self.quote(bid="100",ask="103")))
    def test_crossed_quote_still_rejected(self):
        self.assertNotIn("AMD",self.fetch(self.quote(bid="101",ask="100")))
    def test_zero_bid_still_rejected(self):
        self.assertNotIn("AMD",self.fetch(self.quote(bid="0")))
    def test_fresh_fractional_spread_accepted(self):
        self.assertIn("AMD",self.fetch(self.quote(bid="100",ask="100.052")))
if __name__=="__main__": unittest.main()
