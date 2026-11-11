import unittest
from research.v2_primary_filing_asof_gate_20261110 import verify_official_filing_asof as gate
C={"issuer_cik":"0001571996","decision_at":"2026-10-21T13:40:00Z"}
F={"issuer_cik":"1571996","form":"8-K","first_seen_at":"2026-10-21T13:00:00Z",
"verified_primary_header_accepted_at":"2026-10-21T12:59:00Z",
"primary_header_verified":True,"issuer_guidance_verified":True}
class SECAsOf(unittest.TestCase):
 def test_valid_primary_filing_research_only(self):
  self.assertEqual(gate(C,F),"ASOF_ISSUER_GUIDANCE_CORROBORATED_RESEARCH_ONLY")
 def test_other_issuer_cannot_validate(self):
  self.assertEqual(gate(C,{**F,"issuer_cik":"1645590"}),"CIK_NOT_CONFIRMED")
 def test_no_verified_header_fails(self):
  self.assertEqual(gate(C,{**F,"primary_header_verified":False}),"PRIMARY_HEADER_NOT_VERIFIED")
 def test_acceptance_after_decision_fails(self):
  self.assertEqual(gate(C,{**F,"verified_primary_header_accepted_at":"2026-10-21T20:37:17Z",
      "first_seen_at":"2026-10-21T20:37:18Z"}),"FILING_ACCEPTED_AFTER_DECISION")
 def test_pulled_today_cannot_fake_historical_first_seen(self):
  self.assertEqual(gate(C,{**F,"first_seen_at":"2026-11-10T23:20:00Z"}),"FILING_FIRST_OBSERVED_AFTER_DECISION")
 def test_not_guidance_fails(self):
  self.assertEqual(gate(C,{**F,"issuer_guidance_verified":False}),"FILING_DOES_NOT_VERIFY_ISSUER_GUIDANCE")
 def test_bad_clock_fails(self):
  self.assertEqual(gate(C,{**F,"first_seen_at":"2026-10-21T12:58:00Z"}),"INVALID_RECEIPT_CHRONOLOGY")
 def test_unverified_form_fails(self):
  self.assertEqual(gate(C,{**F,"form":"S-1"}),"UNSUPPORTED_FORM")
 def test_naive_timestamp_fails(self):
  self.assertEqual(gate(C,{**F,"first_seen_at":"2026-10-21T12:58:00"}),"INSUFFICIENT_POINT_IN_TIME_EVIDENCE")
if __name__=="__main__":unittest.main()
