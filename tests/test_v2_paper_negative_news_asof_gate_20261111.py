"""Synthetic tests for research-only negative-news as-of gate; NO broker access."""
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo
import unittest

from research.v2_paper_negative_news_asof_gate_20261111 import (
    evaluate_news_asof, ADVERSE, WATCH, UNKNOWN, CLEAR, CATEGORIES, yesterday_today_start,
)

NOW = datetime(2026, 11, 11, 20, 30, tzinfo=timezone.utc)

def iso(n):
    return (NOW + timedelta(seconds=n)).isoformat()

def fixtures():
    i = {"verified": True, "symbol": "AMD", "exchange": "NASDAQ",
         "issuer_cik": "0000002488", "first_observed_at": iso(-120)}
    cover = []
    for src, categories in [
        ("licensed_news", set(CATEGORIES)),
        ("sec_edgar", {"earnings", "guidance", "dilution", "restatement", "liquidity",
                       "litigation", "regulatory", "corporate_development"}),
        ("issuer_ir", {"earnings", "guidance", "corporate_development"}),
    ]:
        cover.append({"symbol": "AMD", "issuer_cik": "0000002488",
                      "source": src, "verified_complete": True,
                      "source_reference": f"synthetic:{src}",
                      "content_hash": "abcdef0123456789",
                      "first_observed_at": iso(-20),
                      "coverage_since": yesterday_today_start(NOW).isoformat(),
                      "coverage_through": iso(-10),
                      "categories": sorted(categories)})
    return {"symbol": "AMD", "exchange": "NASDAQ", "issuer_cik": "0000002488",
            "asof_utc": iso(0), "identity": i, "coverage": cover, "evidence": []}

def event(category="guidance", status="material_adverse_verified"):
    return {"symbol": "AMD", "issuer_cik": "0000002488", "source": "issuer_ir",
            "published_at": iso(-90), "first_observed_at": iso(-60),
            "source_reference": "synthetic:issuer", "content_hash": "123456",
            "status": status, "category": category}

class NewsGate(unittest.TestCase):
    def test_full_signed_style_coverage_clears_only_in_research(self):
        x = evaluate_news_asof(**fixtures())
        self.assertEqual(x["status"], CLEAR)
        self.assertTrue(x["paper_order_eligible"])
    def test_no_coverage_is_not_no_bad_news(self):
        a = fixtures(); a["coverage"] = []
        self.assertEqual(evaluate_news_asof(**a)["status"], UNKNOWN)
    def test_material_adverse_vetoes_even_without_complete_coverage(self):
        a = fixtures(); a["coverage"] = []; a["evidence"] = [event()]
        self.assertEqual(evaluate_news_asof(**a)["status"], ADVERSE)
    def test_pending_allegation_review_only(self):
        a = fixtures(); a["evidence"] = [event(status="pending_allegation")]
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_contradiction_review_only(self):
        a = fixtures(); a["evidence"] = [event(status="contradictory")]
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_future_article_cannot_retroactively_veto(self):
        a = fixtures(); e = event()
        e["first_observed_at"] = iso(120)
        a["evidence"] = [e]
        self.assertEqual(evaluate_news_asof(**a)["status"], CLEAR)
    def test_other_issuer_same_ticker_is_not_adverse(self):
        a = fixtures(); e = event(); e["issuer_cik"] = "0000111111"
        a["evidence"] = [e]
        self.assertEqual(evaluate_news_asof(**a)["status"], CLEAR)
    def test_missing_first_seen_not_clean(self):
        a = fixtures(); e = event(); del e["first_observed_at"]
        a["evidence"] = [e]
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_missing_news_category_coverage_unknown(self):
        a = fixtures(); a["coverage"][0]["categories"].remove("analyst_downgrade")
        self.assertEqual(evaluate_news_asof(**a)["status"], UNKNOWN)
    def test_stale_issuer_coverage_unknown(self):
        a = fixtures(); a["coverage"][2]["first_observed_at"] = iso(-600)
        self.assertEqual(evaluate_news_asof(**a)["status"], UNKNOWN)
    def test_identity_disambiguation_required(self):
        a = fixtures(); a["identity"]["issuer_cik"] = "0000000001"
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_future_identity_not_valid_at_signal(self):
        a = fixtures(); a["identity"]["first_observed_at"] = iso(60)
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_headline_only_article_not_clear(self):
        a = fixtures(); e = event(status="verified_nonmaterial"); del e["content_hash"]
        a["evidence"] = [e]
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_unknown_classification_not_clean(self):
        a = fixtures(); a["evidence"] = [event(status="unknown")]
        self.assertEqual(evaluate_news_asof(**a)["status"], WATCH)
    def test_old_adverse_news_day_before_yesterday_is_excluded(self):
        a = fixtures()
        old = event()
        old["published_at"] = (yesterday_today_start(NOW)-timedelta(seconds=1)).isoformat()
        old["first_observed_at"] = old["published_at"]
        a["evidence"] = [old]
        r = evaluate_news_asof(**a)
        self.assertEqual(r["status"], CLEAR)
        self.assertEqual(r["adverse_news_window"], "YESTERDAY_AND_TODAY_AMERICA_CHICAGO")
        self.assertEqual(r["adverse_news_from_utc"], yesterday_today_start(NOW).isoformat())
    def test_at_previous_calendar_midnight_is_included(self):
        a=fixtures(); e=event()
        e["published_at"]=yesterday_today_start(NOW).isoformat()
        e["first_observed_at"]=(yesterday_today_start(NOW)+timedelta(seconds=1)).isoformat()
        a["evidence"]=[e]
        self.assertEqual(evaluate_news_asof(**a)["status"], ADVERSE)
    def test_today_news_is_included(self):
        a=fixtures();e=event()
        beginning=datetime.combine(NOW.astimezone(ZoneInfo("America/Chicago")).date(),
                      time.min,ZoneInfo("America/Chicago")).astimezone(timezone.utc)
        e["published_at"]=beginning.isoformat()
        e["first_observed_at"]=(beginning+timedelta(seconds=5)).isoformat()
        a["evidence"]=[e]
        self.assertEqual(evaluate_news_asof(**a)["status"], ADVERSE)
    def test_only_yesterday_today_coverage_is_enough(self):
        self.assertEqual(evaluate_news_asof(**fixtures())["status"],CLEAR)
        a=fixtures()
        for row in a["coverage"]:
            row["coverage_since"]=(yesterday_today_start(NOW)+timedelta(seconds=1)).isoformat()
        self.assertEqual(evaluate_news_asof(**a)["status"],UNKNOWN)
    def test_weekend_monday_means_sunday_and_monday_not_friday(self):
        ct=ZoneInfo("America/Chicago")
        monday=datetime(2026,11,16,10,0,tzinfo=ct)
        self.assertEqual(yesterday_today_start(monday).astimezone(ct).date().isoformat(),"2026-11-15")
        self.assertEqual(yesterday_today_start(monday).astimezone(ct).hour,0)
    def test_spring_dst_uses_own_midnight_offsets(self):
        ct=ZoneInfo("America/Chicago")
        d=datetime(2027,3,15,10,0,tzinfo=ct)
        yesterday=yesterday_today_start(d).astimezone(ct)
        self.assertEqual((yesterday.year,yesterday.month,yesterday.day,yesterday.hour),(2027,3,14,0))
        self.assertEqual(yesterday.utcoffset(),timedelta(hours=-6))
    def test_fall_dst_uses_previous_day_midnight(self):
        ct=ZoneInfo("America/Chicago")
        d=datetime(2026,11,2,10,0,tzinfo=ct)
        yesterday=yesterday_today_start(d).astimezone(ct)
        self.assertEqual((yesterday.year,yesterday.month,yesterday.day,yesterday.hour),(2026,11,1,0))
        self.assertEqual(yesterday.utcoffset(),timedelta(hours=-5))
    def test_old_news_lacking_received_time_is_out_of_scope(self):
        a=fixtures();e=event()
        e["published_at"]=(yesterday_today_start(NOW)-timedelta(days=5)).isoformat()
        e.pop("first_observed_at")
        a["evidence"]=[e]
        self.assertEqual(evaluate_news_asof(**a)["status"],CLEAR)
    def test_new_news_lacking_receipt_is_review_only(self):
        a=fixtures();e=event();e.pop("first_observed_at")
        a["evidence"]=[e]
        self.assertEqual(evaluate_news_asof(**a)["status"],WATCH)
    def test_missing_news_manifest_entirely_unknown(self):
        a = fixtures(); a["coverage"] = None
        self.assertEqual(evaluate_news_asof(**a)["status"], UNKNOWN)

if __name__ == "__main__":
    unittest.main()
