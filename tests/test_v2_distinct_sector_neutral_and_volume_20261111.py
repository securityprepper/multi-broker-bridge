"""Synthetic causal tests for two deliberately distinct, research-only hypotheses."""
import importlib.util
import unittest
from pathlib import Path
from datetime import date

def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
m=load("novel_relative",str(Path(__file__).resolve().parents[1] / "research" / "v2_sector_neutral_dislocation_20261111.py"))
v=load("novel_volume",str(Path(__file__).resolve().parents[1] / "research" / "v2_prior5_volume_absorption_20261111.py"))
SLOTS=("09:30","09:35","09:40","09:45","09:50","09:55")
def bar(o,c=None,volume=2000):
    c=o if c is None else c
    return (o,max(o,c),min(o,c),c,volume)
def data_base():
    d={"ETF":{"09:30":bar(100),"09:55":bar(100)},
       "A":{t:bar(100,98,2000) for t in SLOTS},
       "B":{"09:30":bar(100),"09:55":bar(100,100.1)},
       "C":{"09:30":bar(100),"09:55":bar(100,100.1)}}
    return d
class TestSectorNeutral(unittest.TestCase):
    def test_sector_neutral_selected_before_exit(self):
        d=data_base();s=m.complete_asof(d,"ETF",("A","B","C"))
        self.assertEqual([x["symbol"] for x in s],["A"])
        d["A"].update({"10:05":bar(200),"11:05":bar(1),"14:40":bar(2)})
        self.assertEqual(s,m.complete_asof(d,"ETF",("A","B","C")))
    def test_sector_movement_blocks(self):
        d=data_base();d["ETF"]["09:55"]=bar(100,99)
        self.assertEqual(m.complete_asof(d,"ETF",("A","B","C")),[])
    def test_peers_falling_not_safe(self):
        d=data_base()
        for s in ("B","C"):d[s]["09:55"]=bar(100,99)
        self.assertEqual(m.complete_asof(d,"ETF",("A","B","C")),[])
    def test_require_six_completed_asof_bars(self):
        d=data_base();del d["A"]["09:45"]
        self.assertEqual(m.complete_asof(d,"ETF",("A","B","C")),[])
    def test_invalid_quotes_and_times(self):
        self.assertIsNone(m.safe_bar([1,1,1,0,-10]))
        self.assertEqual(m.date_time_key("2026-11-09T15:00:00Z"),("2026-11-09","10:00"))
    def test_cutoff_not_from_signal_count(self):
        dates=[f"2026-01-{d:02d}" for d in range(1,11)]
        data={"SOXX":{d:{"09:30":bar(100),"09:55":bar(100)} for d in dates}}
        self.assertEqual(m.chronological_cutoff(data),dates[7])
class TestAbsorption(unittest.TestCase):
    def dates(self):
        return [f"2026-05-{d:02d}" for d in range(1,8)]
    def complete(self,c=100.5,volume=4000):
        return {t:bar(100,c,volume) for t in SLOTS}
    def test_five_previously_completed_sessions(self):
        dates=self.dates()
        b={d:self.complete(volume=4000) for d in dates[:5]}
        b[dates[5]]=self.complete(volume=11000)
        signal=v.signal_on_day("A",dates[5],b,5)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["prior5_end_date"],dates[4])
        self.assertEqual(signal["source_bar_complete_et"],dates[5]+"T10:00:00")
    def test_excludes_uncompleted_previous_session(self):
        dates=self.dates()
        b={d:self.complete() for d in dates[:4]}
        b[dates[4]]={"09:30":bar(100)}
        b[dates[5]]=self.complete(volume=12000)
        self.assertIsNone(v.signal_on_day("A",dates[5],b,5))
    def test_future_prices_do_not_change_signal(self):
        dates=self.dates()
        b={d:self.complete() for d in dates[:5]}
        b[dates[5]]=self.complete(volume=12000)
        s=v.signal_on_day("A",dates[5],b,5)
        b[dates[5]]["14:40"]=bar(1_000_000)
        self.assertEqual(s,v.signal_on_day("A",dates[5],b,5))
    def test_no_threshold_tuning_future_leak(self):
        dates=self.dates()
        b={d:self.complete() for d in dates[:5]}
        b[dates[5]]=self.complete(c=100.5,volume=5000)
        self.assertIsNone(v.signal_on_day("A",dates[5],b,5))
        b[dates[5]]=self.complete(c=101.5,volume=15000)
        self.assertIsNone(v.signal_on_day("A",dates[5],b,5))
    def test_1hr_exit_from_future_entry_not_signal_price(self):
        d={"A":{"10:05":bar(110),"11:05":bar(111),"14:40":bar(112)},
           "ETF":{"10:05":bar(100),"11:05":bar(100),"14:40":bar(100)},
           "B":{"10:05":bar(100),"11:05":bar(100),"14:40":bar(100)},
           "C":{"10:05":bar(100),"11:05":bar(100),"14:40":bar(100)}}
        a=v.trade_returns(d,"A","ETF",("A","B","C"))
        self.assertAlmostEqual(a["after30bp_60m"],100/110-0.30,places=3)
        self.assertAlmostEqual(a["after30bp_flat"],200/110-0.30,places=3)
if __name__=="__main__":unittest.main()