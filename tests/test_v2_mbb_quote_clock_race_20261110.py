import unittest
from datetime import datetime,timezone,timedelta
from research.v2_mbb_quote_clock_race_20261110 import (
    validate_observed_quote, classify_batch,temporal_diagnostic,old_v1_acceptance)
T=datetime(2026,11,10,14,46,40,tzinfo=timezone.utc)
def q(sec=45.78,bid="100.00",ask="100.05"):
    return {"t":(T+timedelta(seconds=sec-40)).isoformat(),"bp":bid,"ap":ask}
class ClockRace(unittest.TestCase):
 def test_proven_future_relative_to_scan_but_valid_at_receipt(self):
    quote=q()
    x=temporal_diagnostic(quote,T,T+timedelta(seconds=6))
    self.assertFalse(x["v1_accepts"])
    self.assertEqual(x["correct_at_receipt"],"ACCEPT")
 def test_true_future_quote_also_rejected_at_receipt(self):
    self.assertEqual(validate_observed_quote(q(sec=48),T+timedelta(seconds=6))["reason"],"AFTER_RECEIPT_FUTURE")
 def test_old_stale_stays_rejected(self):
    self.assertEqual(validate_observed_quote(q(sec=-100),T+timedelta(seconds=6))["reason"],"STALE")
 def test_wide_spread_still_rejected(self):
    self.assertEqual(validate_observed_quote(q(bid="100",ask="102"),T+timedelta(seconds=6))["reason"],"WIDE_SPREAD")
 def test_crossed_still_rejected(self):
    self.assertEqual(validate_observed_quote(q(bid="101",ask="100"),T+timedelta(seconds=6))["reason"],"CROSSED")
 def test_invalid_still_rejected(self):
    self.assertEqual(validate_observed_quote(q(bid="0"),T+timedelta(seconds=6))["reason"],"PRICE_INVALID")
 def test_missing_kept_distinct(self):
    r=classify_batch(["AMD","MU"],{"quotes":{"AMD":q()}},T+timedelta(seconds=6))
    self.assertEqual(r["counts"],{"ACCEPT":1,"QUOTE_ABSENT":1})
 def test_invalid_envelope_fail_closed(self):
    with self.assertRaises(ValueError):classify_batch(["AMD"],{"bad":"no quotes"},T)
 def test_no_timestamp_acceptance(self):
    self.assertEqual(validate_observed_quote({"bp":100,"ap":101},T)["reason"],"TIMESTAMP_INVALID")
 def test_retrieval_before_scan_refused(self):
    with self.assertRaises(ValueError):
      temporal_diagnostic(q(),T,T-timedelta(seconds=1))
if __name__=="__main__":unittest.main()
