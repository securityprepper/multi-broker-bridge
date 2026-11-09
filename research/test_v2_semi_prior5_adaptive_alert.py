import unittest
from datetime import datetime, timezone
from research.v2_semi_prior5_adaptive_alert import *
from research.v2_semi_emergency_precision import eligible

def closed_sessions(values,add_future=False):
    d={}
    for i,v in enumerate(values,1):
        day=f"2026-10-{i:02}"
        d[day]={"15:55":(datetime(2026,10,i,15,55,tzinfo=timezone.utc),v,v)}
    if add_future:
        d["2026-10-12"]={"15:55":(datetime(2026,10,12,15,55,tzinfo=timezone.utc),.5,.5)}
    return d

class PriorFiveAsOfTests(unittest.TestCase):
    def test_requires_six_prior_completed_closes(self):
        self.assertIsNone(prior5_mean_abs_close_pct(closed_sessions([100,101,102,103,104]),"2026-10-06"))
    def test_never_reads_same_day_or_future_close(self):
        d=closed_sessions([100,101,102,103,104,105])
        a=prior5_mean_abs_close_pct(d,"2026-10-07")
        d["2026-10-07"]={"15:55":(None,999999,999999)}
        d["2026-10-08"]={"15:55":(None,999999,999999)}
        self.assertEqual(a,prior5_mean_abs_close_pct(d,"2026-10-07"))
    def test_use_exact_five_completed_returns(self):
        d=closed_sessions([100,101,102,103,104,105])
        expected=mean([1,100/101,100/102,100/103,100/104])
        self.assertAlmostEqual(prior5_mean_abs_close_pct(d,"2026-10-07"),expected,places=8)
    def test_floored_adaptive_threshold(self):
        d=closed_sessions([100,101,102,103,104,105])
        self.assertEqual(asof_threshold("prior5_abs1p00_min2",d,"2026-10-07"),2.0)
        self.assertEqual(asof_threshold("fixed3",d,"2026-10-07"),3.0)
    def test_volatile_prior5_widens_not_thins(self):
        d=closed_sessions([100,110,100,110,100,110])
        self.assertGreater(asof_threshold("prior5_abs1p00_min2",d,"2026-10-07"),3)
    def test_overlapping_2p5_includes_1point_recent(self):
        day="2026-11-09"
        t=datetime(2026,11,9,9,45,tzinfo=timezone.utc)
        ser={"X":{day:{"09:45":(t,98.5,98.5),"10:00":(t+timedelta(minutes=15),97.5,97.5)}}}
        self.assertTrue(eligible(ser,"X",day,"10:00",100.,2.5,1.0,"none"))
        self.assertFalse(eligible(ser,"X",day,"10:00",100.,3.0,1.0,"none"))
    def test_score_empty_no_claim(self):
        self.assertEqual(score([],17)["alerts"],0)

if __name__=="__main__":
    unittest.main()
