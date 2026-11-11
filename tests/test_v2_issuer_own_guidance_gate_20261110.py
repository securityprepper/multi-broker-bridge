import unittest
from research.v2_issuer_own_guidance_gate_20261110 import own_guidance_headline,audit_triggering_articles
class IssuerOwnGuidance(unittest.TestCase):
 def test_competitor_guidance_cannot_qualify_dell(self):
  h="Dell, HPE Shares Jump After Hours as AI Server Rival Super Micro Raises Revenue Outlook"
  self.assertEqual(own_guidance_headline(h,["Dell"])[1],"SECONDARY_COMPANY_CONTEXT")
 def test_competitor_guidance_cannot_qualify_hpe(self):
  h="Dell, HPE Shares Jump After Hours as AI Server Rival Super Micro Raises Revenue Outlook"
  self.assertEqual(own_guidance_headline(h,["HPE","Hewlett Packard"])[1],"ISSUER_NOT_INITIAL_SUBJECT")
 def test_nvidia_analyst_price_target_not_issuer_guidance(self):
  h="Goldman Sachs Expects Nvidia To Sustain Competitive Lead, Raises Price Forecast To $1,200"
  self.assertFalse(own_guidance_headline(h,["Nvidia"])[0])
 def test_capex_increase_not_eps_guidance(self):
  h="Alphabet Q3 Earnings Revenue EPS Top Estimates, Google Parent Raises CapEx Guidance"
  self.assertEqual(own_guidance_headline(h,["Alphabet"])[1],"NOT_DIRECT_EARNINGS_GUIDANCE")
 def test_valid_direct_issuer_guidance_remains_unverified(self):
  h="Quanta Services Raises FY2026 Adj EPS Guidance from $16.45 to $17.90"
  self.assertEqual(own_guidance_headline(h,["Quanta Services"]),
       (True,"PLAUSIBLE_OWN_GUIDANCE_UNVERIFIED"))
 def test_positive_not_actionable_without_issuer(self):
  self.assertEqual(own_guidance_headline("Quanta Services Raises FY2026 EPS Guidance",[])[1],
       "MISSING_VERIFIED_ISSUER_MAPPING")
 def test_name_in_middle_is_not_subject(self):
  self.assertEqual(own_guidance_headline("Benzinga Reports Quanta Services Raises FY2026 EPS Guidance",["Quanta Services"])[1],
       "ISSUER_NOT_INITIAL_SUBJECT")
 def test_analyst_target_excluded_even_issuer_starts(self):
  self.assertFalse(own_guidance_headline("Nvidia Shares Surge As Goldman Sachs Raises Price Target",["Nvidia"])[0])
 def test_same_article_dedup_by_symbol(self):
  row={"status":"POSITIVE_RESEARCH","symbol":"DELL","triggering_articles":[{"id":1,
    "headline":"Dell Shares Jump as Rival Super Micro Raises Revenue Outlook","labels":["GUIDANCE_RAISE_HEADLINE"]}]}
  r=audit_triggering_articles([row,row],{"DELL":["Dell"]})
  self.assertEqual(r["distinct_guidance_symbol_article_pairs"],1)
  self.assertEqual(len(r["flagged"]),1)
 def test_same_article_two_symbols_separately(self):
  article={"id":1,"headline":"Dell, HPE Shares Jump as Rival Super Micro Raises Revenue Outlook",
           "labels":["GUIDANCE_RAISE_HEADLINE"]}
  rows=[{"status":"POSITIVE_RESEARCH","symbol":s,"triggering_articles":[article]} for s in ("DELL","HPE")]
  r=audit_triggering_articles(rows,{"DELL":["Dell"],"HPE":["HPE"]})
  self.assertEqual(len(r["flagged"]),2)
if __name__=="__main__":unittest.main()
