"""Offline synthetic tests; no network, broker access, or production module imports."""
import importlib.util
import pathlib
import unittest

audit_path = pathlib.Path(__file__).with_name("v2_fdr_news_scope_audit_20261112.py")
spec = importlib.util.spec_from_file_location("fdr_news_scope_research", audit_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

RUNNER = 'BASKET=("AMD","NVDA")\ndef _fetch_causal_news(x): return ANCHORS\n'
CATALYSTS = 'ANCHORS={"AMD":None}\ndef screen(articles, asof, minimum_distinct=2): return {}\n'

class ScopeTests(unittest.TestCase):
    def test_single_material_headline_is_insufficient_under_default(self):
        self.assertEqual(module.audit_sources(RUNNER, CATALYSTS)["distinct_adverse_headline_minimum"], 2)
    def test_nonanchor_basket_member_uncovered(self):
        self.assertEqual(module.audit_sources(RUNNER, CATALYSTS)["uncovered_basket_symbols"], ["NVDA"])
    def test_fail_closed_without_verified_clearance(self):
        r = module.audit_sources(RUNNER, CATALYSTS)
        self.assertFalse(r["NEWS_CLEAR_ASOF_gate_present"])
        self.assertEqual(r["paper_reactivation_research_decision"], "NO_GO")
    def test_fail_closed_without_first_observed_proof(self):
        self.assertFalse(module.audit_sources(RUNNER, CATALYSTS)["first_observed_at_field_present"])
    def test_fail_closed_without_anchor_query(self):
        r = RUNNER.replace("return ANCHORS", "return []")
        self.assertFalse(module.audit_sources(r, CATALYSTS)["news_query_uses_anchor_set"])
    def test_fail_closed_with_missing_or_unparseable_roster(self):
        with self.assertRaises(ValueError):
            module.audit_sources('BASKET=x', CATALYSTS)
    def test_full_roster_still_not_sufficient_when_two_headlines_required(self):
        r = module.audit_sources(RUNNER.replace('("AMD","NVDA")','("AMD",)'), CATALYSTS)
        self.assertEqual(r["uncovered_basket_symbols"], [])
        self.assertEqual(r["paper_reactivation_research_decision"], "NO_GO")

if __name__ == "__main__":
    unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]