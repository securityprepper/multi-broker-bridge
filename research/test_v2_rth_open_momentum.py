"""V2 point-in-time rising-sector tests; no broker IO."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_rth_open_momentum import (
    ETF, PEERS, VARIANTS, asof_open_momentum, first_signal,
    bounded_entry_to14)

D=date(2026,11,9)
def series(opening=100.,now=101.1,others=None):
    data={}
    for s in (*PEERS,ETF):
        price=(others or {}).get(s,now)
        data[s]={
          datetime.combine(D,time(9,30),ET):[opening,opening,opening,price,200],
        }
    return data

class OpenMomentumTest(unittest.TestCase):
    def test_0935_uses_only_finished_bar_and_open(self):
        bars=series()
        sig=first_signal(bars,D,"MU","early_1030")
        self.assertEqual(sig["at"][11:16],"09:35")
        self.assertIsNone(sig["next_bar_open"])

    def test_subsequent_future_does_not_change_0935(self):
        bars=series()
        bars["MU"][datetime.combine(D,time(9,35),ET)]=[100,100,90,90,100]
        self.assertAlmostEqual(first_signal(bars,D,"MU","early_1030")["price"],101.1)

    def test_lagging_15m_variant_not_available_early(self):
        bars=series()
        self.assertIsNone(asof_open_momentum(
            bars,D,datetime.combine(D,time(9,35),ET),"MU",True))

    def test_missing_peer_fails_closed(self):
        bars=series()
        del bars["AVGO"]
        self.assertIsNone(first_signal(bars,D,"MU","early_1030"))

    def test_missing_market_open_fails_closed(self):
        bars=series()
        del bars["SOXX"][datetime.combine(D,time(9,30),ET)]
        self.assertIsNone(first_signal(bars,D,"MU","early_1030"))

    def test_sector_confirm_cannot_use_one_stock(self):
        bars=series(others={s:100 for s in PEERS if s!="MU"})
        self.assertIsNone(first_signal(bars,D,"MU","early_1030"))

    def test_15minute_momentum_qualifies_at_0950(self):
        bars=series(now=100.2)
        for s in (*PEERS,ETF):
            bars[s][datetime.combine(D,time(9,45),ET)]=[101.2]*4+[100]
        sig=first_signal(bars,D,"MU","recent15_1300")
        self.assertEqual(sig["at"][11:16],"09:50")
        self.assertGreater(sig["own_recent15_pct"],.4)

    def test_15minute_momentum_rejects_stale_move(self):
        bars=series(now=101.1)
        for s in (*PEERS,ETF):
            bars[s][datetime.combine(D,time(9,45),ET)]=[101.1]*4+[100]
        self.assertIsNone(first_signal(bars,D,"MU","recent15_1300"))

    def test_next_bar_not_a_fill_and_cost_changes_eligibility(self):
        event={"price":100.0,"next_bar_open":100.1}
        a=bounded_entry_to14(event,101.0,friction_bp=15)
        b=bounded_entry_to14(event,101.0,friction_bp=30)
        self.assertTrue(a["price_eligible"])
        self.assertFalse(b["price_eligible"])
        self.assertEqual(b["modeled_return_pct"],0)

    def test_time_outside_scope_fails_closed(self):
        bars=series()
        self.assertIsNone(asof_open_momentum(
            bars,D,datetime.combine(D,time(9,30),ET),"MU"))
        self.assertIsNone(asof_open_momentum(
            bars,D,datetime.combine(D,time(13,5),ET),"MU"))
        with self.assertRaises(ValueError):
            asof_open_momentum(bars,D,datetime(2026,11,9,9,35),"MU")

    def test_valid_variants(self):
        with self.assertRaises(ValueError):
            first_signal(series(),D,"MU","wrong")
        self.assertEqual(set(VARIANTS),{"early_1030","through_1300","recent15_1300"})

if __name__=="__main__":
    unittest.main()