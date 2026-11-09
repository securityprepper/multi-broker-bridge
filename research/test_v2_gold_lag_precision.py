"""Synthetic as-of unit tests for V2 gold miner lead/lag research."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import v2_gold_lag_precision as s
from research import v2_gold_miner_preopen_lead as g
ET=ZoneInfo("America/New_York")

class GoldLagTests(unittest.TestCase):
    def row(self,hm,price):
        t=datetime(2026,6,3,int(hm[:2]),int(hm[3:]),tzinfo=ET)
        return t,(price,price,price,price,1000)
    def setUp(self):
        bars={hm:x for hm,x in [
            ("09:25",100),("09:30",100),("09:35",100.1),("09:40",100.4),
            ("09:45",100.5),("09:50",100.6),("09:55",100.7)]}
        self.ss={}
        for sym in ("GLD","GDX","NEM","AEM","KGC"):
            self.ss[(sym,"2026-06-03")]=dict(self.row(hm,pr) for hm,pr in bars.items())
        self.prior={(sym,"2026-06-03"):[98,99,99.5,99.9,100] for sym in
                   ("GLD","GDX","NEM","AEM","KGC")}
    def test_start_timestamps_do_not_peek(self):
        dt=s.decision("2026-06-03",9,45)
        self.assertAlmostEqual(s.price_asof(self.ss[("GLD","2026-06-03")],dt),100.4)
        self.assertIsNone(s.price_asof(self.ss[("GLD","2026-06-03")],dt+timedelta(minutes=2)))
    def test_gold_lead_15min_precedes_miner_decision(self):
        dt=s.decision("2026-06-03",10,0)
        f=s.sample_features("2026-06-03",dt,15,self.ss,self.prior)
        self.assertIsNotNone(f)
        self.assertGreater(f[0],.3)
        self.assertTrue(s.qualify(f,"up","gold_plus_miner",.25))
    def test_requires_prior_five(self):
        dt=s.decision("2026-06-03",10,0)
        self.prior.pop(("KGC","2026-06-03"))
        self.assertIsNone(s.sample_features("2026-06-03",dt,15,self.ss,self.prior))
    def test_sign_selects_strongest_asof(self):
        f=(.4,{"GDX":.2,"NEM":.1,"AEM":.5,"KGC":.3})
        self.assertEqual(s.asof_choice(f,"up"),"AEM")
        self.assertEqual(s.asof_choice(f,"down"),"NEM")
    def test_outcome_labels_not_used_in_qualify(self):
        f=(.3,{"GDX":.2,"NEM":.2,"AEM":.2,"KGC":.01})
        self.assertTrue(s.qualify(f,"up","gold_plus_miner",.25))
        self.assertFalse(s.qualify(f,"down","gold_plus_miner",.25))
    def test_fee_stress_and_empty_sample(self):
        self.assertEqual(s.stats([])["signals"],0)
        rows=[{"day":"2026-06-03","net30":.2,"net15":.35,"net60":-.1,
          "major_sector_outcome":False,"observed_at":"2026-06-03T10:00:00-04:00",
          "next_open_net30":.1}]
        self.assertEqual(s.stats(rows)["profitable"],1)
        self.assertEqual(s.stats(rows)["nonmajor_warnings"],1)

if __name__=="__main__":unittest.main()
