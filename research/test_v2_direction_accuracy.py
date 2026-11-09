import unittest
from datetime import datetime,timedelta,timezone
from research.v2_direction_accuracy import Forecast,evaluate
T=datetime(2026,11,9,15,tzinfo=timezone.utc)
def row(side="UP",close=103,date="2026-11-09",bar=None,cutoff=None):
    return Forecast("semis",date,T,bar or T-timedelta(minutes=5),
                    cutoff or T+timedelta(hours=6),side,100,close)
class Tests(unittest.TestCase):
    def test_both_directions(self):
        self.assertEqual(row().actual,"UP")
        self.assertEqual(row(close=97).actual,"DOWN")
    def test_unchanged_neutral(self):
        self.assertEqual(row(close=100).actual,"NEUTRAL")
    def test_abstain_coverage(self):
        r=evaluate([row("ABSTAIN"),row("DOWN",97,"2026-11-10")])
        self.assertEqual(r["coverage"],.5)
    def test_asof(self):
        with self.assertRaises(ValueError):row(bar=T+timedelta(seconds=1))
        with self.assertRaises(ValueError):row(cutoff=T)
    def test_one_sided_not_qualified(self):
        self.assertFalse(evaluate([row()])["candidate_for_paper_shadow"])
    def test_both_sides_can_qualify_for_shadow(self):
        r=evaluate([row(),row("DOWN",97,"2026-11-10")],min_days=2)
        self.assertTrue(r["candidate_for_paper_shadow"])
    def test_wrong_forecast(self):
        self.assertEqual(evaluate([row("DOWN")])["accuracy"],0.)
    def test_duplicates(self):
        with self.assertRaises(ValueError):evaluate([row(),row()])
if __name__=="__main__":unittest.main()
