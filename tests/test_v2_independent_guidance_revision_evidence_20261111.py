"""Causal identity/share-basis/provenance tests, no broker or provider calls."""
import unittest
from research.v2_independent_guidance_revision_evidence_20261111 import readiness, inventory_articles

CIK=1234567
ASOF="2026-11-10T15:35:00Z"
ISSUER={
 "cik":CIK,"sec_exhibit_url":"https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/ex99-1.htm",
 "official_event_type":"RAISED_EPS_GUIDANCE","release_published_at":"2026-11-10T15:00:00Z",
 "sec_accepted_at":"2026-11-10T15:01:00Z","first_observed_at":"2026-11-10T15:01:25Z",
 "release_original_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
 "sec_exhibit_first_observed_at":"2026-11-10T15:02:15Z",
 "sec_exhibit_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
 "prior_guidance":"4.00","new_guidance":"4.25","fiscal_period":"FY2027",
 "units":"USD_PER_DILUTED_SHARE","share_basis":"AS_REPORTED_UNADJUSTED"}
REV={
 "issuer_cik":CIK,"origin_type":"INDEPENDENT_ANALYST_ESTIMATE",
 "analyst_firm_id":"research-firm-123","source_document_id":"revision-20261110-1",
 "fiscal_period":"FY2027","units":"USD_PER_DILUTED_SHARE",
 "share_basis":"AS_REPORTED_UNADJUSTED","published_at":"2026-11-10T15:06:00Z",
 "first_observed_at":"2026-11-10T15:07:20Z","old_estimate":"4.20","new_estimate":"4.45",
 "revision_original_sha256":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}

class IndependentConfluenceTests(unittest.TestCase):
 def check(self,expected,issuer=None,revision=None,asof=ASOF,negative=()):
  i=ISSUER if issuer is None else issuer
  r=REV if revision is None else revision
  z=readiness(i,r,asof,negative)
  self.assertEqual(z["status"],expected);self.assertFalse(z["signal_authorized"])
  self.assertFalse(z["order_authorized"]);return z
 def test_qualified_is_still_shadow(self):
  self.check("INDEPENDENT_CONFLUENCE_EVIDENCE_READY_SHADOW_ONLY")
 def test_no_official_document(self):
  self.check("NO_OFFICIAL_ISSUER_EVIDENCE",issuer={})
 def test_competitor_issuer_mismatch(self):
  self.check("REVISION_WRONG_ISSUER",revision={**REV,"issuer_cik":98765})
 def test_filing_acceptance_after_signal(self):
  self.check("OFFICIAL_EVENT_NOT_YET_OBSERVED",issuer={**ISSUER,
    "sec_accepted_at":"2026-11-10T15:40:00Z"})
 def test_sec_observation_before_acceptance_rejected(self):
  self.check("INCONSISTENT_SEC_PROVENANCE",issuer={**ISSUER,
    "sec_exhibit_first_observed_at":"2026-11-10T15:00:00Z"})
 def test_issuer_public_release_seen_before_sec_8k_is_legitimate(self):
  # SEC Item 2.02 report/exhibit can follow a public issuer press release.
  self.check("INDEPENDENT_CONFLUENCE_EVIDENCE_READY_SHADOW_ONLY",issuer={**ISSUER,
    "release_published_at":"2026-11-10T14:50:00Z",
    "first_observed_at":"2026-11-10T14:50:12Z",
    "sec_accepted_at":"2026-11-10T15:01:00Z",
    "sec_exhibit_first_observed_at":"2026-11-10T15:02:15Z"})
 def test_release_seen_before_actual_publication_rejected(self):
  self.check("INCONSISTENT_RELEASE_PROVENANCE",issuer={**ISSUER,
    "first_observed_at":"2026-11-10T14:59:00Z"})
 def test_sec_original_text_first_seen_missing_fails_closed(self):
  v={**ISSUER};v.pop("sec_exhibit_first_observed_at")
  self.check("MISSING_SEC_FIRST_SEEN_OR_ORIGINAL_HASH",issuer=v)
 def test_sec_original_text_digest_missing_fails_closed(self):
  v={**ISSUER};v.pop("sec_exhibit_sha256")
  self.check("MISSING_SEC_FIRST_SEEN_OR_ORIGINAL_HASH",issuer=v)
 def test_sec_first_seen_after_decision_fails_closed(self):
  self.check("SEC_EXHIBIT_NOT_YET_OBSERVED",issuer={**ISSUER,
    "sec_exhibit_first_observed_at":"2026-11-10T15:36:00Z"})
 def test_release_original_digest_missing_fails_closed(self):
  self.check("MISSING_RELEASE_ORIGINAL_HASH",issuer={**ISSUER,
    "release_original_sha256":"bad"})
 def test_analyst_original_text_digest_missing_fails_closed(self):
  v={**REV};v.pop("revision_original_sha256")
  self.check("UNVERIFIED_REVISION_ORIGIN",revision=v)

 def test_revision_after_signal(self):
  self.check("REVISION_NOT_YET_OBSERVED",revision={**REV,
    "first_observed_at":"2026-11-10T15:40:00Z"})
 def test_independent_revision_missing(self):
  self.check("NO_INDEPENDENT_ANALYST_REVISION",revision={})
 def test_news_headline_masquerading_as_revision(self):
  self.check("REVISION_NOT_INDEPENDENT",revision={**REV,
    "origin_type":"NEWS_HEADLINE_CLASSIFICATION"})
 def test_revision_prior_to_event_not_discovery(self):
  self.check("REVISION_NOT_CAUSAL_OR_UNVERIFIED",revision={**REV,
    "published_at":"2026-11-10T14:55:00Z"})
 def test_revision_time_untrusted(self):
  self.check("REVISION_NOT_CAUSAL_OR_UNVERIFIED",revision={**REV,
    "first_observed_at":"2026-11-10T15:05:00Z"})
 def test_mismatched_fiscal_period(self):
  self.check("INCOMPARABLE_REVISION_BASIS",revision={**REV,
    "fiscal_period":"FY2026"})
 def test_mismatched_split_basis(self):
  self.check("INCOMPARABLE_REVISION_BASIS",revision={**REV,
    "share_basis":"SPLIT_ADJUSTED_VERIFIED"})
 def test_zero_guidance_invalid(self):
  self.check("INVALID_OFFICIAL_SOURCE",issuer={**ISSUER,
    "new_guidance":"0"})
 def test_false_decimal_precision(self):
  self.check("INVALID_OFFICIAL_SOURCE",issuer={**ISSUER,
    "new_guidance":float(4.25)})
 def test_not_true_guidance_upgrade(self):
  self.check("NOT_RAISED_GUIDANCE",issuer={**ISSUER,
    "new_guidance":"3.50"})
 def test_not_real_analyst_revision(self):
  self.check("REVISION_NOT_POSITIVE",revision={**REV,
    "new_estimate":"4.00"})
 def test_future_negative_cannot_veto(self):
  self.check("INDEPENDENT_CONFLUENCE_EVIDENCE_READY_SHADOW_ONLY",negative=[{
    "issuer_cik":CIK,"first_observed_at":"2026-11-10T15:50:00Z",
    "official_negative":True}])
 def test_known_negative_veto(self):
  self.check("VERIFIED_NEGATIVE_NEWS_VETO",negative=[{
    "issuer_cik":CIK,"first_observed_at":"2026-11-10T15:30:00Z",
    "verified_analyst_downgrade":True}])
 def test_other_company_negative_not_veto(self):
  self.check("INDEPENDENT_CONFLUENCE_EVIDENCE_READY_SHADOW_ONLY",negative=[{
    "issuer_cik":222,"first_observed_at":"2026-11-10T15:30:00Z",
    "official_negative":True}])
 def test_sec_host_altering_document_invalid(self):
  self.check("INVALID_OFFICIAL_SOURCE",issuer={**ISSUER,
    "sec_exhibit_url":"https://www.sec.gov.evil.example/Archives/edgar/data/1234567/000123456726000001/ex99-1.htm"})
 def test_provider_headline_only_has_no_independent_revision(self):
  rows=[{"news_id":1,"created_at":"2026-11-10T15:00:00Z",
         "updated_at":"2026-11-10T15:00:00Z","headline":"stock beat",
         "source":"benzinga","symbols":["AMD"]}]
  self.assertEqual(inventory_articles(rows),{
   "articles":1,"base_fields_present":1,"numeric_issuer_and_revision_ready":0,
   "missing_independent_revision":1,"missing_official_guidance":1})
if __name__=="__main__":unittest.main()
