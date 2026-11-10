"""Synthetic tests only; no market feed, paper account or broker connection."""
import unittest
from datetime import datetime, timedelta, timezone
from v2_quote_rejection_cause_research import classify_quote, attribute_batch

NOW = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)

def q(age=0, bid="99.50", ask="100.00"):
    return {"t": (NOW-timedelta(seconds=age)).isoformat(),
            "bp": bid, "ap": ask}

class QuoteCauseTests(unittest.TestCase):
    def test_accept(self): self.assertEqual(classify_quote(q(), NOW)[0], "ACCEPT")
    def test_age_boundary(self): self.assertEqual(classify_quote(q(100), NOW)[0], "ACCEPT")
    def test_age_exceeded(self): self.assertEqual(classify_quote(q(100.001), NOW)[0], "STALE_QUOTE")
    def test_future_rejected(self): self.assertEqual(classify_quote(q(-1), NOW)[0], "FUTURE_QUOTE")
    def test_absent(self): self.assertEqual(classify_quote(None, NOW)[0], "ABSENT_QUOTE")
    def test_bad_type(self): self.assertEqual(classify_quote([], NOW)[0], "MALFORMED_QUOTE")
    def test_no_timestamp(self): self.assertEqual(classify_quote({"bp":1,"ap":2},NOW)[0], "INVALID_QUOTE_TIMESTAMP")
    def test_naive_timestamp(self): self.assertEqual(classify_quote({"t":"2026-11-10T17:00:00","bp":1,"ap":2},NOW)[0], "INVALID_QUOTE_TIMESTAMP")
    def test_negative_bid(self): self.assertEqual(classify_quote(q(bid="-1"), NOW)[0], "NONPOSITIVE_PRICE")
    def test_zero_ask(self): self.assertEqual(classify_quote(q(ask="0"), NOW)[0], "NONPOSITIVE_PRICE")
    def test_inverted(self): self.assertEqual(classify_quote(q(bid="101"), NOW)[0], "CROSSED_QUOTE")
    def test_wide_spread(self): self.assertEqual(classify_quote(q(bid="98"), NOW)[0], "WIDE_SPREAD")
    def test_spread_boundary(self): self.assertEqual(classify_quote(q(bid="99"), NOW)[0], "ACCEPT")
    def test_nan(self): self.assertEqual(classify_quote(q(bid="NaN"), NOW)[0], "INVALID_PRICE")
    def test_missing_price(self): self.assertEqual(classify_quote({"t":q()["t"]}, NOW)[0], "INVALID_PRICE")
    def test_invalid_now(self):
        with self.assertRaises(ValueError): classify_quote(q(), NOW.replace(tzinfo=None))
    def test_batch(self):
        a=attribute_batch(["AMD","MU","SOXX"], {"quotes":{"AMD":q(),"MU":q(150)}},NOW)
        self.assertEqual(a["reason_counts"],{"ACCEPT":1,"STALE_QUOTE":1,"ABSENT_QUOTE":1})
        self.assertTrue(a["research_only"])
    def test_batch_bad_envelope(self):
        with self.assertRaises(ValueError): attribute_batch(["AMD"],{"error":"expired"},NOW)
    def test_duplicate_symbol(self):
        with self.assertRaises(ValueError): attribute_batch(["AMD","AMD"],{"quotes":{}},NOW)
    def test_non_symbol(self):
        with self.assertRaises(ValueError): attribute_batch(["AMD;rm -rf /"],{"quotes":{}},NOW)

if __name__=="__main__": unittest.main()
