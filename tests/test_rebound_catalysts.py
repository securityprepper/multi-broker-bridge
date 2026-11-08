"""Causal adverse earnings/news catalyst filter tests; no external requests."""
import unittest
from datetime import datetime,timedelta,timezone

from multi_broker_bridge.rebound_catalysts import screen

NOW=datetime(2026,2,4,21,30,tzinfo=timezone.utc)


def item(headline,age_hours=2,updated_hours=None):
    created=NOW-timedelta(hours=age_hours)
    updated=created if updated_hours is None else NOW-timedelta(hours=updated_hours)
    return {"created_at":created.isoformat(),
            "updated_at":updated.isoformat(),
            "headline":headline,"symbols":["AMD"]}


class CompanyCatalystTests(unittest.TestCase):
    def test_two_independent_negative_amd_earnings_headlines_block(self):
        data=[
            item("AMD Stock Slips Following Q4 Earnings: What You Need To Know"),
            item("AMD China AI Sales Lift Results But Stir Wall Street Doubt"),
        ]
        result=screen(data,NOW)
        self.assertTrue(result["veto"])
        self.assertEqual(result["affected_anchors"],("AMD",))
        self.assertEqual(result["distinct_adverse_company_headlines"]["AMD"],2)

    def test_generic_sector_selloff_news_does_not_disqualify_rebounds(self):
        data=[item("Chip Stocks Plunge as Nasdaq Slides"),
              item("Semiconductor Sector Down After Weak AI Market Session")]
        self.assertFalse(screen(data,NOW)["veto"])

    def test_company_earnings_without_adverse_wording_does_not_block(self):
        data=[item("AMD Announces New Quarter Revenue Growth"),
              item("Micron Earnings Beat Wall Street Expectations")]
        self.assertFalse(screen(data,NOW)["veto"])

    def test_article_revision_after_the_signal_is_not_backdated(self):
        data=[item("AMD Earnings Miss Outlook",age_hours=2,updated_hours=-2),
              item("AMD Earnings Lower Guidance",age_hours=3,updated_hours=1)]
        self.assertFalse(screen(data,NOW)["veto"])

    def test_same_headline_reprint_not_independent(self):
        data=[item("AMD Earnings Outlook Draws Wall Street Doubt"),
              item("AMD Earnings Outlook Draws Wall Street Doubt")]
        self.assertFalse(screen(data,NOW)["veto"])

    def test_news_not_yet_published_cannot_be_used(self):
        data=[item("AMD Earnings Outlook Draws Wall Street Doubt",age_hours=-2),
              item("AMD Earnings Revenue Weak",age_hours=1)]
        self.assertFalse(screen(data,NOW)["veto"])

    def test_wrong_named_company_never_blocks_semiconductor_anchor(self):
        data=[item("Apple Earnings Forecast Cut"),
              item("Microsoft Earnings Outlook Weak")]
        self.assertFalse(screen(data,NOW)["veto"])


if __name__=="__main__":
    unittest.main()
