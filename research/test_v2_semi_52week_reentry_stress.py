"""Offline unit guards for one-reentry V2 causal research prototype."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v2_semi_52week_reentry_stress import forward_reentry
class ReplayReentryTests(unittest.TestCase):
    def setup_bars(self):
        bars={};day="2026-09-01"
        for s in ("SOXX","AMD"):
            series={}
            for mins in range(9*60+30,14*60+41,5):
                t=f"{mins//60:02d}:{mins%60:02d}"
                series[t]=[100.,100.,100.,100.]
            bars[s,day]=series
        h={(s,day):[100.]*5 for s in ("SOXX","AMD")}
        return bars,h,day
    def test_no_reentry_without_asof_reconfirmation(self):
        b,h,d=self.setup_bars()
        self.assertIsNone(forward_reentry(b,h,d,"AMD",1,"10:00"))
    def test_reentry_requires_cooloff_plus_10_min_latency(self):
        b,h,d=self.setup_bars()
        for s in ("SOXX","AMD"):
            b[s,d]["10:15"][3]=100.4
        result=forward_reentry(b,h,d,"AMD",1,"10:00")
        self.assertIsNotNone(result)
        self.assertEqual(result["entry_time"],"10:25")
    def test_not_allow_reentry_after_last_admission_time(self):
        b,h,d=self.setup_bars()
        for s in ("SOXX","AMD"):b[s,d]["14:20"][3]=101.
        self.assertIsNone(forward_reentry(b,h,d,"AMD",1,"14:10"))
if __name__=="__main__":unittest.main()
