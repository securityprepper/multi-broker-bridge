"""Isolated tests for V2 no-lookahead 20-session anti-churn replay."""
import importlib.util
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

P=Path(__file__).with_name("v2_20session_anti_churn_replay.py")
spec=importlib.util.spec_from_file_location("v2_anti_churn",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def bars():
    times=[(datetime(2026,11,6,9,30,tzinfo=ZoneInfo("America/New_York"))+timedelta(minutes=i)).strftime("%H:%M") for i in range(311)]
    return {s:{t:[100.,100.,100.,100.,1000,"sip"] for t in times} for s in m.ALL},times

class AntiChurnTests(unittest.TestCase):
    def test_signal_uses_completed_0934_not_current_or_future(self):
        b,_=bars()
        for s in ("SOXX","AMD","MU"):b[s]["09:34"][3]=100.5
        old=m.sign_at_window(b,{s:100 for s in m.ALL})
        self.assertEqual(old,1)
        for s in m.ALL:
            b[s]["09:35"][3]=0.01
            b[s]["14:40"][3]=10000
        self.assertEqual(m.sign_at_window(b,{s:100 for s in m.ALL}),old)
    def test_bearish_signal(self):
        b,_=bars()
        for s in ("SOXX","AMD","MU"):b[s]["09:34"][3]=99.6
        self.assertEqual(m.sign_at_window(b,{s:100 for s in m.ALL}),-1)
    def test_no_signal(self):
        b,_=bars()
        self.assertEqual(m.sign_at_window(b,{s:100 for s in m.ALL}),0)
    def test_stock_selection_requires_asof_strength(self):
        b,_=bars()
        b["AMD"]["09:34"][3]=100.5
        self.assertEqual(m.eligible_stocks(b,{s:100 for s in m.ALL},1),["AMD"])
    def test_previous_five_excludes_today_and_future(self):
        series=[(f"2026-11-0{i}",float(i)) for i in range(1,7)]
        series += [("2026-11-09",999),("2026-11-10",888)]
        self.assertEqual(m.previous_five(series,"2026-11-09"),[2.,3.,4.,5.,6.])
    def test_tight_exit_at_next_open_not_trigger_close(self):
        b,t=bars()
        b["AMD"][t[10]][3]=99.7
        b["SOXX"][t[10]][3]=99.88
        b["AMD"][t[11]][0]=98.95
        z=m.outcome(b,"AMD",1,5,"one_min_sector_tight")
        self.assertEqual(z["exit_at"],"09:41")
        self.assertEqual(z["reason"],"ONE_MIN_REVERSAL")
        self.assertAlmostEqual(z["gross_pct"],-1.05,places=3)
    def test_target_reacts_to_completed_bar_then_next_open(self):
        b,t=bars()
        b["MU"][t[10]][3]=101.2
        b["MU"][t[11]][0]=100.9
        z=m.outcome(b,"MU",1,5,"one_pct_target_stop")
        self.assertEqual(z["exit_at"],"09:41")
        self.assertAlmostEqual(z["gross_pct"],.9,places=3)
    def test_hold_to_1340_chicago(self):
        b,t=bars()
        b["SNDK"]["14:40"][0]=103
        z=m.outcome(b,"SNDK",1,5,"hold_1340_CT")
        self.assertEqual(z["exit_at"],"14:40")
        self.assertEqual(z["reason"],"TIME_1340_CT")
        self.assertEqual(z["duration_min"],305)
        self.assertAlmostEqual(z["net30_pct"],2.7)
    def test_cost_deducted_per_trade(self):
        b,t=bars()
        z=m.outcome(b,"AMD",1,5,"hold_1340_CT")
        self.assertAlmostEqual(z["net30_pct"],z["gross_pct"]-0.30,places=5)
    def test_split_basis_three_to_one_normalized_asof(self):
        b,_=bars()
        for row in b["SOXX"].values():
            for i in range(4):row[i]=300.
        self.assertEqual(m.reconcile_sector_price_basis(b,100.),3)
        self.assertAlmostEqual(b["SOXX"]["09:34"][3],100.)
        self.assertEqual(m.sign_at_window(b,{s:100 for s in m.ALL}),0)
    def test_split_basis_one_to_one_preserved(self):
        b,_=bars()
        b["SOXX"]["09:34"][3]=101.
        self.assertEqual(m.reconcile_sector_price_basis(b,100.),1)
        self.assertEqual(b["SOXX"]["09:34"][3],101.)
    def test_unknown_split_basis_fails_closed(self):
        b,_=bars()
        b["SOXX"]["09:34"][3]=200.
        with self.assertRaises(ValueError):
            m.reconcile_sector_price_basis(b,100.)

if __name__=="__main__":
    unittest.main()
