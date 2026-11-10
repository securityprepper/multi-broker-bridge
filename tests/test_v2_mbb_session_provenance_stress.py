"""No-broker synthetic tests for stale MBB session ownership hazards."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from v2_mbb_session_provenance_stress import (
    when, historical_wall_key, trading_session_day,
    session_key_discontinuity, fake_cross_strategy_flatten,
)


class SessionKeyAndProvenanceTest(unittest.TestCase):
    def test_evening_rollover_starts_next_ct_trading_session(self):
        self.assertEqual(str(trading_session_day(when("2026-11-09T19:00:01"))),
                         "2026-11-10")

    def test_before_evening_rollover_same_ct_day(self):
        self.assertEqual(str(trading_session_day(when("2026-11-09T18:59:59"))),
                         "2026-11-09")

    def test_ny_wall_key_differs_at_night_start(self):
        at = when("2026-11-09T21:30:00")
        self.assertEqual(historical_wall_key(at), "2026-11-09")
        self.assertEqual(str(trading_session_day(at)), "2026-11-10")

    def test_same_session_crosses_ny_midnight(self):
        before = when("2026-11-09T21:30:00")
        after = when("2026-11-09T23:30:00")
        self.assertEqual(trading_session_day(before), trading_session_day(after))
        self.assertNotEqual(historical_wall_key(before), historical_wall_key(after))

    def test_legacy_reservation_is_split_in_same_session(self):
        result = session_key_discontinuity()
        self.assertTrue(result["legacy_both_reservations_accepted"])
        self.assertEqual(result["wall_date_keys"], ["2026-11-09", "2026-11-10"])

    def test_normalized_session_reservation_blocks_second(self):
        self.assertTrue(session_key_discontinuity()["session_key_only_first_accepted"])

    def test_stale_ledger_can_attribute_other_strategy_position(self):
        x = fake_cross_strategy_flatten()
        self.assertEqual(x["status"], "FLATTEN_IN_PROGRESS")
        self.assertEqual(x["fake_sell_quantities"], ["2"])
        self.assertEqual(x["fake_sell_order_types"], ["market"])

    def test_no_position_stale_ledger_does_not_sell(self):
        x = fake_cross_strategy_flatten(new_qty=None)
        self.assertEqual(x["status"], "FLAT_IN_BROKER_SNAPSHOT")
        self.assertEqual(x["fake_sell_count"], 0)

    def test_unmanaged_order_blocks_exit(self):
        x = fake_cross_strategy_flatten(manual_open_order=True)
        self.assertEqual(x["status"], "UNMANAGED_ORDER_BLOCKED")
        self.assertEqual(x["fake_sell_count"], 0)

    def test_manual_shares_above_tracked_quantity_blocked(self):
        x = fake_cross_strategy_flatten(new_qty=5)
        self.assertEqual(x["status"], "OrderRejected")
        self.assertEqual(x["fake_sell_count"], 0)

    def test_spring_dst_session_boundary(self):
        self.assertEqual(str(trading_session_day(when("2026-03-09T19:05:00"))),
                         "2026-03-10")

    def test_fall_dst_session_boundary(self):
        self.assertEqual(str(trading_session_day(when("2026-11-02T19:05:00"))),
                         "2026-11-03")


if __name__ == "__main__":
    unittest.main()
