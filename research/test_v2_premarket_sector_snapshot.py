"""Pure offline as-of tests for premarket sector breadth candidate."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_premarket_sector_snapshot import (
    ETF,PEERS,fixed_snapshot,earliest_signal,price_mark,preopen_up_baseline)
TODAY=date(2026,11,9)
PREV=date(2026,11,6)
def bar(value):
    return [value,value,value,value,100]
def fixture(direction="down"):
    sign=-1 if direction=="down" else 1
    b={}
    closes={}
    for s in (*PEERS,ETF):
        b[s]={datetime.combine(TODAY,time(8,25),ET):bar(100+sign*0.8),
              datetime.combine(TODAY,time(9,10),ET):bar(100+sign*0.8),
              datetime.combine(TODAY,time(8,30),ET):bar(100+sign*0.8),
              datetime.combine(TODAY,time(9,15),ET):bar(100+sign*0.8)}
        closes[s]={PREV:100}
    b["MU"][datetime.combine(TODAY,time(8,25),ET)]=bar(100+sign*1.2)
    b["MU"][datetime.combine(TODAY,time(9,10),ET)]=bar(100+sign*1.2)
    return b,closes
class PreopenTests(unittest.TestCase):
    def test_down_signal_sector_and_own(self):
        bars,closes=fixture()
        event=fixed_snapshot(bars,closes,"MU",PREV,TODAY,time(8,30),"down")
        self.assertEqual(event["asof"],datetime.combine(TODAY,time(8,30),ET).isoformat())
        self.assertEqual(event["peer_count"],7)
        self.assertEqual(event["aligned"],7)
    def test_up_side_mirrors_down(self):
        b,c=fixture("up")
        self.assertTrue(fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"up"))
        self.assertIsNone(fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"down"))
    def test_missing_peer_fails_closed(self):
        b,c=fixture()
        del b["WDC"][datetime.combine(TODAY,time(8,25),ET)]
        self.assertIsNone(fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"down"))
    def test_does_not_read_future_bar(self):
        b,c=fixture()
        original=fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"down")
        b["MU"][datetime.combine(TODAY,time(8,30),ET)]=bar(50)
        after=fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"down")
        self.assertEqual(original["asof"],after["asof"])
        self.assertEqual(original["own_move_pct"],after["own_move_pct"])
        self.assertNotEqual(original["next_bar_open"],after["next_bar_open"])
    def test_late_snapshot_fallback(self):
        b,c=fixture()
        del b["SOXX"][datetime.combine(TODAY,time(8,25),ET)]
        event=earliest_signal(b,c,"MU",PREV,TODAY,"down")
        self.assertEqual(event["asof"],datetime.combine(TODAY,time(9,15),ET).isoformat())
    def test_requires_own_magnitude_even_with_sector_confirmation(self):
        b,c=fixture()
        b["MU"][datetime.combine(TODAY,time(8,25),ET)]=bar(99.5)
        self.assertIsNone(fixed_snapshot(b,c,"MU",PREV,TODAY,time(8,30),"down"))
    def test_limit_price_unfilled_not_assumed_to_execute(self):
        r={"observed_price":98.8,"next_bar_open":97.0}
        result=price_mark(r,100,98.5,"down")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["vs_0930_pp"],0)
    def test_friday_evening_not_monday_signal(self):
        starts={datetime(2026,11,6,18,0,tzinfo=ET):bar(105),
                datetime(2026,11,6,17,45,tzinfo=ET):bar(101)}
        self.assertIsNone(preopen_up_baseline(starts,TODAY,PREV,100))
    def test_valid_same_day_premarket_up_baseline(self):
        starts={datetime.combine(TODAY,time(8,25),ET):bar(103),
                datetime.combine(TODAY,time(8,10),ET):bar(101.8)}
        self.assertEqual(preopen_up_baseline(starts,TODAY,PREV,100),
            datetime.combine(TODAY,time(8,30),ET).isoformat())
    def test_end_day_marks_scored_but_not_signals(self):
        r={"observed_price":98.8,"next_bar_open":98.8}
        v=price_mark(r,100,98.6,'down',97.0)
        self.assertTrue(v['eligible'])
        self.assertGreater(v['vs_close_pp'],0)
    def test_up_price_mark(self):
        r={"observed_price":101.2,"next_bar_open":101.2}
        result=price_mark(r,100,102,"up")
        self.assertTrue(result["eligible"])
        self.assertGreater(result["vs_0930_pp"],0)
if __name__=="__main__":unittest.main()