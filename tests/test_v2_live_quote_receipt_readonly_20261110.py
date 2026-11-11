"""Network- and broker-free checks for raw latest-response auditor."""
import unittest
from datetime import datetime,timedelta,timezone
from research.v2_live_quote_receipt_readonly_20261110 import categorize_response,fetch_latest
T=datetime(2026,11,10,14,46,40,tzinfo=timezone.utc)
def q(at_offset=5.8,bid="100",ask="100.05"):
 return {"t":(T+timedelta(seconds=at_offset)).isoformat(),"bp":bid,"ap":ask}
class TestQuoteObserver(unittest.TestCase):
 def test_same_quote_future_at_start_acceptable_at_receipt(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q()}},T,T+timedelta(seconds=6))
  self.assertEqual(result["old_future_but_valid_at_receipt"],["AMD"])
  self.assertEqual(result["correct_receipt_clock_counts"],{"ACCEPT":1})
 def test_truly_future_stays_rejected(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q(10)}},T,T+timedelta(seconds=6))
  self.assertEqual(result["correct_receipt_clock_counts"],{"FUTURE":1})
 def test_missing_stays_missing(self):
  result=categorize_response(["AMD"],{"quotes":{}},T,T+timedelta(seconds=6))
  self.assertEqual(result["correct_receipt_clock_counts"],{"MISSING":1})
 def test_old_stale_stays_stale(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q(-200)}},T,T+timedelta(seconds=6))
  self.assertEqual(result["correct_receipt_clock_counts"],{"STALE":1})
 def test_wide_stays_wide(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q(5,bid="100",ask="105")}},T,T+timedelta(seconds=6))
  self.assertEqual(result["correct_receipt_clock_counts"],{"WIDE_SPREAD":1})
 def test_crossed_stays_crossed(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q(5,bid="102",ask="101")}},T,T+timedelta(seconds=6))
  self.assertEqual(result["correct_receipt_clock_counts"],{"CROSSED":1})
 def test_malformed_response_fails(self):
  with self.assertRaises(ValueError):categorize_response(["AMD"],{"bad":[]},T,T)
 def test_unknown_symbol_rejected(self):
  with self.assertRaises(ValueError):categorize_response(["AMD"],{"quotes":{"PWR":q()}},T,T+timedelta(seconds=6))
 def test_unrecognized_feed_never_request(self):
  with self.assertRaises(ValueError):fetch_latest(["AMD"],"iex",{},opener=lambda *a,**k: self.fail("Network"))
 def test_no_orders_and_no_broker_calls(self):
  result=categorize_response(["AMD"],{"quotes":{"AMD":q()}},T,T+timedelta(seconds=6))
  self.assertEqual(result["orders_submitted"],0)
  self.assertEqual(result["broker_api_calls"],0)
if __name__=="__main__":unittest.main()
