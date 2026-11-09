"""V2 research-only as-of/stops/cost regression; no external broker imports."""
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import v2_52week_delayed_anti_churn as sem
import v2_cross_sector_0935_risk_replay as cross
def make_bars():
    bars={}
    for s in ("SOXX","AMD","MU","SNDK"):
        rows={}
        for mins in range(9*60+30,14*60+41,5):
            t=f"{mins//60:02d}:{mins%60:02d}"
            price=100.0
            rows[t]=[price,price,price,price]
        bars[s,"2026-09-01"]=rows
    return bars
class ResearchTests(unittest.TestCase):
    def test_signal_uses_completed_0930_only(self):
        b=make_bars();h={(s,"2026-09-01"):[100]*5 for s in sem.SYMS}
        for s in sem.SYMS:b[s,"2026-09-01"]["09:30"][3]=101
        direction,names,_=sem.forecast("2026-09-01",b,h)
        self.assertEqual(direction,1);self.assertEqual(len(names),3)
        for s in sem.SYMS:
            b[s,"2026-09-01"]["14:40"][3]=1
            b[s,"2026-09-01"]["09:40"][3]=1
        self.assertEqual(sem.forecast("2026-09-01",b,h)[0],1)
    def test_two_sided_signal(self):
        b=make_bars();h={(s,"2026-09-01"):[100]*5 for s in sem.SYMS}
        for s in sem.SYMS:b[s,"2026-09-01"]["09:30"][3]=99
        self.assertEqual(sem.forecast("2026-09-01",b,h)[0],-1)
    def test_insufficient_peer_confirmation_abstains(self):
        b=make_bars();h={(s,"2026-09-01"):[100]*5 for s in sem.SYMS}
        b["SOXX","2026-09-01"]["09:30"][3]=101
        b["AMD","2026-09-01"]["09:30"][3]=101
        self.assertEqual(sem.forecast("2026-09-01",b,h)[0],0)
    def test_hold_flat_mark_and_cost(self):
        b=make_bars()
        for t in b["AMD","2026-09-01"]:
            b["AMD","2026-09-01"][t]=[100,100,100,100]
        b["AMD","2026-09-01"]["14:40"][0]=102
        e=sem.replay(b,"2026-09-01","AMD",1,"hold")
        self.assertEqual(e["entry_time"],"09:40")
        self.assertEqual(e["exit_time"],"14:40")
        self.assertEqual(e["net30"],1.7)
        self.assertEqual(e["net60"],1.4)
    def test_delayed_stop_following_completed_bar(self):
        b=make_bars()
        # 09:40 bar is completed only at 09:45. Stop gets one extra 5m execution latency.
        b["AMD","2026-09-01"]["09:40"][3]=97
        b["AMD","2026-09-01"]["09:45"][0]=97
        b["AMD","2026-09-01"]["09:50"][0]=98
        x=sem.replay(b,"2026-09-01","AMD",1,"hard_stop_2p5")
        self.assertEqual(x["exit_time"],"09:50")
        self.assertTrue(x["triggered"])
        self.assertEqual(x["net30"],-2.3)
    def test_trailing_stop_not_armed_without_gain(self):
        b=make_bars()
        b["AMD","2026-09-01"]["09:40"][3]=98
        x=sem.replay(b,"2026-09-01","AMD",1,"trail_2p5_after_1")
        self.assertFalse(x["triggered"])
        self.assertEqual(x["exit_time"],"14:40")
    def test_day_equal_not_equal_trade_when_clusters_unbalanced(self):
        rows=[
          {"day":"A","net30":2,"net60":1.7,"side":"UP","mae":0,"triggered":False,"hold_minutes":20},
          {"day":"A","net30":2,"net60":1.7,"side":"UP","mae":0,"triggered":False,"hold_minutes":20},
          {"day":"B","net30":-4,"net60":-4.3,"side":"DOWN","mae":-3,"triggered":True,"hold_minutes":10}]
        a=sem.sample_metrics(rows)
        self.assertEqual(a["trades"],3)
        self.assertEqual(a["day_equal_avg_after30"],-1)
        self.assertEqual(a["avg_after30"],0)
    def test_gold_spot_must_confirm_side(self):
        b=make_bars()
        day="2026-09-01"
        for s in ("GDX","NEM","AEM","KGC","GLD"):b[s,day]={t:v.copy() for t,v in b["AMD",day].items()}
        h={(s,day):[100]*5 for s in ("GDX","NEM","AEM","KGC","GLD")}
        for s in ("GDX","NEM","AEM","KGC"):b[s,day]["09:30"][3]=101
        self.assertEqual(cross.sector_signal(day,b,h,"GDX",("NEM","AEM","KGC"),"GLD")[0],0)
        b["GLD",day]["09:30"][3]=100.2
        self.assertEqual(cross.sector_signal(day,b,h,"GDX",("NEM","AEM","KGC"),"GLD")[0],1)
    def test_missing_intermediate_bars_rejected(self):
        b=make_bars()
        del b["AMD","2026-09-01"]["09:45"]
        self.assertIsNone(sem.replay(b,"2026-09-01","AMD",1,"hold"))
if __name__=="__main__":unittest.main()
