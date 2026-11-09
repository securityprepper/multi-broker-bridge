"""Isolated deterministic tests for as-of evening warning and outcome separation."""
import unittest
from datetime import datetime, time
from zoneinfo import ZoneInfo

from research.v2_evening_next_open_gap import (
    ET, compute_rows, index_bars, parse_bar, previous_five_return,
    snapshot_bar, strict_overlap_at, summarize, warning,
)

def bar(close, vol=10):
    return (close, close, close, close, vol)

def ix_with(clock_prices):
    # Bars indexed at their START, not completed until five minutes later.
    return {("2026-01-05",t):bar(v) for t,v in clock_prices.items()}


class AsOfEveningTests(unittest.TestCase):
    def test_utc_to_new_york_during_dst(self):
        self.assertEqual(parse_bar("2026-07-01T20:55:00Z").hour, 16)
        self.assertEqual(parse_bar("2026-01-05T21:55:00Z").hour, 16)

    def test_evening_snapshot_uses_completed_bar_only(self):
        ix=ix_with({time(16,55):98,time(17,0):87})
        self.assertEqual(snapshot_bar(ix,"2026-01-05",time(17))[3],98)

    def test_missing_or_zero_volume_is_unobserved(self):
        self.assertIsNone(snapshot_bar({}, "2026-01-05",time(17)))
        self.assertIsNone(snapshot_bar(ix_with({time(16,55):bar(99,0)[3]}),"2026-01-06",time(17)))
        self.assertIsNone(snapshot_bar(ix_with({time(16,55):99}),"2026-01-05",time(19)))

    def test_prior_five_uses_only_six_closes_through_today(self):
        days=[f"2026-01-{i:02d}" for i in range(1,8)]
        closes={d:100+i*2 for i,d in enumerate(days)}
        self.assertIsNone(previous_five_return(days,closes,days[4]))
        self.assertAlmostEqual(previous_five_return(days,closes,days[5]),10.0)
        closes[days[6]]=99999
        self.assertAlmostEqual(previous_five_return(days,closes,days[5]),10.0)

    def test_symmetric_down_up_breadth(self):
        self.assertEqual(warning(-1.5,-.5,[-.8]*4),"DOWN")
        self.assertEqual(warning(1.5,.5,[.8]*4),"UP")
        self.assertIsNone(warning(-1.5,-.5,[-.8]*3))
        self.assertEqual(warning(-2.5,None,[]),"DOWN")
        self.assertEqual(warning(2.5,None,[]),"UP")
        self.assertIsNone(warning(-1,None,[]))

    def test_strict_overlap_inclusive_not_additive(self):
        ix=ix_with({time(16,40):98.5,time(16,55):97.5})
        result=strict_overlap_at(ix,"2026-01-05",time(17),100)
        self.assertEqual(result["total_pct"],-2.5)
        self.assertEqual(result["last15_pp"],-1.0)
        self.assertTrue(result["trigger"])

    def test_strict_total_alone_not_enough(self):
        ix=ix_with({time(16,40):97.75,time(16,55):97.5})
        self.assertFalse(strict_overlap_at(ix,"2026-01-05",time(17),100)["trigger"])

    def test_strict_missing_15m_is_unknown(self):
        self.assertIsNone(strict_overlap_at(ix_with({time(16,55):97}),"2026-01-05",time(17),100))

    def test_overnight_outcome_not_a_signal_input(self):
        days=["2025-12-29","2025-12-30","2025-12-31",
              "2026-01-02","2026-01-05","2026-01-06","2026-01-07"]
        bars={}
        for d in days:
            bars[(d,time(9,30))]=bar(100)
            bars[(d,time(15,55))]=bar(100)
            bars[(d,time(16,55))]=bar(97)
            bars[(d,time(17))]=bar(97.9)
        idx={"AMD":bars.copy()}
        baseline={(days[-1],"AMD")}
        before=compute_rows(idx,baseline=baseline)[0]
        idx["AMD"][(days[-1],time(9,30))]=bar(75)
        after=compute_rows(idx,baseline=baseline)[0]
        # Score is allowed to change: it is an outcome-only diagnostic.
        def decision(w):
            return {k:v for k,v in w.items()
                    if k != "estimated_advantage_vs_next_open_pp_outcome_only"}
        self.assertEqual(decision(before["warnings"]["17:00"]),
                         decision(after["warnings"]["17:00"]))
        self.assertNotEqual(before["next_open_gap_outcome_only"],after["next_open_gap_outcome_only"])
        self.assertEqual(before["warnings"]["17:00"]["asof"],
                         "2026-01-06T17:00:00-05:00")

    def test_earliest_alarm_and_nonmajor_accounting(self):
        rows=[{"next_open_gap_outcome_only":-7,
               "observed":{"17:00":True,"19:00":False},
               "warnings":{"17:00":{"asof":"2026-01-05T17:00:00-05:00","direction":"DOWN",
               "stock_evening_pct":-3,"estimated_advantage_vs_next_open_pp_outcome_only":2}},
               "symbol":"AMD","period":"earlier","strict_overlap":{},
               "prior5_completed_sessions_pct":0},
              {"next_open_gap_outcome_only":2,
               "observed":{"17:00":True,"19:00":False},
               "warnings":{"17:00":{"asof":"2026-01-05T17:00:00-05:00","direction":"DOWN",
               "stock_evening_pct":-2,"estimated_advantage_vs_next_open_pp_outcome_only":-2}},
               "symbol":"MU","period":"earlier","strict_overlap":{},
               "prior5_completed_sessions_pct":0}]
        x=summarize(rows)
        self.assertEqual(x["either_17_or_19"]["down"]["hits"],1)
        self.assertEqual(x["either_17_or_19"]["down"]["nonmajor_warnings"],1)

if __name__=="__main__":
    unittest.main()
