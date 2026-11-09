"""V2 isolated tests: as-of bar close, threshold overlaps, late observations excluded."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.v2_reliability_threshold_grid import (
    threshold_met, minute_close_at_or_before, classify_day,
    first_signal, breadth_confirm, build_rows, wilson_lower
)
ET=ZoneInfo("America/New_York")
def dt(h,m):
    return datetime(2026,1,7,h,m,tzinfo=ET)
def bars_at_close(closes):
    return {dt(h,m):(p,p) for h,m,p in closes}
class TestPrecisionThresholdGrid(unittest.TestCase):
    def test_2p5_total_includes_last_1pp(self):
        self.assertTrue(threshold_met(100,97.5,98.5,2.5,1,"down"))
        self.assertFalse(threshold_met(100,97.51,98.51,2.5,1,"down"))
    def test_recent_drop_does_not_suffice_without_total(self):
        self.assertFalse(threshold_met(100,98,99,2.5,1,"down"))
    def test_total_drop_does_not_suffice_without_recent_slope(self):
        self.assertFalse(threshold_met(100,97,97.5,2.5,1,"down"))
    def test_upside_symmetric(self):
        self.assertTrue(threshold_met(100,102.5,101.5,2.5,1,"up"))
        self.assertFalse(threshold_met(100,102.5,102,2.5,1,"up"))
    def test_3pct_stricter_than_2pct(self):
        self.assertTrue(threshold_met(100,97.5,98.5,2.0,1,"down"))
        self.assertFalse(threshold_met(100,97.5,98.5,3.0,1,"down"))
    def test_wilson_lower_bound_is_conservative(self):
        self.assertEqual(wilson_lower(0,0),0)
        self.assertLess(wilson_lower(8,10),.8)

    def test_exact_completed_candle_required(self):
        hist={dt(9,30):100}
        self.assertIsNone(minute_close_at_or_before(hist,dt(9,34)))
        self.assertEqual(minute_close_at_or_before(hist,dt(9,35)),100)
    def test_no_future_candle_can_confirm(self):
        hist={dt(9,40):97}
        self.assertIsNone(minute_close_at_or_before(hist,dt(9,40)))
        self.assertIsNone(minute_close_at_or_before(hist,dt(9,44)))
        self.assertEqual(minute_close_at_or_before(hist,dt(9,45)),97)
    def test_open_to_close_severe_is_separate_outcome_only(self):
        x=classify_day(100,91,95)
        self.assertTrue(x["severe_down"])
        self.assertFalse(x["severe_up"])
        self.assertEqual(x["total_pct"],-5.0)
    def test_open_to_close_decline_even_with_gap_up(self):
        x=classify_day(100,110,104)
        self.assertTrue(x["severe_down"])
        self.assertFalse(x["severe_up"])
    def test_no_trigger_before_three_bars_history(self):
        row={"prior":100,"bars":bars_at_close([(9,0,99),(9,5,98.5)])}
        self.assertIsNone(first_signal(row,2.5,"down",False,{}, {},["AMD"]))
    def test_first_trigger_uses_completed_15min_series(self):
        row={"prior":100,"bars":bars_at_close([(9,0,98.5),(9,5,98.3),
                                                  (9,10,98.2),(9,15,97.5),
                                                  (9,20,94.0)])}
        found=first_signal(row,2.5,"down",False,{}, {},["AMD"])
        self.assertEqual(found["when"],dt(9,20).isoformat())
        self.assertEqual(found["price"],97.5)
    def test_sector_confirmation_fails_closed_without_peers(self):
        self.assertFalse(breadth_confirm("AMD","2026-01-07",dt(9,35),"down",{}, {"SOXX":100},["AMD","SOXX"]))
    def test_prior_completed_close_never_same_day(self):
        from datetime import date,time
        data={}
        for d,close in [("2026-01-06",100),("2026-01-07",92)]:
            year,mo,dd=map(int,d.split("-"))
            start=datetime(year,mo,dd,9,30,tzinfo=ET)
            data[("AMD",d)]={start+timedelta(minutes=i*5):(close,close) for i in range(78)}
        rows=build_rows(data,["AMD"])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["prior"],100)
        self.assertEqual(rows[0]["rth_close"],92)
    def test_insufficient_previous_session_not_used(self):
        data={("AMD","2026-01-06"):{dt(9,30):(100,100)}}
        self.assertEqual(build_rows(data,["AMD"]),[])
if __name__=="__main__":
    unittest.main()
