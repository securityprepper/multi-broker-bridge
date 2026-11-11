import unittest
from research.v2_sealed_news_archive_eligibility_20261110 import audit,InvalidArchive
def record(observed="2026-11-10T16:00:00+00:00",published="2026-11-10T15:59:00+00:00",category="EARNINGS_RELEASE_CANDIDATE_UNVERIFIED",verified=False,up=False,news_id="a"):
 return {"article":{"news_id":news_id,"observed_at_utc":observed,"published_at_utc":published,
 "category":category,"realtime_fresh":True},"issuer_verified":verified,
 "guidance_change_verified":up,"prospective_archive":True,
 "orders_submitted":0,"trade_authorized":False}
ASOF="2026-11-11T04:33:00+00:00"
class ArchiveAudit(unittest.TestCase):
 def test_unverified_primary_source_abstains(self):
  c=audit([record()],ASOF)["counts"]
  self.assertEqual(c["missing_verified_primary_issuer"],1)
 def test_after_entry_cutoff_never_qualifies(self):
  c=audit([record(observed="2026-11-10T23:00:00+00:00")],ASOF)["counts"]
  self.assertEqual(c["after_1315_ct"],1)
 def test_future_record_abstains(self):
  c=audit([record(observed="2026-11-11T05:00:00+00:00")],ASOF)["counts"]
  self.assertEqual(c["future_abstain"],1)
 def test_publication_future_invalid(self):
  c=audit([record(published="2026-11-10T17:00:00+00:00")],ASOF)["counts"]
  self.assertEqual(c["publication_after_observation_error"],1)
 def test_consensus_unverified_abstains(self):
  c=audit([record(verified=True)],ASOF)["counts"]
  self.assertEqual(c["missing_verified_guidance_upgrade"],1)
 def test_even_verified_never_authorizes_orders(self):
  r=audit([record(verified=True,up=True)],ASOF)
  self.assertEqual(r["approved_trades"],0)
  self.assertEqual(r["counts"]["verified_catalyst_still_needs_quote_and_paper_gate"],1)
 def test_duplicate_id_counted_once(self):
  c=audit([record(),record()],ASOF)["counts"]
  self.assertEqual(c["unique_observed"],1)
  self.assertEqual(c["duplicate_id"],1)
 def test_broker_write_evidence_refused(self):
  x=record();x["orders_submitted"]=1
  with self.assertRaises(InvalidArchive):audit([x],ASOF)
 def test_plain_timestamp_refused(self):
  with self.assertRaises(InvalidArchive):audit([record(observed="2026-11-10T16:00:00")],ASOF)
if __name__=="__main__":unittest.main()
