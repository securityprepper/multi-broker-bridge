"""Offline V2 causality, alert, ranking, and data-coverage regression tests."""
import unittest
from datetime import date, datetime, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_open_relative_blindspots_and_admission_caps import (
    at_open_relative_move, first_open_decline, cap_admissions, earliest, THRESHOLDS
)
D = date(2026,11,9)
A = datetime(2026,11,9,9,30,tzinfo=ET)
def record(op,cl):
    return [op,max(op,cl),min(op,cl),cl,50]
def fixture(stockclose=98.4,sectorclose=198.0):
    return {"MU":{A:record(100,stockclose),A+timedelta(minutes=5):record(98,97)},
            "SOXX":{A:record(200,sectorclose),A+timedelta(minutes=5):record(199,199)}}
class OfflineTests(unittest.TestCase):
    def test_completed_bar_not_lookahead(self):
        bars=fixture()
        at=A+timedelta(minutes=5)
        e=first_open_decline(bars,D,"MU",1.5)
        self.assertEqual(e["asof"],at.isoformat())
        self.assertAlmostEqual(e["own_from_open_pct"],-1.6)
        # Following bar may wildly change WITHOUT changing earlier alert.
        bars["MU"][at]=record(95,150)
        self.assertEqual(first_open_decline(bars,D,"MU",1.5)["asof"],at.isoformat())
        self.assertIsNone(at_open_relative_move(bars,D,"MU",A))

    def test_both_reference_and_sector_filter(self):
        bars=fixture(stockclose=98.4,sectorclose=200.2)
        self.assertIsNotNone(first_open_decline(bars,D,"MU",1.5,sector=False))
        self.assertIsNone(first_open_decline(
            {"MU":{A:bars["MU"][A]}, "SOXX":{A:bars["SOXX"][A]}},
            D, "MU", 1.5, sector=True))
        # sector may catch up only by following completed bar
        assert first_open_decline(bars,D,"MU",1.5,sector=True)["asof"]==(A+timedelta(minutes=10)).isoformat()

    def test_threshold_sensitivity(self):
        bars=fixture(stockclose=98.4,sectorclose=198)
        self.assertIsNotNone(first_open_decline(bars,D,"MU",1.5))
        self.assertIsNone(first_open_decline({"MU":{A:record(100,98.4)}},D,"MU",2.5))
        with self.assertRaises(ValueError):first_open_decline(bars,D,"MU",-1)

    def test_missing_market_observation(self):
        self.assertIsNone(first_open_decline({"MU":{A:record(100,98)}},D,
                                             "MU",1,sector=True))
        self.assertIsNone(first_open_decline({"MU":{}},D,"MU",1))

    def test_no_future_session(self):
        bars=fixture()
        self.assertIsNone(at_open_relative_move(bars,D,"MU",A+timedelta(days=1)))
        with self.assertRaises(ValueError):
            at_open_relative_move(bars,D,"MU",datetime(2026,11,9,9,35))

    def test_first_candidate_tiebreak_no_outcomes(self):
        events=[
          {"at":"2026-11-09T09:40:00-05:00","own_open_pct":6,"sym":"A"},
          {"at":"2026-11-09T09:35:00-05:00","own_open_pct":2,"sym":"B"},
          {"at":"2026-11-09T09:35:00-05:00","own_open_pct":3,"sym":"C"},
        ]
        self.assertEqual([x["sym"] for x in cap_admissions(events,2)],["C","B"])
        self.assertEqual(len(cap_admissions(events,None)),3)
        with self.assertRaises(ValueError):cap_admissions(events,0)

    def test_earliest_does_not_look_at_future_values(self):
        a={"asof":"2026-11-09T09:35:00-05:00","next_bar_open":None}
        b={"asof":"2026-11-09T09:40:00-05:00","next_bar_open":999}
        self.assertIs(earliest(a,b),a)
    def test_fixed_variants(self):
        self.assertEqual(len(THRESHOLDS),5)

if __name__=="__main__":unittest.main()
