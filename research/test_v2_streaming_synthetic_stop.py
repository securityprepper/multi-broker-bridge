"""Offline V2 synthetic-stop tests: zero broker connectivity."""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from research.v2_streaming_synthetic_stop import Quote, SyntheticStop

T = datetime(2026, 11, 9, 14, 45, tzinfo=timezone.utc)

def quote(at, bid, ask=None, size=100):
    b = D(str(bid))
    return Quote(at, b, D(str(ask)) if ask is not None else b + D("0.02"), size, size)

class SyntheticStopTests(unittest.TestCase):
    def setUp(self):
        self.s = SyntheticStop("MU", D("100"))
        self.params = dict(now=T, quote=quote(T,"97.50"),
            quote_15m_ago=quote(T-timedelta(minutes=15),"98.50"),
            available_long_qty=D("10"), verified_position=True,
            permitted_session=True, known_no_open_sell=True)

    def test_overlap_exact_boundary(self):
        result = self.s.propose(**self.params)
        self.assertIsNotNone(result)
        self.assertEqual(result.total_decline_pct, D("2.5"))
        self.assertEqual(result.recent_decline_pct_points, D("1"))
        self.assertEqual(result.limit_price, D("97.35"))

    def test_one_outstanding_intent(self):
        self.assertIsNotNone(self.s.propose(**self.params))
        self.assertIsNone(self.s.propose(**{**self.params,"now":T+timedelta(seconds=1)}))

    def test_both_thresholds_required(self):
        self.assertIsNone(self.s.propose(**{**self.params,
            "quote_15m_ago":quote(T-timedelta(minutes=15),"98.20")}))
        self.assertIsNone(SyntheticStop("MU",D("100")).propose(**{**self.params,
            "quote":quote(T,"98"), "quote_15m_ago":quote(T-timedelta(minutes=15),"99.20")}))

    def test_permissions_and_verified_long(self):
        for change in ({"permitted_session":False},{"known_no_open_sell":False},
                       {"verified_position":False},{"available_long_qty":D("0")}):
            with self.subTest(change=change):
                self.assertIsNone(SyntheticStop("MU",D("100")).propose(
                    **{**self.params,**change}))

    def test_stale_or_invalid_market_data(self):
        cases = (
            {"quote":quote(T-timedelta(seconds=4),"97.50")},
            {"quote_15m_ago":quote(T-timedelta(minutes=14),"98.50")},
            {"quote":quote(T,"97.50","99")},
            {"quote":quote(T,"97.50","97.40")},
            {"quote":quote(T,"97.50",size=0)},
        )
        for change in cases:
            with self.subTest(change=change):
                self.assertIsNone(SyntheticStop("MU",D("100")).propose(
                    **{**self.params,**change}))

    def test_deep_gap_not_chased(self):
        self.assertIsNone(self.s.propose(**{**self.params,"quote":quote(T,"90")}))

    def test_uncertain_order_blocks_new_intent(self):
        self.s.propose(**self.params)
        self.s.reconcile(broker_outcome="UNKNOWN",remaining_long_qty=D("10"),
                         known_no_open_sell=False)
        self.assertIsNone(self.s.propose(**{**self.params,
            "now":T+timedelta(seconds=1),
            "quote":quote(T+timedelta(seconds=1),"97.4")}))

    def test_partial_fill_blocks_reorder(self):
        self.s.propose(**self.params)
        self.s.reconcile(broker_outcome="PARTIAL",remaining_long_qty=D("5"),
                         known_no_open_sell=False)
        self.assertTrue(self.s.locked_uncertain)

    def test_verified_cancellation_rearms(self):
        self.s.propose(**self.params)
        self.s.reconcile(broker_outcome="CANCELLED",remaining_long_qty=D("10"),
                         known_no_open_sell=True)
        self.assertIsNotNone(self.s.propose(**{**self.params,
            "now":T+timedelta(seconds=1),
            "quote":quote(T+timedelta(seconds=1),"97.4")}))

    def test_stale_event_does_not_replay(self):
        self.assertIsNone(self.s.propose(**{**self.params,
            "now":T-timedelta(seconds=1)}))
        self.assertIsNotNone(self.s.propose(**self.params))

if __name__ == "__main__":
    unittest.main()
