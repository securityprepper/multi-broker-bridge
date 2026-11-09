"""V2 offline postforecast outcome tests. No broker connectivity."""
import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("follow",Path(__file__).with_name("v2_direction_followthrough_20261109.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def row(pred="UP",actual="UP",clock="10:00",day="2026-09-02",price=100,close=105,nextop=98,
        major=True,emergency=True):
    return dict(sector="semiconductors",day=day,checkpoint=clock,
     prediction=pred,actual=actual,sector_mark_price=price,regular_close_price=close,
     next_regular_open=nextop,close_pct=5,rth_pct=5,significant_up=major,
     significant_down=False,emergency=emergency,observed_sector_pct=2,
     severity_threshold_pct=4,bar_available_at="2026-09-02T10:00:00-04:00")
class OutcomeTests(unittest.TestCase):
    def test_favorable_up_continuation(self):
        self.assertAlmostEqual(m.continuation(row()),5)
    def test_bad_down_continuation(self):
        self.assertAlmostEqual(m.continuation(row(pred="DOWN")),-5)
    def test_abstain_no_trade_return(self):
        self.assertIsNone(m.continuation(row(pred="ABSTAIN")))
    def test_early_sell_better_than_next_open(self):
        self.assertAlmostEqual(m.hypothetical_sell_advantage(row(pred="DOWN")),1.7)
    def test_early_sell_worse_when_next_open_higher(self):
        self.assertLess(m.hypothetical_sell_advantage(row(pred="DOWN",nextop=105)),0)
    def test_broker_order_never_generated(self):
        self.assertIsNone(m.hypothetical_sell_advantage(row(pred="UP")))
    def test_empty_stats(self):
        self.assertEqual(m.stats_forecasts([])["available_days"],0)
    def test_wrong_emergency_counts(self):
        self.assertEqual(m.stats_forecasts([row(pred="DOWN")])["emergency_false"],1)
    def test_valid_emergency_counts(self):
        self.assertEqual(m.stats_forecasts([row()])["emergency_true"],1)
    def test_first_signal_only_from_qualified_clocks(self):
        s={"sectors":{"semiconductors":{"checkpoint_results":{
            "08:30":{"policy":"SHADOW_ONLY_NO_GO"},
            "09:25":{"policy":"QUALIFIED"},
            "10:00":{"policy":"QUALIFIED"}}}}}
        a=[row(clock="08:30",pred="DOWN"),
           row(clock="09:25",pred="UP"),
           row(clock="10:00",pred="DOWN")]
        r=m.evaluate(s,a)["sectors"]["semiconductors"]["first_train_qualified_forecast"]
        self.assertEqual(r["issued"],1)
        self.assertEqual(r["correct"],1)
        self.assertEqual(r["forecast_reversals_on_days_with_signal"],1)
    def test_no_qualified_strategy_is_abstain(self):
        s={"sectors":{"semiconductors":{"checkpoint_results":{
            "10:00":{"policy":"SHADOW_ONLY_NO_GO"}}}}}
        r=m.evaluate(s,[row()])["sectors"]["semiconductors"]["first_train_qualified_forecast"]
        self.assertEqual(r["issued"],0)
        self.assertEqual(r["coverage"],0)
    def test_exact_5percent_severity(self):
        s={"sectors":{"semiconductors":{"checkpoint_results":{
            "10:00":{"policy":"QUALIFIED"}}}}}
        r=m.evaluate(s,[row(pred="UP")])["sectors"]["semiconductors"]["first_train_qualified_forecast"]
        self.assertEqual(r["semi_5pct_days"],1)
        self.assertEqual(r["semi_5pct_first_direction_correct"],1)
if __name__=="__main__":unittest.main()