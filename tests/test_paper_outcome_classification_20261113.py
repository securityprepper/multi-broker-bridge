"""Causal PAPER handoff/notification classification tests, with no broker calls."""
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from recommendation_paper_bridge import bridge
import watcher_paper_executor as w
import watcher_event

NOW=datetime(2026,11,13,19,0,tzinfo=timezone.utc)
def event(source="QW1",news=False,plan=True):
    proof={"negative_news_screened":True,
      "momentum":{"asof":NOW.isoformat()},
      "verified_news_clear_asof":"NEWS_CLEAR_ASOF" if news else None,
      "plan":{"entry":100,"target":102,"stop":99} if plan else None}
    return {"source":source,"symbol":"AMD","action":"BUY NOW",
      "event_id":source+"-20261113-AMD-0123456789AB",
      "source_task":watcher_event.SOURCES[source],"origin_id":"dummy",
      "issued_at_utc":NOW.isoformat(),"evidence":proof}

class PaperAlertClassifications(unittest.TestCase):
    def test_missing_issuer_clearance_is_source_veto_not_broker_failure(self):
        x=event(news=False)
        with patch.object(w.bridge,"entry_window",return_value=True),\
             patch.object(w,"quote_now",side_effect=AssertionError("should never quote a blocked BUY")),\
             patch.object(w.bridge,"ingest",side_effect=AssertionError("should never create PAPER intent")):
            outcome=w.submit_buy(x)
        self.assertEqual(outcome["status"],"NO_ORDER_SOURCE_PREQUALIFICATION")
        self.assertIn("CLEAR_ASOF",outcome["reason"])
        self.assertFalse(outcome["broker_post_attempted"])
        label=w.paper_outcome_label(outcome)
        self.assertIn("NOT ELIGIBLE",label)
        self.assertNotIn("ATTEMPT REJECTED OR FAILED",label)

    def test_no_verified_plan_is_no_broker_order(self):
        x=event(news=True,plan=False)
        with patch.object(w.bridge,"entry_window",return_value=True),\
             patch.object(w,"quote_now",side_effect=AssertionError("must not GET quote")):
            outcome=w.submit_buy(x)
        self.assertEqual(outcome["status"],"NO_ORDER_SOURCE_PREQUALIFICATION")
        self.assertIn("NO_VERIFIED_QUALITY_ENTRY_PLAN",outcome["reason"])

    def test_outside_1315_not_called_a_failed_broker_order(self):
        with patch.object(w.bridge,"entry_window",return_value=False),\
             patch.object(w,"quote_now",side_effect=AssertionError("must not GET quote")):
            outcome=w.submit_buy(event(news=True))
        self.assertEqual(outcome["status"],"NO_ORDER_OUTSIDE_RTH_BRACKET_WINDOW")
        self.assertIn("13:15",w.paper_outcome_label(outcome))
        self.assertNotIn("REJECTED OR FAILED",w.paper_outcome_label(outcome))

    def test_no_alpaca_position_is_not_a_failed_order(self):
        msg=w.paper_outcome_label({"status":"NO_HELD_POSITION"})
        self.assertIn("NO POSITION HELD",msg)
        self.assertIn("NO SELL ORDER NEEDED",msg)
        self.assertNotIn("REJECTED OR FAILED",msg)

    def test_protective_sell_unknown_is_a_risk_block_not_alpaca_rejection(self):
        msg=w.paper_outcome_label({"status":"PROTECTIVE_SELL_CANCEL_UNKNOWN_NO_CLOSE"})
        self.assertIn("PROTECTION / VERIFICATION BLOCKED",msg)
        self.assertNotIn("REJECTED OR FAILED",msg)

    def test_real_broker_rejection_still_reports_failure(self):
        msg=w.paper_outcome_label({"status":"BROKER_REJECTED"})
        self.assertIn("REJECTED OR FAILED",msg)

    def test_unknown_submission_not_claimed_failed_and_no_auto_retry(self):
        msg=w.paper_outcome_label({"status":"NO_ORDER_OR_UNKNOWN_NO_RETRY"})
        self.assertIn("STATUS UNKNOWN",msg)
        self.assertIn("DO NOT RETRY",msg)
        self.assertNotIn("REJECTED OR FAILED",msg)

    def test_success_not_a_fill(self):
        self.assertIn("NOT A FILLED TRADE",w.paper_outcome_label({"status":"BROKER_ACCEPTED"}))
        self.assertIn("NOT A FILLED TRADE",w.paper_outcome_label({"status":"PAPER_CLOSE_ACCEPTED_NOT_A_FILL"}))

    def test_verified_news_does_not_skip_broker_own_risk_gates(self):
        x=event(news=True,plan=True)
        self.assertEqual(w.eligible_quality_plan(x)[0],"AMD")
        self.assertEqual(w.eligible_quality_plan(x)[2],"BUY NOW")

    def test_source_headline_only_flag_is_not_news_clearance(self):
        x=event(news=False)
        self.assertTrue(x["evidence"]["negative_news_screened"])
        with self.assertRaisesRegex(bridge.Unsafe,"SOURCE_NEWS_CLEAR_ASOF_REQUIRED"):
            w.eligible_quality_plan(x)

if __name__=="__main__": unittest.main()
