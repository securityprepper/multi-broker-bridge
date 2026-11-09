"""Smoke tests for the V2 direction report — not brokerage functionality."""
import unittest
from datetime import datetime,timedelta,timezone
from research.v2_sector_direction_scoring import DirectionObservation,evaluate,wilson_lower
T=datetime(2026,11,9,15,5,tzinfo=timezone.utc)
def o(pred,final=101,day="2026-11-09",bar=None):
    return DirectionObservation("semis",day,T,bar or T, pred,100,final)
class TestDirectionScoring(unittest.TestCase):
    def test_bull(self):
        self.assertEqual(o("UP").actual,"UP")
    def test_bear(self):
        self.assertEqual(o("DOWN",99).actual,"DOWN")
    def test_abstain_reduces_coverage(self):
        x=evaluate([o("UP"),o("ABSTAIN",day="2026-11-10")])
        self.assertEqual(x["issued"],1)
        self.assertEqual(x["coverage"],.5)
    def test_both_sides(self):
        x=evaluate([o("UP"),o("DOWN",99,day="2026-11-10")])
        self.assertEqual(x["correct"],2)
        self.assertEqual(x["down"]["precision"],1)
    def test_future_bar_rejected(self):
        with self.assertRaises(ValueError):
            o("UP",bar=T+timedelta(seconds=1))
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([o("UP"),o("DOWN")])
    def test_wilson_nonzero_uncertainty(self):
        self.assertLess(wilson_lower(20,20),1)
        self.assertGreater(wilson_lower(20,20),.80)
    def test_no_forecasts(self):
        self.assertIsNone(evaluate([o("ABSTAIN")])["accuracy"])
if __name__=="__main__":unittest.main()
