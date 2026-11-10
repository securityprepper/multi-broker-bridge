"""Order-free, broker-free risk regression tests for V2 ownership model."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.v2_mbb_session_ownership_gate import Activity, Evidence, classify, trading_session_key

CT = ZoneInfo("America/Chicago")


def at(day=10, hour=4, minute=32):
    return datetime(2026, 11, day, hour, minute, tzinfo=CT)


def base(**kw):
    return replace(Evidence(
        symbol="AMD", broker_shares="0", asof=at(),
        positions_complete=True, orders_complete=True,
        orders_history_complete=True, activities_complete_from_flat_anchor=True,
        writer_registry_complete=True, unknown_submissions=False,
        any_open_orders=False, exclusive_mbb_lease_proven=False,
        tracked_origin_session="2026-11-09"), **kw)


def fill(i, side, n, writer="MBB"):
    return Activity(f"a{i}", f"order{i}", writer, "AMD", side, str(n))


class OwnershipTests(unittest.TestCase):
    def check(self, proof, expected, purpose="entry", now=None):
        self.assertEqual(classify(now or at(), proof, purpose=purpose,
                                  holiday_unpaused=True).result, expected)

    def test_session_key_matches_overnight_chicago_not_new_york_date(self):
        self.assertEqual(trading_session_key(at(9, 18, 59)), "2026-11-09")
        self.assertEqual(trading_session_key(at(9, 19)), "2026-11-10")
        self.assertEqual(trading_session_key(at(9, 21, 30)), "2026-11-10")
        self.assertEqual(trading_session_key(at(9, 23, 30)), "2026-11-10")
        self.assertEqual(trading_session_key(at(10, 4)), "2026-11-10")

    def test_dst_with_local_cutoff(self):
        for day in (datetime(2026, 3, 9, 19, tzinfo=CT),
                    datetime(2026, 11, 9, 19, tzinfo=CT)):
            self.assertEqual(trading_session_key(day),
                             (day.date()+timedelta(days=1)).isoformat())

    def test_prior_day_closed_rearms_only_after_complete_readback(self):
        p=base(activities=(fill(1,"buy",4),fill(2,"sell",4)))
        self.check(p,"NEW_SESSION_FIRST_ENTRY_ELIGIBLE_FOR_NORMAL_GATES")
        self.check(p,"VERIFIED_FLAT_NO_EXIT_ORDER",purpose="flatten")
        self.check(replace(p, activities_complete_from_flat_anchor=False),
                   "BLOCK_INCOMPLETE_OR_STALE_READBACK")

    def test_same_session_attempt_still_locked(self):
        p=base(current_session_attempts=1)
        self.check(p,"SAME_SESSION_REENTRY_REQUIRES_BROKER_PROOF")

    def test_unknown_or_partial_order_not_rearmed(self):
        self.check(base(unknown_submissions=True),"BLOCK_PENDING_OR_UNKNOWN_ORDERS")
        self.check(base(any_open_orders=True),"BLOCK_PENDING_OR_UNKNOWN_ORDERS")
        self.check(base(orders_history_complete=False),"BLOCK_INCOMPLETE_OR_STALE_READBACK")

    def test_stale_snapshot_cannot_rearm(self):
        self.check(base(asof=at()-timedelta(minutes=2)),
                   "BLOCK_INCOMPLETE_OR_STALE_READBACK")

    def test_flat_sqlite_tracking_cannot_authorize_sale(self):
        self.check(base(),"VERIFIED_FLAT_NO_EXIT_ORDER",purpose="flatten")

    def test_other_writer_replaced_stale_symbol_cannot_be_sold(self):
        p=base(broker_shares="2",activities=(fill(1,"buy",4),
            fill(2,"sell",4),fill(3,"buy",2,"OTHER")))
        self.check(p,"BLOCK_AND_ESCALATE_OWNERSHIP",purpose="flatten")

    def test_aggregate_qty_matching_mbb_not_enough_without_exclusive_lease(self):
        p=base(broker_shares="4",activities=(fill(1,"buy",4),))
        self.check(p,"BLOCK_AND_ESCALATE_OWNERSHIP",purpose="flatten")
        self.check(replace(p,exclusive_mbb_lease_proven=True),
                   "VERIFIED_MBB_EXIT_OBLIGATION",purpose="flatten")

    def test_mixed_writer_broker_equal_cannot_sell(self):
        p=base(broker_shares="6",activities=(fill(1,"buy",4),
          fill(2,"buy",2,"OTHER")),exclusive_mbb_lease_proven=True)
        self.check(p,"BLOCK_AND_ESCALATE_OWNERSHIP",purpose="flatten")

    def test_duplicates_and_unmatched_fills_are_blocked(self):
        f=fill(1,"buy",4)
        self.check(base(broker_shares="4",activities=(f,f)),
                   "BLOCK_UNRECONCILED_ACTIVITY",purpose="flatten")
        self.check(base(broker_shares="4",activities=(f,)),
                   "BLOCK_AND_ESCALATE_OWNERSHIP",purpose="flatten")
        self.check(base(broker_shares="4",activities=(fill(1,"sell",4),)),
                   "BLOCK_INVENTORY_DRIFT_OR_SHORT",purpose="flatten")

    def test_inventory_drift_blocks(self):
        p=base(broker_shares="3",activities=(fill(1,"buy",4),))
        self.check(p,"BLOCK_INVENTORY_DRIFT_OR_SHORT",purpose="flatten")

    def test_missing_writer_registry_blocks(self):
        self.check(base(writer_registry_complete=False),
                   "BLOCK_INCOMPLETE_OR_STALE_READBACK")

    def test_entry_cutoff_but_protection_can_still_be_required(self):
        p=base(broker_shares="4", activities=(fill(1,"buy",4),),
               exclusive_mbb_lease_proven=True, asof=at(10,14,0))
        self.check(p,"BLOCK_1315_ENTRY_CUTOFF",now=at(10,14,0))
        self.check(p,"VERIFIED_MBB_EXIT_OBLIGATION",
                   purpose="flatten",now=at(10,14,0))

    def test_holiday_fail_closed(self):
        d=classify(at(),base(),purpose="entry",holiday_unpaused=False)
        self.assertEqual(d.result,"BLOCK_HOLIDAY_GATE")


if __name__=="__main__":
    unittest.main()
