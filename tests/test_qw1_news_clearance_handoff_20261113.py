"""Regression: unverified NEWS_UNKNOWN and late RTH cannot trigger BUY/paper failure Pushover."""
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import quality_watch as q
from recommendation_paper_bridge.news_clearance import NewsBlocked

CT=q.CT
NOW=datetime(2026,11,13,10,43,tzinfo=CT).astimezone(timezone.utc)

class TrustedSignalPreflightTests(unittest.TestCase):
    def test_missing_news_attestation_blocks_qualified_buy(self):
        with patch.object(q,"root_news_clear",side_effect=NewsBlocked("NEWS_UNKNOWN","TRUSTED_CLEARANCE_UNAVAILABLE")):
            valid,reason=q.trusted_buy_eligibility("AMD",NOW)
        self.assertFalse(valid)
        self.assertIn("NEWS_UNKNOWN",reason)

    def test_adverse_news_blocks(self):
        with patch.object(q,"root_news_clear",side_effect=NewsBlocked("NEWS_MATERIAL_ADVERSE","ADVERSE_GUIDANCE")):
            valid,reason=q.trusted_buy_eligibility("AMD",NOW)
        self.assertFalse(valid)
        self.assertIn("MATERIAL_ADVERSE",reason)

    def test_positive_trusted_clearance_passes_but_no_broker_order_here(self):
        with patch.object(q,"root_news_clear",return_value={"status":"NEWS_CLEAR_ASOF","issuer_cik":"0000002488"}):
            valid,reason=q.trusted_buy_eligibility("AMD",NOW)
        self.assertEqual((valid,reason),(True,"NEWS_CLEAR_ASOF"))

    def test_past_1315_cutoff_never_emits_buy(self):
        after=datetime(2026,11,13,13,16,tzinfo=CT).astimezone(timezone.utc)
        with patch.object(q,"root_news_clear",side_effect=AssertionError("no news request after cutoff")):
            valid,reason=q.trusted_buy_eligibility("AMD",after)
        self.assertEqual((valid,reason),(False,"PAST_1315_PAPER_ENTRY_CUTOFF"))

    def test_weekend_never_emits_buy(self):
        saturday=datetime(2026,11,14,10,5,tzinfo=CT).astimezone(timezone.utc)
        self.assertFalse(q.trusted_buy_eligibility("AMD",saturday)[0])

    def test_fresh_global_news_feed_does_not_prove_issuer_clearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=root/"state.sqlite3"
            news=root/"news.json";holiday=root/"holiday.json"
            news.write_text(json.dumps({"asof_utc":NOW.isoformat(),"broker_read_only":True,"recent":[]}))
            holiday.write_text(json.dumps({"timezone":"America/Chicago","paused":False,
                "calendar_coverage_ok":True,"next_check_at":(NOW+timedelta(hours=1)).isoformat()}))
            x={"p5":.2,"p15":.35,"p20":.30,"p60":.50,"price":100.7,
               "low60":100.2,"volume60":100000,"bars60":50,"asof":NOW.isoformat()}
            sig={"status":"BUY NOW","reason":"MOCK_TECHNICAL_QUALIFIED_NOT_NEWS_CLEARED",
                 "momentum":x,"sector":{"status":"RISING","etf":"XLK"}}
            with patch.object(q,"QUALITY_SYMBOLS",("IBM",)),\
                 patch.object(q,"get_market",return_value=({"IBM":[]},[])),\
                 patch.object(q,"metrics",return_value=x),\
                 patch.object(q,"infer_sector_universe",return_value={"Technology":{"status":"RISING","p5":.2,"p20":.3}}),\
                 patch.object(q,"sector_closes",return_value={}),\
                 patch.object(q,"sector_alert_candidates",return_value=([],set())),\
                 patch.object(q,"estimate_signal",return_value=sig),\
                 patch.object(q,"fetch_quotes",return_value={"IBM":{"t":NOW.isoformat(),"bp":100.7,"ap":100.71}}),\
                 patch.object(q,"get_closes",return_value={"IBM":100}),\
                 patch.object(q,"paper_handoff_commissioned",return_value=True),\
                 patch.object(q,"trusted_buy_eligibility",return_value=(False,"NEWS_NEWS_UNKNOWN")),\
                 patch.object(q,"emit_paper_event",side_effect=AssertionError("must not emit PAPER BUY")),\
                 patch.object(q,"dispatch_pushover",side_effect=AssertionError("must not send spurious failure Pushover")):
                result=q.run(NOW,state,news,holiday,{},root,lambda *a:{},deliver=True)
            self.assertEqual(result["qualified_signals"],0)
            self.assertEqual(result["alerts"],[])
            self.assertGreaterEqual(result["buy_preflight_block_counts"]["NEWS_NEWS_UNKNOWN"],1)

    def test_no_new_broker_module_or_order_call(self):
        from inspect import getsource
        body=getsource(q.trusted_buy_eligibility)
        self.assertNotIn("paper_api",body)
        self.assertNotIn("POST",body)
        self.assertNotIn("place_order",body)

if __name__=="__main__":
    unittest.main()
