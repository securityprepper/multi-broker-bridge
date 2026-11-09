"""Offline research gate tests (not trading authorization)."""
import unittest
from research.v2_precision_gate import *
class PrecisionGateTests(unittest.TestCase):
    def test_empty_never_qualifies(self):
        self.assertFalse(evaluate([]).approved_for_further_paper_testing)
    def test_80percent_not_sufficient_without_independent_days(self):
        trades=[FinishedTrade("2026-11-09",1,"10:00","semis")]*80+[FinishedTrade("2026-11-09",-1,"10:00","semis")]*20
        r=evaluate(trades)
        self.assertEqual(r.precision,.8)
        self.assertFalse(r.approved_for_further_paper_testing)
    def test_90percent_independent_days_pass(self):
        trades=[FinishedTrade(f"day-{i:02}",1 if i<=27 else -1,"10:00","gold") for i in range(1,31)]
        self.assertTrue(evaluate(trades).approved_for_further_paper_testing)
    def test_winner_rate_not_sufficient_if_losses_larger(self):
        trades=[FinishedTrade(f"day-{i:02}",.1 if i<=27 else -5,"10:00","gold") for i in range(1,31)]
        self.assertFalse(evaluate(trades).approved_for_further_paper_testing)
    def test_wilson(self):
        self.assertEqual(wilson_lower(0,0),0)
        self.assertLess(wilson_lower(8,10),.8)
    def test_unequal_sector_volatility(self):
        self.assertEqual(emergency_threshold_pct(.5,2),2)
        self.assertEqual(emergency_threshold_pct(3,2),3.75)
    def test_gold_lead_causal_and_session_matched(self):
        self.assertFalse(leading_signal_eligible("10:05","10:00","rth","rth",True,True))
        self.assertFalse(leading_signal_eligible("09:30","10:00","premarket","rth",True,True))
        self.assertTrue(leading_signal_eligible("09:30","10:00","rth","rth",True,True))
        self.assertFalse(leading_signal_eligible("09:30","10:00","rth","rth",False,True))
if __name__=="__main__":
    unittest.main()
