"""Fail-closed offline regression for future-date quote false rejection."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research.v2_recommendation_router_quote_receipt_clock_20261111 import (
    InvalidQuote, validate_post_get_quote, old_rule_would_reject,
)

START = datetime(2026, 11, 11, 15, 20, tzinfo=timezone.utc)
RECEIVED = START + timedelta(seconds=6)


def quote(at=START + timedelta(seconds=5), bid="100.04", ask="100.10"):
    return {"t": at.isoformat(), "bp": bid, "ap": ask}


class RecommendationRouterQuoteReceiptTests(unittest.TestCase):
    def validate(self, q, start=START, received=RECEIVED, **kwargs):
        return validate_post_get_quote(q, scan_started_at=start, received_at=received, **kwargs)

    def test_new_valid_quote_after_scan_start_old_rule_false_rejects(self):
        q = quote()
        self.assertTrue(old_rule_would_reject(START + timedelta(seconds=5), START))
        res = self.validate(q)
        self.assertEqual(res["age_milliseconds"], 1000)
        self.assertIs(res["order_authorized"], False)
        self.assertEqual(res["quote_received_at_utc"], RECEIVED.isoformat())

    def test_prior_quote_that_is_still_fresh_is_valid(self):
        res = self.validate(quote(START - timedelta(seconds=20)))
        self.assertEqual(res["age_milliseconds"], 26000)

    def test_future_quote_relative_to_get_receipt_is_rejected(self):
        with self.assertRaisesRegex(InvalidQuote, "future or stale"):
            self.validate(quote(RECEIVED + timedelta(milliseconds=100)))

    def test_stale_46_second_quote_is_rejected(self):
        with self.assertRaisesRegex(InvalidQuote, "future or stale"):
            self.validate(quote(RECEIVED - timedelta(seconds=46)))

    def test_exact_45_second_quote_is_valid(self):
        self.assertEqual(self.validate(quote(RECEIVED - timedelta(seconds=45)))["age_milliseconds"], 45000)

    def test_crossed_quote_rejected(self):
        with self.assertRaisesRegex(InvalidQuote, "crossed"):
            self.validate(quote(bid="100.11"))

    def test_more_than_one_percent_spread_rejected(self):
        with self.assertRaisesRegex(InvalidQuote, "spread"):
            self.validate(quote(bid="98.90", ask="100.10"))

    def test_invalid_and_nan_quote_rejected(self):
        for bid in ["NaN", "0", "-10", "bad"]:
            with self.subTest(bid=bid), self.assertRaises(InvalidQuote):
                self.validate(quote(bid=bid))

    def test_naive_quote_timestamp_rejected(self):
        with self.assertRaises(InvalidQuote):
            self.validate({"t": "2026-11-11T15:20:05", "bp": "100", "ap": "100.1"})

    def test_nonmonotonic_receipt_rejected(self):
        with self.assertRaisesRegex(InvalidQuote, "predates"):
            self.validate(quote(), received=START - timedelta(seconds=1))

    def test_invalid_clock_rejected(self):
        with self.assertRaises(InvalidQuote):
            self.validate(quote(), start=START.replace(tzinfo=None))

    def test_cannot_relax_age_or_spread_limits(self):
        with self.assertRaises(InvalidQuote):
            self.validate(quote(), max_age=timedelta(seconds=46))
        with self.assertRaises(InvalidQuote):
            self.validate(quote(), max_spread=Decimal("0.0101"))

    def test_missing_quote_rejected(self):
        with self.assertRaises(InvalidQuote):
            self.validate(None)


if __name__ == "__main__":
    unittest.main()
