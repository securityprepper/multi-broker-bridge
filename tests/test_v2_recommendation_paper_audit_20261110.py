import unittest
from v2_recommendation_paper_audit import validate_recommendation,intent_record,audit_closed,UnverifiedExecution
R={"recommendation_id":"TO-20261110-AMD-T1-A","issued_at_utc":"2026-11-10T15:00:00Z",
"quote_at_utc":"2026-11-10T14:59:45Z","symbol":"AMD","action":"BUY NOW",
"quote_last":"100","quote_bid":"99.95","quote_ask":"100.05",
"limit":"100.10","profit_target":"101.50","stop_loss":"98.50",
"rationale":"Verified independent earnings guidance upgrade with acceptable spread",
"source_task":"Task - Trading Opportunities One","source_run_id":"run-20261110-1500"}
class TestAudit(unittest.TestCase):
 def test_record(self):
  self.assertEqual(intent_record(R)["order_status"],"NOT_PLACED_UNCOMMISSIONED")
 def test_idempotency(self):
  self.assertEqual(intent_record(R)["client_order_id"],intent_record(dict(R))["client_order_id"])
 def test_broker_receipt_required(self):
  self.assertEqual(audit_closed(R,intent_record(R),[])["status"],"NOT_CLOSED_OR_NO_VERIFIED_ORDER")
 def test_stale_quote(self):
  x=dict(R,quote_at_utc="2026-11-10T14:50:00Z")
  with self.assertRaises(UnverifiedExecution): validate_recommendation(x)
 def test_stop_order(self):
  with self.assertRaises(UnverifiedExecution): validate_recommendation(dict(R,stop_loss="101.00"))
 def test_no_chase(self):
  with self.assertRaises(UnverifiedExecution): validate_recommendation(dict(R,limit="100.00"))
 def test_source_provenance(self):
  with self.assertRaises(UnverifiedExecution): validate_recommendation(dict(R,source_task="Unknown"))
 def test_closed_fees(self):
  o=dict(intent_record(R),broker_order_id="broker-buy-uuid")
  f=[{"recommendation_id":R["recommendation_id"],"broker_order_id":"broker-buy-uuid","activity_id":"act1","time_utc":"2026-11-10T15:01:00Z","side":"BUY","qty":"2","price":"100","commission":"0.20"},
     {"recommendation_id":R["recommendation_id"],"broker_order_id":"broker-exit-uuid","activity_id":"act2","time_utc":"2026-11-10T15:03:00Z","side":"SELL","qty":"2","price":"101","commission":"0.20"}]
  self.assertEqual(audit_closed(R,o,f)["after_fee_realized_pnl"],"1.60")
 def test_partial_stays_open(self):
  o=dict(intent_record(R),broker_order_id="broker-buy-uuid")
  f=[{"recommendation_id":R["recommendation_id"],"broker_order_id":"b","activity_id":"a","time_utc":"2026-11-10T15:01:00Z","side":"BUY","qty":"2","price":"100"}]
  self.assertEqual(audit_closed(R,o,f)["status"],"OPEN_OR_PARTIAL")
 def test_no_oversell(self):
  o=dict(intent_record(R),broker_order_id="broker-buy-uuid")
  f=[{"recommendation_id":R["recommendation_id"],"broker_order_id":"b","activity_id":"a","time_utc":"2026-11-10T15:01:00Z","side":"SELL","qty":"1","price":"100"}]
  with self.assertRaises(UnverifiedExecution): audit_closed(R,o,f)
 def test_duplicate_activity(self):
  o=dict(intent_record(R),broker_order_id="broker-buy-uuid")
  f=[{"recommendation_id":R["recommendation_id"],"broker_order_id":"b","activity_id":"a","time_utc":"2026-11-10T15:01:00Z","side":"BUY","qty":"1","price":"100"}]*2
  with self.assertRaises(UnverifiedExecution): audit_closed(R,o,f)
if __name__=="__main__": unittest.main()
