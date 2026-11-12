import unittest
from v2_live_exit_source_drift_20261112 import audit

BASE = '''class TrendMonitor:
 def scan(self,now):
  if cutoff:
   reason = "flat"
  elif is_early_market(now):
   if _two_falling(bars):
    reason = "early"
  elif change <= LOSS_WATCH:
   reason = "loss"
  elif change >= PROFIT_TARGET:
   reason = "profit"
  elif high >= entry and trail <= -TRAIL_REVERSAL:
   reason = "trail"
'''
AUTO = '''def send(side, row):
 recorded = {}
 if side == "sell":
  recorded["exit_signal_reason"] = str(row.get("reason", "UNKNOWN"))
  recorded["exit_fill_verified"] = False
'''

class AuditTests(unittest.TestCase):
 def test_only_premarket_two_bar(self):
  result = audit(BASE, AUTO)
  self.assertFalse(result["rth_independent_two_falling_present"])
  self.assertEqual(result["premarket_two_falling_calls"], 1)

 def test_detects_rth_two_bar(self):
  trend = BASE + '  elif _two_falling(bars):\n   reason = "two falling"\n'
  self.assertTrue(audit(trend, AUTO)["rth_independent_two_falling_present"])

 def test_reason_field(self):
  self.assertTrue(audit(BASE, AUTO)["sell_order_submission_reason_field_present"])

 def test_sell_acceptance_not_fill(self):
  self.assertTrue(audit(BASE, AUTO)["sell_submission_explicitly_not_verified_fill"])

 def test_would_reject_false_fill_flag(self):
  self.assertFalse(audit(BASE, AUTO.replace("= False", "= True"))["sell_submission_explicitly_not_verified_fill"])

 def test_broken_source_fails(self):
  with self.assertRaises(SyntaxError):
   audit("!!", AUTO)

 def test_missing_monitor_fails(self):
  with self.assertRaises(ValueError):
   audit("class Other: pass", AUTO)

 def test_missing_rth_loss_guard_fails(self):
  with self.assertRaises(ValueError):
   audit(BASE.replace("change <= LOSS_WATCH", "change <= 0"), AUTO)

if __name__ == "__main__":
 unittest.main()
