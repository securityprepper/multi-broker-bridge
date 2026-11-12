"""Synthetic causal/coverage tests for post-exit completed-bar research."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from research import v2_all_paper_postexit_completed_1m_20261111 as m
CT=ZoneInfo("America/Chicago")
DAY="2026-11-11"
def dt(hhmmss):
    return datetime.fromisoformat(DAY+"T"+hhmmss+"-06:00")
def tr(exit_hm="10:00:30",qty=4):
    return dict(day=DAY,symbol="AAA",source="MBB",entry_at=dt("09:50:00").isoformat(),
                exit_at=dt(exit_hm).isoformat(),entry=100,exit=99,qty=qty,exit_type="limit")
def bars(start="10:01:00",n=36,price=102):
    a=dt(start)
    return [dict(t=(a+timedelta(minutes=i)).isoformat(),o=price,h=price+1,
                 l=price-1,c=price,v=100) for i in range(n)]
class TestPostExit(unittest.TestCase):
    def test_two_minutes_available_only_after_completed_bar(self):
        r=m.assess(tr(),bars(),2)
        self.assertEqual(r["status"],"COMPLETED_TRADE_BAR_MARK_ONLY")
        self.assertAlmostEqual(r["mark_delta_vs_broker_exit_usd"],12)
    def test_missing_one_minute_fails_closed(self):
        path=bars()
        path.pop(1)
        self.assertEqual(m.assess(tr(),path,5)["status"],"MISSING_CONTIGUOUS_POST_EXIT_1M")
    def test_does_not_use_exit_containing_candle(self):
        # First permitted bar starts 10:01, not 10:00; a dramatic 10:00 low is irrelevant.
        path=[dict(t=dt("10:00:00").isoformat(),o=100,h=150,l=1,c=1)]+bars()
        self.assertEqual(m.assess(tr(),path,2)["counterfactual_gross_vs_entry_usd"],8)
    def test_at_cutoff_is_non_executable(self):
        self.assertEqual(m.assess(tr("13:38:30"),bars("13:39:00",2),2)["status"],
                         "PAST_CAUSAL_FLAT_CUTOFF")
    def test_flat_or_unavailable_cannot_count_as_win(self):
        self.assertEqual(m.assess(tr(),[],5)["status"],"MISSING_CONTIGUOUS_POST_EXIT_1M")
    def test_source_grouping_never_doubles_fills(self):
        x=tr()
        data=dict(research_only=True,broker_orders_submitted=0,trades=[x],
                  bars={DAY+"|AAA":bars()})
        a=m.aggregate(data)
        self.assertEqual(a["scope"]["round_trips"],1)
        self.assertEqual(a["horizons"]["5"]["ALL"]["population"],1)
        self.assertEqual(a["horizons"]["5"]["MBB"]["population"],1)
        self.assertEqual(a["horizons"]["5"]["FDR"]["population"],0)
    def test_negative_move_is_not_missed_winner(self):
        r=m.assess(tr(),bars(price=97),5)
        self.assertLess(r["mark_delta_vs_broker_exit_usd"],0)
    def test_requires_broker_evidence_research_scope(self):
        with self.assertRaises(AssertionError):
            m.aggregate(dict(research_only=True,broker_orders_submitted=1,
                             trades=[],bars={}))
    def test_assumed_cost_not_realized_commission(self):
        r=m.assess(tr(),bars(price=100),5)
        self.assertAlmostEqual(r["counterfactual_after_assumed_30bp_usd"],-1.2)
if __name__=="__main__":
    unittest.main()
