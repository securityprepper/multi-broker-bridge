"""Offline causal/source tests for independent activist Schedule 13D idea."""
import importlib.util
import unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1] / "research" / "v2_13d_activist_source_gate_20261111.py"
spec=importlib.util.spec_from_file_location("candidate_13d_gate",p)
m=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=m
spec.loader.exec_module(m)
DATA={
"form":"SC 13D","accession":"0001193125-26-123456",
"target_cik":"0000001234","expected_target_cik":"1234",
"accepted_at":"2026-11-10T21:00:00+00:00",
"first_observed_at":"2026-11-10T21:00:02+00:00",
"decision_at":"2026-11-10T21:01:00+00:00",
"event_document_sha256":"a"*64,"source_covers_target":True,
"item4_independently_attested":True,"active_intent_attested":True,
"ownership_pct":"5.1","negative_news_veto_clear":True
}
def evaluate(**change):
    data={**DATA,**change}
    return m.evaluate(**data)
class Test13D(unittest.TestCase):
    def test_complete_source_is_still_never_trade(self):
        x=evaluate()
        self.assertEqual(x.decision,"SOURCE_VERIFIED_REPLAY_ONLY")
        self.assertFalse(x.allowed_to_trade)
        self.assertFalse(x.validated_prediction)
    def test_passive_13g_not_activist(self):
        x=evaluate(form="SC 13G")
        self.assertIn("NOT_ORIGINAL_SC_13D",x.reasons)
    def test_13d_amendment_not_initial_trigger(self):
        x=evaluate(form="SC 13D/A")
        self.assertIn("NOT_ORIGINAL_SC_13D",x.reasons)
    def test_acceptance_does_not_equal_collector_first_seen(self):
        x=evaluate(first_observed_at=None)
        self.assertIn("ORIGINAL_FIRST_OBSERVED_MISSING",x.reasons)
    def test_future_initial_observation_fails(self):
        x=evaluate(first_observed_at="2026-11-10T21:03:00Z")
        self.assertIn("FIRST_OBSERVED_OUTSIDE_DECISION",x.reasons)
    def test_preacceptance_first_observation_fails(self):
        x=evaluate(first_observed_at="2026-11-10T20:00:00Z")
        self.assertIn("FIRST_OBSERVED_OUTSIDE_DECISION",x.reasons)
    def test_decision_before_sec_acceptance_fails(self):
        x=evaluate(decision_at="2026-11-10T20:00:00Z")
        self.assertIn("DECISION_BEFORE_ACCEPTANCE",x.reasons)
    def test_target_coverage_fails_closed(self):
        x=evaluate(source_covers_target=False)
        self.assertIn("TARGET_COVERAGE_NOT_CERTIFIED",x.reasons)
    def test_incorrect_target_cik(self):
        x=evaluate(target_cik="9999")
        self.assertIn("TARGET_CIK_UNVERIFIED",x.reasons)
    def test_non_numeric_target_fails(self):
        x=evaluate(target_cik="12A")
        self.assertIn("TARGET_CIK_UNVERIFIED",x.reasons)
    def test_invalid_5_percent_threshold(self):
        x=evaluate(ownership_pct="5")
        self.assertIn("OWNERSHIP_GT5_NOT_VERIFIED",x.reasons)
    def test_nan_prevents_threshold_pass(self):
        x=evaluate(ownership_pct="NaN")
        self.assertIn("OWNERSHIP_GT5_NOT_VERIFIED",x.reasons)
    def test_missing_item4_purpose_fails(self):
        x=evaluate(item4_independently_attested=False)
        self.assertIn("ITEM4_PURPOSE_NOT_ATTESTED",x.reasons)
    def test_missing_active_control_intent_fails(self):
        x=evaluate(active_intent_attested=False)
        self.assertIn("CONTROL_INTENT_NOT_ATTESTED",x.reasons)
    def test_content_version_missing(self):
        x=evaluate(event_document_sha256=None)
        self.assertIn("DOCUMENT_VERSION_UNVERIFIED",x.reasons)
    def test_negative_news_veto_uncertain(self):
        x=evaluate(negative_news_veto_clear=False)
        self.assertIn("NEGATIVE_NEWS_VETO_UNVERIFIED",x.reasons)
    def test_naive_datetimes_fail(self):
        x=evaluate(decision_at="2026-11-10T21:01:00")
        self.assertIn("DECISION_BEFORE_ACCEPTANCE",x.reasons)
    def test_bad_accepted_at_fails(self):
        x=evaluate(accepted_at="not-a-time")
        self.assertIn("SEC_ACCEPTANCE_UNVERIFIED",x.reasons)
    def test_bad_accession_fails(self):
        x=evaluate(accession="../123")
        self.assertIn("INVALID_ACCESSION",x.reasons)

if __name__=="__main__": unittest.main()