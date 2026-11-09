"""Offline premarket cohort summary tests."""
import unittest
from research.v2_premarket_prior5_stress import summary

def row(**kwargs):
    d={"big_loss":False,"pre_asof":None,"pre_early":False,
       "exit_open":None,"open_price":None,"base":100}
    d.update(kwargs)
    return d

class PremarketTests(unittest.TestCase):
    def test_alert_before_severe_counts_causal_detection(self):
        r=summary([row(big_loss=True,pre_asof="2026-11-06T08:05:00-05:00",
                       pre_early=True,exit_open=97,open_price=96)])
        self.assertEqual(r["major_down_detected"],1)
        self.assertEqual(r["major_detected_before_minus5"],1)
        self.assertEqual(r["mean_preopen_price_mark_vs_rth_open_pp"],0.9985)
    def test_missed_major_separate_from_nonmajor_alert(self):
        r=summary([row(big_loss=True),row(pre_asof="2026-11-06T08:05:00-05:00")])
        self.assertEqual(r["major_down_missed"],1)
        self.assertEqual(r["nonmajor_warnings"],1)
    def test_unscorable_warning_does_not_claim_price_benefit(self):
        r=summary([row(pre_asof="2026-11-06T08:00:00-05:00",exit_open=95)])
        self.assertEqual(r["observed_first_after_alert_and_rth_open"],0)
        self.assertIsNone(r["mean_preopen_price_mark_vs_rth_open_pp"])
    def test_holding_wins_when_market_recovers(self):
        r=summary([row(pre_asof="2026-11-06T08:00:00-05:00",
                      exit_open=95,open_price=99)])
        self.assertLess(r["mean_preopen_price_mark_vs_rth_open_pp"],0)
        self.assertEqual(r["worse_vs_open"],1)

if __name__=="__main__":
    unittest.main()
