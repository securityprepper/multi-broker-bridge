"""No broker dependencies. Causality and overlapping trigger boundary tests."""
import unittest
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from research import v2_stock_risk_dayphase as s

ET=ZoneInfo("America/New_York")

class OfflineStudyTests(unittest.TestCase):
    def test_two_conditions_overlap_exact_boundary(self):
        self.assertTrue(s.alert(100,98.5,97.5))
        self.assertFalse(s.alert(100,99,97.6))
        self.assertFalse(s.alert(100,97.5,97.4))
        self.assertFalse(s.alert(100,99.5,98.5))
    def test_complete_five_minute_bar_asof(self):
        target=date(2026,11,9)
        at=datetime(2026,11,9,8,45,tzinfo=ET)
        bars={at-timedelta(minutes=15):[99,99,99,98.6,1],
              at:[97.5,97.5,97.5,97.5,1]}
        r=s.first_signal(bars,100,target,date(2026,11,6),{"premarket"})
        self.assertEqual(r[0],at+timedelta(minutes=5))
        self.assertEqual(r[1],"premarket")
    def test_no_preceding_friday_evening_for_monday(self):
        t=datetime(2026,11,6,18,0,tzinfo=ET)
        self.assertIsNone(s.phase(t,date(2026,11,9),date(2026,11,6)))
    def test_open_hour_cannot_masquerade_as_premarket(self):
        d=date(2026,11,9)
        self.assertEqual(s.phase(datetime(2026,11,9,10,5,tzinfo=ET),d,date(2026,11,6)),"rth_open_hour")
        self.assertIsNone(s.phase(datetime(2026,11,9,10,30,tzinfo=ET),d,date(2026,11,6)))
    def test_missing_prior_fifteen_minute_bar_is_no_alert(self):
        d=date(2026,11,9)
        t=datetime(2026,11,9,8,50,tzinfo=ET)
        self.assertIsNone(s.first_signal({t:[97,97,97,97,1]},100,d,date(2026,11,6),{"premarket"}))

if __name__=="__main__":
    unittest.main()
