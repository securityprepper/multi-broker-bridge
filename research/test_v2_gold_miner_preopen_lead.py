import sys
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from research.v2_gold_miner_preopen_lead import *

def t(h,m=0):
    return datetime(2026,11,9,h,m,tzinfo=ET)

class GoldLeadCausalityTests(unittest.TestCase):
    def test_0925_only_completed_0920(self):
        b={t(9,20):(100,101,99,100,30),t(9,25):(110,111,109,110,99)}
        self.assertEqual(at(b,t(9,25))[0],100)
    def test_0945_excludes_current_0945_bar(self):
        b={t(9,40):(100,101,99,100,30),t(9,45):(110,111,109,110,99)}
        self.assertEqual(at(b,t(9,45))[0],100)
    def test_cannot_use_future_or_stale_bar(self):
        self.assertIsNone(at({t(9,25):(1,1,1,1,1)},t(9,25)))
        self.assertIsNone(at({t(8,50):(1,1,1,1,1)},t(9,25)))
    def test_qualification_requires_gold_plus_miner_breadth(self):
        f={"GLD":{"pct":.32},"GDX":{"pct":.8},"NEM":{"pct":.9},
           "AEM":{"pct":.6},"KGC":{"pct":-.2}}
        self.assertTrue(qualifies(f,"gold_breadth","up"))
        self.assertFalse(qualifies(f,"gold_breadth","down"))
    def test_miner_breadth_not_implied_by_gold_price(self):
        f={"GLD":{"pct":.9},"GDX":{"pct":.8},"NEM":{"pct":-.9},
           "AEM":{"pct":-.6},"KGC":{"pct":-.2}}
        self.assertTrue(qualifies(f,"gold_only","up"))
        self.assertFalse(qualifies(f,"gold_breadth","up"))
    def test_no_five_completed_days_no_eligibility(self):
        f={("GDX","2026-11-03"):{"close":100,"open":99},
           ("GDX","2026-11-04"):{"close":101,"open":100},
           ("GDX","2026-11-05"):{"close":102,"open":101},
           ("GDX","2026-11-06"):{"close":103,"open":102},
           ("GDX","2026-11-09"):{"close":104,"open":103}}
        prev,prior5,nxt=historical_context(f)
        self.assertEqual(prev[("GDX","2026-11-09")],103)
        self.assertNotIn(("GDX","2026-11-09"),prior5)
    def test_prev_close_not_same_day_final_close(self):
        f={("GLD","2026-11-01"):{"close":100,"open":99},
           ("GLD","2026-11-02"):{"close":120,"open":119}}
        prev,prior5,nxt=historical_context(f)
        self.assertEqual(prev[("GLD","2026-11-02")],100)
    def test_rth_outcome_separate_from_gap(self):
        o=outcome(100,95,98)
        self.assertFalse(o["major_down"]) # sharp gap recovered by close
        self.assertTrue(o["gap_down"])
        o2=outcome(100,101,96)
        self.assertTrue(o2["major_down"]) # bad intraday RTH
    def test_empty_statistics(self):
        self.assertEqual(stats([],"up")["count"],0)
    def test_wilson_exposes_low_statistical_confidence(self):
        self.assertLess(wilson(8,10),.8)

if __name__=="__main__":
    unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]