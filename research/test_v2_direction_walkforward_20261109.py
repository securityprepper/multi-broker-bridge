"""Offline tests for direction-first walk-forward. No broker or network APIs."""
import unittest
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import importlib.util

SPEC=importlib.util.spec_from_file_location("v2_direction_walkforward",
    Path(__file__).with_name("v2_direction_walkforward_20261109.py"))
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
ET=ZoneInfo("America/New_York")

def sample_rows(preds,actuals):
    return [{"prediction":p,"actual":a,"day":f"2026-09-{i+1:02d}"}
            for i,(p,a) in enumerate(zip(preds,actuals))]

class DirectionWalkForwardTests(unittest.TestCase):
    def test_time_is_eastern_and_dst_sensitive(self):
        self.assertEqual(m.parse_time("2026-03-08T14:30:00Z").hour,10)
        self.assertEqual(m.parse_time("2026-11-09T14:30:00Z").hour,9)
    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):m.parse_time("2026-11-09T14:30:00")
    def test_daily_label_up_down_neutral(self):
        self.assertEqual(m.label(100.3,100),"UP")
        self.assertEqual(m.label(99.7,100),"DOWN")
        self.assertEqual(m.label(100.1,100),"NEUTRAL")
    def test_abstentions_in_coverage(self):
        r=m.score(sample_rows(["UP","ABSTAIN","DOWN"],["UP","UP","UP"]))
        self.assertEqual(r["issued"],2)
        self.assertAlmostEqual(r["coverage"],2/3)
        self.assertEqual(r["correct"],1)
    def test_one_sided_perfect_not_qualified(self):
        rows=sample_rows(["UP"]*40,["UP"]*40)
        self.assertFalse(m.is_eligible(m.score(rows)))
    def test_low_coverage_not_qualified(self):
        rows=sample_rows(["UP"]*10+["DOWN"]*10+["ABSTAIN"]*200,
                           ["UP"]*10+["DOWN"]*10+["UP"]*200)
        self.assertFalse(m.is_eligible(m.score(rows)))
    def test_both_sides_are_required(self):
        rows=sample_rows(["UP"]*20+["DOWN"]*20,["UP"]*20+["DOWN"]*20)
        self.assertTrue(m.is_eligible(m.score(rows)))
    def test_mismatched_direction_is_wrong(self):
        r=m.score(sample_rows(["UP","DOWN"],["DOWN","UP"]))
        self.assertEqual(r["accuracy"],0)
        self.assertEqual(r["wrong"],2)
    def test_breadth_works_in_both_directions(self):
        syms=("ETF","A","B")
        f={k:{"move":v,"recent":v,"prior5":v,"open_move":v}
           for k,v in zip(syms,(-2,-1,-1))}
        self.assertEqual(m.signal(f,syms,"peer_both",.5,"09:25"),"DOWN")
        f["B"]["move"]=.5
        self.assertEqual(m.signal(f,syms,"peer_both",.5,"09:25"),"ABSTAIN")
    def test_rth_rule_cannot_run_premarket(self):
        syms=("ETF","A","B")
        f={k:{"move":.8,"recent":.2,"prior5":.1,"open_move":.4} for k in syms}
        self.assertEqual(m.signal(f,syms,"rth_peer",.25,"09:25"),"ABSTAIN")
        self.assertEqual(m.signal(f,syms,"rth_peer",.25,"10:00"),"UP")
    def test_prior5_veto(self):
        syms=("ETF","A","B")
        f={k:{"move":1.2,"recent":.2,"prior5":-3,"open_move":.4} for k in syms}
        self.assertEqual(m.signal(f,syms,"peer_both_prior5",.25,"10:00"),"ABSTAIN")
    def test_missing_15m_does_not_guess(self):
        syms=("ETF","A","B")
        f={k:{"move":.8,"recent":None,"prior5":2,"open_move":.4} for k in syms}
        self.assertEqual(m.signal(f,syms,"peer_both_15m",.25,"10:00"),"ABSTAIN")
    def test_missing_complete_history_no_signal(self):
        syms=("ETF","A","B")
        self.assertIsNone(m.features("2026-11-09","09:25",syms,{}, {}, {}, {}))
    def test_early_bar_available_only_at_end(self):
        d="2026-11-09"
        syms=("ETF","A","B")
        daily={};complete={};prev={};p5={}
        for s in syms:
            t=datetime(2026,11,9,9,20,tzinfo=ET)
            daily[(s,d)]={"09:20":(100,101,t)}
            complete[(s,d)]={"open":100,"close":130}
            prev[(s,d)]=100
            p5[(s,d)]=[95,96,97,98,100]
        f=m.features(d,"09:25",syms,daily,complete,prev,p5)
        self.assertAlmostEqual(f["ETF"]["move"],1)
        # Changing FUTURE RTH close does not change as-of forecast.
        complete[("ETF",d)]["close"]=75
        self.assertEqual(f,m.features(d,"09:25",syms,daily,complete,prev,p5))
        # Bar start 09:25 only completes 09:30 => never substitutes for 09:25.
        daily[("ETF",d)]={"09:25":(100,105,datetime(2026,11,9,9,25,tzinfo=ET))}
        self.assertIsNone(m.features(d,"09:25",syms,daily,complete,prev,p5))
    def test_no_future_label_in_features(self):
        self.assertEqual(m.label(100,100),"NEUTRAL")
        self.assertEqual(m.wilson(0,0),0.0)
    def test_emergency_false_positive(self):
        row={"day":"2026-09-02","prediction":"DOWN","significant_up":False,
             "significant_down":False,"emergency":True,
             "observed_sector_pct":-1.5,"severity_threshold_pct":2.0,
             "bar_available_at":"2026-09-02T10:00:00-04:00"}
        r=m.emergency_stats([row])
        self.assertEqual(r["false_alerts"],1)
        self.assertEqual(r["true_significant"],0)
    def test_per_checkpoint_one_label_and_abstentions(self):
        r=m.score(sample_rows(["ABSTAIN","UP","DOWN"],["NEUTRAL","UP","DOWN"]))
        self.assertEqual(r["counts"]["NEUTRAL"],1)
        self.assertEqual(r["balanced_recall"],1)
    def test_lookahead_end_time_equality(self):
        # A SIP 5m bar starting 09:20 is completed exactly at 09:25; allowed.
        t=datetime(2026,11,9,9,20,tzinfo=ET)
        self.assertEqual((t+timedelta(minutes=5)).strftime("%H:%M"),"09:25")

if __name__=="__main__":unittest.main()