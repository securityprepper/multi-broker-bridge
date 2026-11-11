"""Synthetic offline tests for first-seen/revision leakage in news replay."""
import unittest
from research.v2_catalyst_archival_firstseen_audit_20261111 import (
 summarize_articles,summarize_triggering_versions,parse)

def article(created="2026-11-10T14:00:00Z",updated="2026-11-10T14:00:00Z"):
 return {"news_id":7,"created_at":created,"updated_at":updated,
 "headline":"factual public headline","source":"benzinga","symbols":["AMD"]}

class ArchivalProvenance(unittest.TestCase):
 def test_no_first_seen_is_not_causal_proof(self):
  s=summarize_articles([article()])
  self.assertEqual(s["no_contemporaneous_first_seen"],1)
  self.assertEqual(s["no_independent_numeric_estimate_revision"],1)
  self.assertEqual(s["no_verified_numeric_issuer_guidance"],1)
 def test_updated_post_entry_has_leakage_risk(self):
  a=article(updated="2026-11-10T16:00:00Z")
  s=summarize_triggering_versions([{"status":"POSITIVE_RESEARCH",
   "evaluation_time_et":"2026-11-10T15:40:00Z",
   "triggering_articles":[{"id":7}]}],{"7":a})
  self.assertEqual(s["final_record_updated_after_decision"],1)
  self.assertEqual(s["no_forward_own_first_seen_at_signal"],1)
 def test_updated_before_entry_not_imputed_first_seen(self):
  a=article(updated="2026-11-10T14:05:00Z")
  s=summarize_triggering_versions([{"status":"POSITIVE_RESEARCH",
   "evaluation_time_et":"2026-11-10T15:40:00Z",
   "triggering_articles":[{"id":7}]}],{"7":a})
  self.assertNotIn("final_record_updated_after_decision",s)
  self.assertEqual(s["no_forward_own_first_seen_at_signal"],1)
 def test_missing_raw_article_detected(self):
  s=summarize_triggering_versions([{"status":"POSITIVE_RESEARCH",
   "evaluation_time_et":"2026-11-10T15:40:00Z",
   "triggering_articles":[{"id":7}]}],{})
  self.assertEqual(s["missing_raw_article_id"],1)
 def test_future_creation_detected(self):
  a=article(created="2026-11-10T16:00:00Z",updated="2026-11-10T16:00:00Z")
  s=summarize_triggering_versions([{"status":"POSITIVE_RESEARCH",
   "evaluation_time_et":"2026-11-10T15:40:00Z",
   "triggering_articles":[{"id":7}]}],{"7":a})
  self.assertEqual(s["created_after_decision"],1)
 def test_revision_time_backwards_detected(self):
  s=summarize_articles([article(updated="2026-11-10T13:00:00Z")])
  self.assertEqual(s["reversed_publication_update"],1)
 def test_absence_of_article_types_excluded(self):
  self.assertEqual(summarize_articles([None])["articles"],0)
 def test_naive_timestamp_fail_closed(self):
  with self.assertRaises(ValueError):parse("2026-11-10T09:00:00")
if __name__=="__main__":unittest.main()
