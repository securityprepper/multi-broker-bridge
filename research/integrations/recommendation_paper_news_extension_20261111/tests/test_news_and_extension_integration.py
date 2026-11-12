import unittest
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from unittest.mock import patch
from recommendation_paper_bridge import bridge,news_clearance,news_eligibility,entry_tracking
from test_router_transaction import NOW, ROW, BrokerFake, FakeDB, REC

def doc(now=NOW, symbol="AMD"):
    seen=(now-timedelta(seconds=9)).isoformat()
    since=(now-timedelta(days=35)).isoformat()
    def cov(source,cats):
        return dict(symbol=symbol,issuer_cik="0000002488",source=source,
                    verified_complete=True,first_observed_at=seen,
                    coverage_since=since,coverage_through=seen,
                    source_reference="trusted:"+source,content_hash="sha-"+source,
                    categories=sorted(cats))
    return dict(schema_version=1,symbol=symbol,exchange="NASDAQ",
                issuer_cik="0000002488",
                producer="trusted_issuer_sec_news_attestor_v1",
                produced_at_utc=seen,
                identity={"verified":True,"symbol":symbol,"exchange":"NASDAQ",
                          "issuer_cik":"0000002488","first_observed_at":seen},
                coverage=[
                    cov("sec_edgar",{"earnings","guidance","dilution","restatement",
                                     "liquidity","litigation","regulatory","corporate_development"}),
                    cov("issuer_ir",{"earnings","guidance","corporate_development"}),
                    cov("licensed_news",news_eligibility.CATEGORIES)],
                evidence=[])

def loader(d):
    return lambda symbol: (deepcopy(d),"f"*64)

class NewsChecks(unittest.TestCase):
    def test_clear_only_with_complete_verified_issuer_sources(self):
        got=news_clearance.require_clear("AMD",NOW,loader(doc()))
        self.assertEqual(got["status"],"NEWS_CLEAR_ASOF")
        self.assertEqual(got["evidence_sha256"],"f"*64)
    def test_unavailable_document_fails_closed(self):
        with self.assertRaises(news_clearance.NewsBlocked) as caught:
            news_clearance.require_clear("AMD",NOW,lambda x: (_ for _ in ()).throw(OSError()))
        # The real protected read handles an absent file; an injected broken
        # test reader is deliberately not a clearance provider.
    def test_incomplete_news_coverage_unknown(self):
        d=doc();d["coverage"]=d["coverage"][:2]
        with self.assertRaises(news_clearance.NewsBlocked) as caught:
            news_clearance.require_clear("AMD",NOW,loader(d))
        self.assertEqual(caught.exception.status,"NEWS_UNKNOWN")
    def test_older_attestation_unknown(self):
        d=doc();d["produced_at_utc"]=(NOW-timedelta(minutes=4)).isoformat()
        with self.assertRaises(news_clearance.NewsBlocked) as caught:
            news_clearance.require_clear("AMD",NOW,loader(d))
        self.assertEqual(caught.exception.status,"NEWS_UNKNOWN")
    def test_future_attestation_unknown(self):
        d=doc();d["produced_at_utc"]=(NOW+timedelta(seconds=3)).isoformat()
        with self.assertRaises(news_clearance.NewsBlocked):
            news_clearance.require_clear("AMD",NOW,loader(d))
    def test_negative_material_filing_veto(self):
        d=doc()
        d["evidence"].append(dict(symbol="AMD",issuer_cik="0000002488",
            published_at=(NOW-timedelta(seconds=12)).isoformat(),
            first_observed_at=(NOW-timedelta(seconds=9)).isoformat(),
            source="sec_edgar",source_reference="SEC-8K-20261111",
            content_hash="hash-negative",category="guidance",
            status="material_adverse_verified"))
        with self.assertRaises(news_clearance.NewsBlocked) as caught:
            news_clearance.require_clear("AMD",NOW,loader(d))
        self.assertEqual(caught.exception.status,"NEWS_MATERIAL_ADVERSE")
    def test_conflicting_news_watch_only(self):
        d=doc()
        d["evidence"].append(dict(symbol="AMD",issuer_cik="0000002488",
            published_at=(NOW-timedelta(seconds=12)).isoformat(),
            first_observed_at=(NOW-timedelta(seconds=9)).isoformat(),
            source="licensed_news",source_reference="news-id",content_hash="hash",
            category="litigation",status="pending_allegation"))
        with self.assertRaises(news_clearance.NewsBlocked) as caught:
            news_clearance.require_clear("AMD",NOW,loader(d))
        self.assertEqual(caught.exception.status,"NEWS_REVIEW_WATCH_ONLY")
    def test_wrong_issuer_mismatch_unknown(self):
        d=doc();d["identity"]["issuer_cik"]="9999999999"
        with self.assertRaises(news_clearance.NewsBlocked):
            news_clearance.require_clear("AMD",NOW,loader(d))
    def test_future_news_is_not_retroactive(self):
        d=doc()
        d["evidence"].append(dict(symbol="AMD",issuer_cik="0000002488",
            published_at=(NOW+timedelta(minutes=1)).isoformat(),
            first_observed_at=(NOW+timedelta(minutes=1)).isoformat(),
            source="licensed_news",source_reference="future-id",content_hash="hash",
            category="guidance",status="material_adverse_verified"))
        self.assertEqual(news_clearance.require_clear("AMD",NOW,loader(d))["status"],
                         "NEWS_CLEAR_ASOF")
    def test_actual_root_path_empty_does_not_clear(self):
        with patch.object(news_clearance,"ROOT",news_clearance.Path("/nonexistent/protected/news")):
            with self.assertRaises(news_clearance.NewsBlocked):
                news_clearance.require_clear("AMD",NOW)

class TimingAndPrice(unittest.TestCase):
    def proof(self,bid="100.00",ask="100.10",reference="98.50"):
        return {"bid":bid,"ask":ask,"quote_at":NOW,
                "entry_extension":{"previous_rth_close":reference,
                                   "previous_session_date":"2026-11-09"}}
    def row(self):
        return {"quote_last":"100.05","quote_ask":"100.10","limit_price":"100.10"}
    def test_preorder_price_extensions(self):
        p=entry_tracking.pre_order(self.row(),self.proof())
        self.assertEqual(p["already_up_at_recommendation_pct"],"1.5736")
        self.assertEqual(p["already_up_at_order_ask_pct"],"1.6244")
        self.assertEqual(p["move_ask_since_recommendation_pct"],"0.0000")
    def test_dont_chase_after_recommendation(self):
        r=self.row();r["limit_price"]="101.00"
        with self.assertRaises(entry_tracking.EntryExtended):
            entry_tracking.pre_order(r,self.proof("100.7","100.9"))
    def test_resting_lower_pullback_is_not_chasing(self):
        r=self.row();r["limit_price"]="99.70"
        p=entry_tracking.pre_order(r,self.proof("100.7","100.9"))
        self.assertEqual(p["price_gate"],"NO_CHASE")
        self.assertEqual(p["move_ask_since_recommendation_pct"],"0.7992")
        self.assertLess(Decimal(p["max_price_move_since_recommendation_pct"]),Decimal("0"))
    def test_fill_is_broker_price_not_quote_or_order_acceptance(self):
        data=entry_tracking.at_fill({"quote_ask":"100.10","quote_last":"100.05",
             "previous_rth_close":"98.50"},"100.025",4,
              "2026-11-10T16:01:03+00:00")
        self.assertEqual(data["fill_vs_previous_close_pct"],"1.5482")
        self.assertEqual(data["filled_quantity"],"4")
        self.assertTrue(data["execution_is_fill"])

class BrokerPath(unittest.TestCase):
    def test_news_check_precedes_any_broker_inventory_read(self):
        calls=[]
        def forbidden_broker(*args,**kwargs):
            calls.append(args)
            raise AssertionError("broker called before NEWS_CLEAR_ASOF")
        row=dict(ROW)
        row["expires_at_utc"]=(NOW+timedelta(minutes=1)).replace(tzinfo=None)
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(
            bridge,"require_clear",side_effect=news_clearance.NewsBlocked(
                "NEWS_UNKNOWN","MISSING_SOURCE")):
            with self.assertRaises(bridge.Unsafe):
                bridge.preflight(row,NOW,httpfn=forbidden_broker)
        self.assertEqual(calls,[])
    def test_unknown_news_never_posts_or_retries(self):
        db=FakeDB();broker=BrokerFake()
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(
            bridge,"preflight",side_effect=bridge.Unsafe("NEWS_UNKNOWN:INDEPENDENT_NEWS_MISSING")):
            result=bridge.process_once(now=NOW,connect=lambda _:db,
                         httpfn=broker,only_recommendation_id=REC,clockfn=lambda:NOW)
        self.assertEqual(result["results"][0]["status"],"NO_ORDER")
        self.assertNotIn("PAPER_POST",broker.events)
        self.assertIn("UPDATE_INTENT",db.events)
    def test_change_in_news_before_post_blocks_buy(self):
        db=FakeDB();broker=BrokerFake()
        proof={"account_fingerprint":"fingerprint",
               "quote_at":NOW-timedelta(seconds=2),
               "entry_tracking":{"price_gate":"NO_CHASE"},
               "news_clearance":{"status":"NEWS_CLEAR_ASOF",
                                 "evidence_sha256":"old"}}
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(
            bridge,"preflight",return_value=proof),patch.object(
            bridge,"require_clear",side_effect=news_clearance.NewsBlocked(
                "NEWS_MATERIAL_ADVERSE","ADVERSE_GUIDANCE")):
            result=bridge.process_once(now=NOW,connect=lambda _:db,httpfn=broker,
                       only_recommendation_id=REC,clockfn=lambda:NOW)
        self.assertEqual(result["results"][0]["status"],"NO_ORDER")
        self.assertEqual(broker.events,[])
        self.assertIn("EVENT",db.events)
    def test_late_quote_blocks_post(self):
        db=FakeDB();broker=BrokerFake()
        proof={"account_fingerprint":"fingerprint",
               "quote_at":NOW-timedelta(minutes=4),
               "entry_tracking":{"price_gate":"NO_CHASE"},
               "news_clearance":{"status":"NEWS_CLEAR_ASOF",
                                 "evidence_sha256":"old"}}
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(
            bridge,"preflight",return_value=proof),patch.object(
            bridge,"require_clear",return_value={"status":"NEWS_CLEAR_ASOF","evidence_sha256":"new"}):
            result=bridge.process_once(now=NOW,connect=lambda _:db,httpfn=broker,
                       only_recommendation_id=REC,clockfn=lambda:NOW)
        self.assertEqual(result["results"][0]["status"],"NO_ORDER")
        self.assertEqual(broker.events,[])

if __name__=="__main__":unittest.main()
