import unittest
from datetime import datetime, timedelta, timezone
from research.v2_paper_two_bar_rth_compat_20261111 import compatibility, aggregate

def b(minute,high,low,close,day="2026-11-11"):
    return {"t":f"{day}T16:{minute:02d}:00+00:00","h":high,"l":low,"c":close}
def trade(exit_at="2026-11-11T16:03:40+00:00",entry=100.0,exit=99.9):
    return {"source":"MBB","day":"2026-11-11","symbol":"TST","entry_at":"2026-11-11T16:00:10+00:00",
            "exit_at":exit_at,"entry":entry,"exit":exit,"qty":3}
class Test(unittest.TestCase):
    def setUp(self):
        self.bars=[b(0,100.02,99.96,100),b(1,100.01,99.95,99.99),b(2,100,99.94,99.98)]
    def test_tiny_underwater_two_down(self):
        x=compatibility(trade(),self.bars)
        self.assertEqual(x["status"],"TWOBAR_COMPATIBLE_NOT_CAUSE_PROVEN")
        self.assertLess(abs(x["candidate"]["three_bar_close_move_pct"]),.1)
    def test_no_after_fill_lookahead(self):
        self.assertEqual(compatibility(trade(exit_at="2026-11-11T16:02:20+00:00"),self.bars)["status"],"INSUFFICIENT_POST_ENTRY_BARS")
    def test_gap_not_consecutive(self):
        gap=[self.bars[0],b(3,100.01,99.95,99.99),b(4,100,99.94,99.98)]
        self.assertEqual(compatibility(trade(exit_at="2026-11-11T16:05:30+00:00"),gap)["status"],"NO_EXCLUSIVE_COMPATIBLE_PATTERN_IN_WINDOW")
    def test_profitable_exit_excluded(self):
        self.assertEqual(compatibility(trade(exit=100.05),self.bars)["status"],"NOT_REALIZED_LOSS")
    def test_over_one_percent_watch_excluded(self):
        bars=[b(0,99.8,99.1,99.3),b(1,99.7,99.0,99.2),b(2,99.6,98.9,99.0)]
        self.assertEqual(compatibility(trade(exit=98.9),bars)["status"],"NO_EXCLUSIVE_COMPATIBLE_PATTERN_IN_WINDOW")
    def test_trail_precedence(self):
        bars=[b(0,100.8,100.0,100.6),b(1,100.7,99.85,100.0),b(2,100.6,99.7,99.8)]
        self.assertEqual(compatibility(trade(exit=99.9),bars)["status"],"NO_EXCLUSIVE_COMPATIBLE_PATTERN_IN_WINDOW")
    def test_premarket_excluded(self):
        self.assertEqual(compatibility(trade(exit_at="2026-11-11T13:03:40+00:00"),self.bars)["status"],"NOT_RTH")
    def test_no_live_execution(self):
        x={"research_only":True,"broker_orders_submitted":0,"trades":[trade()],"bars":{"2026-11-11|TST":self.bars}}
        out=aggregate(x)
        self.assertEqual(out["summary"]["broker_orders_submitted"],0)
        self.assertEqual(out["summary"]["two_falling_compatible"],1)
    def test_reject_nonresearch_input(self):
        with self.assertRaises(ValueError):
            aggregate({"research_only":True,"broker_orders_submitted":1,"trades":[],"bars":{}})
if __name__=="__main__":unittest.main()

