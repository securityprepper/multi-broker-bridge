import unittest
from v2_catalyst_issuer_gate_20261110 import evaluate,audit_recent,InvalidEvent
A={"symbols":["MRK"],"published_at_utc":"2026-11-10T21:01:44Z",
   "observed_at_utc":"2026-11-10T21:02:26Z","category":"POSITIVE_NEWS_CANDIDATE_UNVERIFIED"}
I={"symbol":"MRK","canonical_issuer_key":"MERCK_AND_CO_US"}
E={"verified_at_utc":"2026-11-10T21:30:00Z","source_type":"FDA_OFFICIAL",
   "official_event_type":"FDA_APPROVAL","canonical_issuer_key":"MERCK_KGAA_DE"}
Q={"observed_at_utc":"2026-11-10T21:30:10Z","bid":"110.00","ask":"110.05",
   "session_supported":True,"protective_exit_supported":True}
class TestCatalystIssuer(unittest.TestCase):
 def test_unverified_at_news_arrival(self):
  self.assertEqual(evaluate(A,E,I,"2026-11-10T21:02:30Z")["status"],"UNVERIFIED_ISSUER")
 def test_posthoc_wrong_issuer(self):
  self.assertEqual(evaluate(A,E,I,"2026-11-10T21:31:00Z",quote=Q)["status"],"WRONG_LISTED_ISSUER")
 def test_never_order(self):
  self.assertFalse(evaluate(A,E,I,"2026-11-10T21:31:00Z")["order_authorized"])
 def test_no_source(self):
  self.assertEqual(evaluate(A,None,I,"2026-11-10T21:31:00Z")["status"],"UNVERIFIED_ISSUER")
 def test_article_future(self):
  self.assertEqual(evaluate(A,E,I,"2026-11-10T21:00:00Z")["status"],"NOT_YET_OBSERVED")
 def test_after_cutoff(self):
  e=dict(E,canonical_issuer_key="MERCK_AND_CO_US")
  self.assertEqual(evaluate(A,e,I,"2026-11-10T21:31:00Z")["status"],"AFTER_ENTRY_CUTOFF")
 def test_untrusted_blog(self):
  e=dict(E,source_type="BLOG",canonical_issuer_key="MERCK_AND_CO_US")
  self.assertEqual(evaluate(A,e,I,"2026-11-10T21:31:00Z")["status"],"UNVERIFIED_PRIMARY_SOURCE")
 def test_wrong_catalyst(self):
  e=dict(E,official_event_type="EARNINGS_BEAT_HEADLINE",canonical_issuer_key="MERCK_AND_CO_US")
  self.assertEqual(evaluate(A,e,I,"2026-11-10T21:31:00Z")["status"],"UNVERIFIED_CATALYST")
 def test_frozen_prior_consensus_needed(self):
  a=dict(A,published_at_utc="2026-11-10T14:01:44Z",observed_at_utc="2026-11-10T14:02:26Z")
  e=dict(E,verified_at_utc="2026-11-10T14:03:00Z",canonical_issuer_key="MERCK_AND_CO_US",
         official_event_type="RAISED_REVENUE_GUIDANCE",previous_guidance="10",new_guidance="11",
         consensus_frozen_at_utc="2026-11-10T14:02:44Z")
  self.assertEqual(evaluate(a,e,I,"2026-11-10T14:04:00Z")["status"],"UNVERIFIED_PRIOR_CONSENSUS")
 def test_good_research_candidate_not_order(self):
  a=dict(A,published_at_utc="2026-11-10T14:01:44Z",observed_at_utc="2026-11-10T14:02:26Z")
  e=dict(E,verified_at_utc="2026-11-10T14:03:00Z",canonical_issuer_key="MERCK_AND_CO_US",
         official_event_type="RAISED_REVENUE_GUIDANCE",previous_guidance="10",new_guidance="11",
         consensus_frozen_at_utc="2026-11-09T20:00:00Z")
  q=dict(Q,observed_at_utc="2026-11-10T14:03:40Z")
  v=evaluate(a,e,I,"2026-11-10T14:04:00Z",quote=q)
  self.assertEqual(v["status"],"RESEARCH_SHADOW_ELIGIBLE_ONLY")
  self.assertFalse(v["order_authorized"])
 def test_stale_quote(self):
  a=dict(A,published_at_utc="2026-11-10T14:01:44Z",observed_at_utc="2026-11-10T14:02:26Z")
  e=dict(E,verified_at_utc="2026-11-10T14:03:00Z",canonical_issuer_key="MERCK_AND_CO_US")
  self.assertEqual(evaluate(a,e,I,"2026-11-10T14:04:00Z",quote=Q)["status"],"STALE_OR_FUTURE_QUOTE")
 def test_no_protection(self):
  a=dict(A,published_at_utc="2026-11-10T14:01:44Z",observed_at_utc="2026-11-10T14:02:26Z")
  e=dict(E,verified_at_utc="2026-11-10T14:03:00Z",canonical_issuer_key="MERCK_AND_CO_US")
  q=dict(Q,observed_at_utc="2026-11-10T14:03:40Z",protective_exit_supported=False)
  self.assertEqual(evaluate(a,e,I,"2026-11-10T14:04:00Z",quote=q)["status"],"NO_VERIFIED_PROTECTION")
 def test_feed_count(self):
  x={"recent":[dict(A),dict(A,category="OTHER_NEWS")]}
  self.assertEqual(audit_recent(x,"2026-11-10T21:32:00Z")["candidate_headlines"],1)
 def test_feed_count_late(self):
  x={"recent":[dict(A)]}
  self.assertEqual(audit_recent(x,"2026-11-10T21:32:00Z")["arrived_after_1315_ct"],1)
if __name__=="__main__": unittest.main()
