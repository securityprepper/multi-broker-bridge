"""Synthetic evidence-integrity tests for macro calendar budget, not trading."""
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime,timezone,time
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT=Path(__file__).resolve().parents[1]/"research"/"v2_macro_event_opportunity_budget_20261113.py"
s=importlib.util.spec_from_file_location("macro_budget",SCRIPT)
mod=importlib.util.module_from_spec(s)
s.loader.exec_module(mod)
ET=ZoneInfo("America/New_York")

def stub(day,asof_h=9,asof_m=30,initial=100,late=101):
    a=datetime(day.year,day.month,day.day,asof_h,asof_m,tzinfo=ET).astimezone(timezone.utc).isoformat()
    b=datetime(day.year,day.month,day.day,14,35,tzinfo=ET).astimezone(timezone.utc).isoformat()
    return {a:[initial,initial,initial,initial,100],b:[late,late,late,late,100]}

class ResearchMacroDates(unittest.TestCase):
    def test_disjoint_event_calendar(self):
        self.assertFalse(mod.CPI&mod.JOBS)
        self.assertFalse(mod.CPI&mod.FOMC)
        self.assertFalse(mod.JOBS&mod.FOMC)
    def test_fomc_uses_only_1405_asof_five_minute_bar(self):
        b={time(9,30):100,time(14,0):101,time(14,35):103}
        self.assertEqual(mod.asof_pair(b,"FOMC"),(101,103))
        self.assertEqual(mod.asof_pair(b,"CPI"),(100,103))
    def test_fomc_unknown_when_first_five_minute_candle_missing(self):
        self.assertIsNone(mod.asof_pair({time(9,30):100,time(14,35):103},"FOMC"))
    def test_missing_exit_bar_cannot_produce_return(self):
        self.assertIsNone(mod.asof_pair({time(9,30):100},"JOBS"))
    def test_timezone_dst_aware_matching(self):
        z=datetime(2026,7,14,9,30,tzinfo=ET)
        self.assertEqual(z.astimezone(timezone.utc).hour,13)
        self.assertEqual(mod.utciso(z.astimezone(timezone.utc).isoformat()).astimezone(ET).hour,9)
    def test_data_fails_closed_on_invalid_ohlc(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bars.json"
            dat=stub(datetime(2026,11,6))
            dat[next(iter(dat))]=[100,99,98,100,100]
            p.write_text(json.dumps({"SOXX":dat}))
            with self.assertRaisesRegex(ValueError,"Invalid OHLC"):mod.load_symbol("SOXX",str(p))
    def test_event_not_used_as_a_buy_prediction_and_control_excludes_it(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bars.json"
            j=stub(datetime(2026,11,6),initial=100,late=103)
            j.update(stub(datetime(2026,11,5),initial=100,late=100.1))
            p.write_text(json.dumps({"SOXX":j}))
            x=mod.evaluate({"SOXX":str(p)})
            self.assertTrue(x["no_trade_or_buy_signal"])
            self.assertFalse(x["consensus_surprises_available"])
            self.assertTrue(x["realized_move_not_known_at_decision"])
            v=x["results"]["SOXX"]["JOBS"]
            self.assertEqual(v["observed"],1)
            self.assertEqual(v["abs_forward_gt_30bp"],1)
            self.assertEqual(v["control_non_event_days"],1)
            self.assertEqual(v["control_abs_forward_gt_30bp"],0)
            self.assertEqual(v["forward_up_count"],1)
            self.assertEqual(v["signal_time_et"],"09:35")
            self.assertEqual(v["exit_time_et"],"14:40")
    def test_missing_future_event_not_called_observed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"bars.json"
            p.write_text(json.dumps({"SOXX":stub(datetime(2026,11,6))}))
            v=mod.evaluate({"SOXX":str(p)})["results"]["SOXX"]["CPI"]
            self.assertEqual(v["observed"],0)
    def test_research_has_no_broker_transport_or_order_execution(self):
        source=SCRIPT.read_text()
        for banned in ("urllib.request","requests.post(", "paper_api(", "broker_api(", "/v2/orders"):
            self.assertNotIn(banned,source)
    def test_event_window_is_after_actual_release_time(self):
        self.assertEqual(mod.asof_pair({time(14,0):100,time(14,35):101},"FOMC"),(100,101))
        self.assertEqual(mod.asof_pair({time(9,30):100,time(14,35):101},"JOBS"),(100,101))
    def test_magnitude_is_not_a_direction_prediction(self):
        self.assertEqual(mod.realized(.007),(True,True))
        self.assertEqual(mod.realized(-.007),(True,True))
        self.assertEqual(mod.realized(.002),(False,False))

if __name__=="__main__":unittest.main()
