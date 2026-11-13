"""Isolated, synthetic tests for static analysis; never use broker credentials."""
import unittest
from research.v2_mbb_direct_news_gate_audit_20261112 import audit_source, audit_journal

DIRECT = """
def paper_api(method,path,body=None):
    req = Request("https://paper-api.alpaca.markets" + path)
    return urlopen(req)
def run(now,execute=False):
    receipt=paper_api("POST","/v2/orders", {"side":"buy"})
    return receipt
"""

class SourceGateAuditTests(unittest.TestCase):
    def test_detects_direct_post_without_news_clearance(self):
        x = audit_source(DIRECT)
        self.assertEqual(x["status"], "MISSING_EXPLICIT_PREBUY_NEWS_CLEARANCE_IN_DIRECT_ORDER_PATH")
        self.assertTrue(x["direct_buy_order_post"])
        self.assertTrue(x["direct_paper_https_transport"])

    def test_visible_news_reference_requires_review_not_go(self):
        source = DIRECT.replace('receipt=paper_api', 'NEWS_CLEAR_ASOF=check_negative_news(now)\n    receipt=paper_api')
        x = audit_source(source)
        self.assertTrue(x["explicit_news_check_observed"])
        self.assertEqual(x["status"], "REQUIRES_MANUAL_CODE_AND_ASOF_EVIDENCE_REVIEW")

    def test_missing_run_fail_unknown(self):
        self.assertEqual(audit_source("def example(): pass")["status"], "UNKNOWN_SOURCE")

    def test_no_post_not_equivalent_to_clearance(self):
        src = DIRECT.replace('paper_api("POST","/v2/orders"', 'paper_api("GET","/v2/orders"')
        self.assertEqual(audit_source(src)["status"], "NO_DIRECT_ORDER_POST_FOUND")

    def test_journal_never_equates_acceptance_with_fill(self):
        r = audit_journal(['{"status":"SCAN_COMPLETE","orders":[{"side":"buy","broker_order_id":"opaque","status":"pending_new"}]}'])
        self.assertEqual(r["buy_order_responses"], 1)
        self.assertEqual(r["buy_responses_with_documented_news_clearance"], 0)

    def test_journal_counts_only_source_proof(self):
        r = audit_journal(['{"status":"SCAN_COMPLETE","orders":[{"side":"buy","broker_order_id":"opaque","news_clearance":"NEWS_CLEAR_ASOF","news_evidence_observed_at":"2026-11-12T14:00:00Z"}]}'])
        self.assertEqual(r["buy_responses_with_documented_news_clearance"], 1)

    def test_journal_ignores_nonjson_and_sell(self):
        r = audit_journal(["bad", '{"status":"SCAN_COMPLETE","orders":[{"side":"sell","broker_order_id":"opaque"}]}'])
        self.assertEqual(r["buy_order_responses"], 0)

if __name__ == "__main__":
    unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]