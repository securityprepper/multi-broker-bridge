"""Synthetic offline as-of checks for the 1-minute premarket coverage audit."""
import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from v2_premarket_bar_coverage_quality_20261109 import audit_day, bar_available_at, minute_sets, iso_minute_utc

def sample(date="2026-11-06"):
    stamp="2026-11-06T09:00:00Z"  # 04:00 ET in November
    row=[1.,1.1,.9,1.05,100]
    return {s:{stamp:row} for s in ("SOXX","AMD","MU","SNDK")}

class TestCoverage(unittest.TestCase):
    def test_complete_all_four(self):
        r=audit_day("2026-11-06",sample())
        self.assertEqual(r["soxx_and_all_three_peers_present"],1)
        self.assertEqual(r["amd_mu_sndk_3of3_present"],1)
        self.assertFalse(r["executable_nbbo_or_fill_verified"])
    def test_missing_etf_fails_joint(self):
        d=sample();d["SOXX"]={}
        r=audit_day("2026-11-06",d)
        self.assertEqual(r["soxx_and_all_three_peers_present"],0)
        self.assertEqual(r["amd_mu_sndk_3of3_present"],1)
    def test_missing_stock_fails_joint(self):
        d=sample();d["MU"]={}
        self.assertEqual(audit_day("2026-11-06",d)["amd_mu_sndk_3of3_present"],0)
    def test_no_prior_day_leak(self):
        d=sample()
        self.assertEqual(audit_day("2026-11-09",d)["soxx_and_all_three_peers_present"],0)
    def test_no_rth_mark(self):
        d=sample()
        for s in d:
            d[s]["2026-11-06T14:30:00Z"]=[2.,2.2,1.9,2.1,10]
        self.assertEqual(audit_day("2026-11-06",d)["soxx_and_all_three_peers_present"],1)
    def test_reject_invalid_bar(self):
        d=sample();d["AMD"]["2026-11-06T09:00:00Z"]=[float("nan"),2,1,1]
        self.assertEqual(audit_day("2026-11-06",d)["soxx_and_all_three_peers_present"],0)
    def test_reject_naive_time(self):
        with self.assertRaises(ValueError):iso_minute_utc("2026-11-06T08:00:00")
    def test_reject_nonaligned(self):
        d=sample()
        d["MU"]={"2026-11-06T09:00:03Z":[1,2,1,2]}
        with self.assertRaises(ValueError):minute_sets("2026-11-06",d)
    def test_correct_completed_timestamp(self):
        a=bar_available_at("2026-11-09","04:18")
        self.assertEqual(a.strftime("%H:%M:%S"),"04:19:15")
        self.assertEqual(a.tzinfo, ZoneInfo("America/New_York"))
    def test_dst_aware(self):
        a=bar_available_at("2026-07-09","04:18")
        self.assertEqual(a.astimezone(timezone.utc).strftime("%H:%M:%S"),"08:19:15")
        b=bar_available_at("2026-11-09","04:18")
        self.assertEqual(b.astimezone(timezone.utc).strftime("%H:%M:%S"),"09:19:15")

if __name__=="__main__":
    unittest.main()
