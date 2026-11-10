"""Pure synthetic UUID-join regression tests; no broker calls or credentials."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import importlib.util

SOURCE = Path(__file__).resolve().parents[1] / "research" / "v2_mbb_broker_uuid_chain.py"
spec = importlib.util.spec_from_file_location("v2_mbb_broker_uuid_chain", SOURCE)
import sys
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

CT = ZoneInfo("America/Chicago")
asof = datetime(2026, 11, 10, 4, 45, tzinfo=CT)
anchor = datetime(2026, 11, 8, 14, 0, tzinfo=CT)
day9 = datetime(2026, 11, 9, 7, 30, tzinfo=CT)

def order(name="ob", cid="MBB-20261109-B-AMD", side="buy",
          qty="4", filled="4", status="filled", when=day9,
          writer="MBB", attested=True, symbol="AMD"):
    return m.BrokerOrder(name,cid,symbol,side,qty,filled,status,when,writer,attested)

def activity(name="f1", oid="ob", side="buy", qty="4",
             when=day9+timedelta(seconds=10), symbol="AMD"):
    return m.FillActivity(name,oid,symbol,side,qty,when)

def proof(**changes):
    baseline = m.Proof("AMD",asof,anchor,"0",True,True,True,True,(),())
    return replace(baseline, **changes)

def closed(quantity="4"):
    buy=order(qty=quantity,filled=quantity)
    sell=order("os","MBB-20261109-S-AMD","sell",quantity,quantity,
               when=day9+timedelta(minutes=3))
    return (buy,sell), (activity(qty=quantity),
        activity("f2","os","sell",quantity,when=day9+timedelta(minutes=3, seconds=5)))

class ChainTests(unittest.TestCase):
    def check(self,p, expected):
        got=m.verify(p)
        self.assertEqual(got.status, expected)
        return got

    def test_closed_prior_day_can_be_attributed_as_flat(self):
        orders,fills=closed()
        r=self.check(proof(orders=orders,activities=fills),
                     "FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")
        self.assertEqual((r.mbb_net,r.other_net),("0","0"))
        self.assertEqual(len(r.normalized_activities),2)

    def test_multi_partial_fill_uuids_sum_to_one_filled_order(self):
        p=proof(orders=(order(),),activities=(activity(qty="1"),
                   activity("f2",qty="3",when=day9+timedelta(seconds=20))),
                broker_position_quantity="4")
        r=self.check(p,"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")
        self.assertEqual((r.mbb_net,len(r.normalized_activities)),("4",2))

    def test_foreign_writer_shares_cannot_be_misassigned_to_mbb(self):
        p=proof(orders=(order("of","FDR-20261109-B-AMD",
                       writer="OTHER",qty="2",filled="2"),),
                activities=(activity(oid="of",qty="2"),),
                broker_position_quantity="2")
        r=self.check(p,"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")
        self.assertEqual((r.mbb_net,r.other_net),("0","2"))

    def test_mixed_writers_reconcile_arithmetic_but_not_exclusive_lease(self):
        p=proof(orders=(order(),order("of","FDR-20261109-B-AMD",
                       writer="OTHER",qty="2",filled="2")),
                activities=(activity(),activity("f2","of",qty="2")),
                broker_position_quantity="6")
        r=self.check(p,"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")
        self.assertEqual((r.mbb_net,r.other_net),("4","2"))

    def test_duplicate_fill_uuid_rejected(self):
        p=proof(orders=(order(),),activities=(activity(qty="2"),
                        activity(qty="2")),broker_position_quantity="4")
        self.check(p,"BLOCK_ACTIVITY_UUID_CHAIN")

    def test_duplicate_broker_order_uuid_rejected(self):
        self.check(proof(orders=(order(),order()),activities=(activity(),),
                    broker_position_quantity="4"),"BLOCK_ORDER_PROVENANCE")

    def test_unmapped_activity_order_uuid_rejected(self):
        self.check(proof(orders=(order(),),activities=(activity(oid="no-such-order"),),
                    broker_position_quantity="4"),"BLOCK_ACTIVITY_UUID_CHAIN")

    def test_incomplete_fill_quantity_rejected_even_if_broker_pos_matches(self):
        self.check(proof(orders=(order(),),activities=(activity(qty="3"),),
                    broker_position_quantity="3"),"BLOCK_PARTIAL_OR_MISSING_FILLS")

    def test_overfilled_order_and_filled_status_mismatch_rejected(self):
        self.check(proof(orders=(order(filled="5"),)),
                   "BLOCK_ORDER_PROVENANCE")
        self.check(proof(orders=(order(filled="3"),)),
                   "BLOCK_ORDER_PROVENANCE")

    def test_partially_filled_then_canceled_reconciled_if_complete(self):
        p=proof(orders=(order(qty="4",filled="2",status="canceled"),),
                activities=(activity(qty="2"),),broker_position_quantity="2")
        self.check(p,"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")

    def test_unknown_or_done_for_day_status_is_not_final(self):
        for s in ("new","partially_filled","pending_cancel","done_for_day","unknown"):
            with self.subTest(s=s):
                self.check(proof(orders=(order(status=s),)),
                           "BLOCK_ORDER_PROVENANCE")

    def test_writer_prefix_disagrees_with_attested_registry(self):
        self.check(proof(orders=(order(cid="MBB-FAKE",writer="OTHER"),)),
                   "BLOCK_ORDER_PROVENANCE")
        self.check(proof(orders=(order(cid="FDR-BUY",writer="MBB"),)),
                   "BLOCK_ORDER_PROVENANCE")

    def test_unattested_writer_stays_blocked(self):
        self.check(proof(orders=(order(attested=False),)),
                   "BLOCK_ORDER_PROVENANCE")
        self.check(proof(writer_registry_complete=False),"BLOCK_INCOMPLETE_HISTORY")

    def test_missing_history_any_family_blocks(self):
        for f in ("broker_orders_complete","broker_activities_complete",
                  "broker_positions_complete"):
            with self.subTest(f=f):
                self.check(replace(proof(),**{f:False}),"BLOCK_INCOMPLETE_HISTORY")

    def test_fill_before_order_or_future_fill_is_causally_invalid(self):
        for when in (day9-timedelta(seconds=1),asof+timedelta(seconds=1)):
            self.check(proof(orders=(order(),),activities=(activity(when=when),),
                        broker_position_quantity="4"),"BLOCK_ACTIVITY_UUID_CHAIN")

    def test_order_earlier_than_flat_anchor_or_after_snapshot_blocks(self):
        for when in (anchor-timedelta(seconds=1),asof+timedelta(seconds=1)):
            self.check(proof(orders=(order(when=when),)),
                       "BLOCK_ORDER_PROVENANCE")

    def test_inconsistent_aggregate_position_blocks(self):
        self.check(proof(orders=(order(),),activities=(activity(),),
                         broker_position_quantity="3"),
                   "BLOCK_WRITER_NET_OR_POSITION_DRIFT")

    def test_writer_net_negative_flags_inter_strategy_sale(self):
        p=proof(orders=(order("s","MBB-20261109-S-AMD",side="sell",
                              when=day9),),activities=(activity(oid="s",side="sell"),),
                broker_position_quantity="0")
        self.check(p,"BLOCK_WRITER_OVERSELL_SEQUENCE")

    def test_nan_fractional_and_negative_quantities_block(self):
        for q in ("NaN","-1","0.5","Infinity"):
            with self.subTest(q=q):
                self.check(proof(orders=(order(qty=q),)),"BLOCK_ORDER_PROVENANCE")
                self.check(proof(broker_position_quantity=q),"BLOCK_INVALID_BROKER_POSITION")

    def test_writer_oversell_then_replenish_even_if_final_zero(self):
        sell=order("s","MBB-20261109-S-AMD",side="sell",when=day9)
        buy=order("b","MBB-20261109-B-AMD",side="buy",
                  when=day9+timedelta(minutes=2))
        p=proof(orders=(sell,buy),activities=(
            activity("s1","s",side="sell",when=day9+timedelta(seconds=2)),
            activity("b1","b",side="buy",when=day9+timedelta(minutes=2,seconds=2))),
            broker_position_quantity="0")
        self.check(p,"BLOCK_WRITER_OVERSELL_SEQUENCE")

    def test_same_timestamp_opposite_fills_not_ordered_by_input(self):
        buy=order("b","MBB-20261109-B-AMD",side="buy",when=day9)
        sell=order("s","MBB-20261109-S-AMD",side="sell",when=day9)
        t=day9+timedelta(seconds=10)
        p=proof(orders=(buy,sell),activities=(
            activity("b1","b",side="buy",when=t),
            activity("s1","s",side="sell",when=t)))
        self.check(p,"BLOCK_AMBIGUOUS_FILL_SEQUENCE")

    def test_out_of_input_order_valid_chronological_sequence(self):
        orders,fills=closed()
        p=proof(orders=orders,activities=tuple(reversed(fills)))
        self.check(p,"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")

    def test_zero_order_zero_fill_flat_proof_is_not_an_execution_signal(self):
        r=self.check(proof(),"FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY")
        self.assertEqual(r.normalized_activities,())
        self.assertNotIn("ELIGIBLE", r.status)
        self.assertNotIn("SELL", r.status)

if __name__=="__main__":
    unittest.main()