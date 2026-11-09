"""Offline V2 sector threshold audit and time-reference tests."""
import unittest
from research.v2_emergency_threshold_full_year_20261109 import LIMITS,summarize
def session(open_,close,hi,lo,pre=None,post=None):
    return {"open":open_,"close":close,"rth_high":hi,"rth_low":lo,
            "pre":pre or [],"post":post or [],"rth_bars":78}
class TestSectorThresholds(unittest.TestCase):
    def test_owner_percentages(self):
        self.assertEqual(LIMITS["semiconductors"],{"day":2.,"night":3.})
        self.assertEqual(LIMITS["gold_miners"],{"day":2.,"night":2.})
        for k in ("energy","financials","industrials","healthcare","software"):
            self.assertEqual(LIMITS[k],{"day":3.,"night":3.})
    def test_day_reference_is_today_open_not_previous_close(self):
        # Day two opens much higher than yesterday but trades flat within RTH.
        d={"2026-11-03":session(100,100,101,99),
           "2026-11-04":session(110,110,111,109)}
        x=summarize("semiconductors",d)
        self.assertEqual(x["day_touched"]["either"],0)
        self.assertEqual(x["night_gap_at_open"]["up"],1)
    def test_day_up_down_intrabar_reversal_deduped(self):
        d={"2026-11-03":session(100,100,103,97)}
        x=summarize("semiconductors",d)
        self.assertEqual(x["day_touched"],{"up":1,"down":1,"either":1,"both":1})
        self.assertEqual(x["day_closed_beyond"]["either"],0)
    def test_night_uses_previous_close(self):
        d={"2026-11-03":session(100,101,102,99,
            post=[("t",(101,105,101,104,500))]),
           "2026-11-04":session(101,101,101,100)}
        x=summarize("semiconductors",d)
        self.assertEqual(x["night_sip_observed_or_gap_touched"]["up"],1)
        self.assertEqual(x["night_gap_at_open"]["up"],0)
        self.assertEqual(x["day_touched"]["up"],0)
    def test_night_gap_without_extended_bars_is_observable(self):
        d={"2026-11-03":session(100,100,100,99),
           "2026-11-04":session(96,96,97,95)}
        x=summarize("semiconductors",d)
        self.assertEqual(x["night_gap_at_open"]["down"],1)
        self.assertEqual(x["night_sip_observed_or_gap_touched"]["down"],1)
        self.assertEqual(x["night_with_any_ext_sip_bars"],0)
    def test_down_beyond_close_does_not_duplicate(self):
        d={"2026-11-03":session(100,97,101,96)}
        x=summarize("semiconductors",d)
        self.assertEqual(x["day_closed_beyond"]["down"],1)
        self.assertEqual(x["day_touched"]["down"],1)
if __name__=="__main__":unittest.main()
