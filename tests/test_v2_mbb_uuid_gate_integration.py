"""Integration of independent UUID join with existing V2 admission model (offline)."""
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from research.v2_mbb_broker_uuid_chain import BrokerOrder, FillActivity, Proof, verify
from research.v2_mbb_session_ownership_gate import Activity, Evidence, classify

CT=ZoneInfo("America/Chicago")
NOW=datetime(2026,11,10,4,45,tzinfo=CT)
ANCHOR=datetime(2026,11,8,14,tzinfo=CT)
EARLIER=datetime(2026,11,9,7,30,tzinfo=CT)

def o(n,writer,side,qty,time):
    cid=("MBB-" if writer=="MBB" else "FDR-")+n
    return BrokerOrder(n,cid,"AMD",side,str(qty),str(qty),"filled",time,writer,True)

def f(n,side,qty,time):
    return FillActivity("activity-"+n,n,"AMD",side,str(qty),time+timedelta(seconds=1))

def combined(orders,fills,position,*,attempts=0,lease=False):
    chain=verify(Proof("AMD",NOW,ANCHOR,str(position),True,True,True,True,
                       tuple(orders),tuple(fills)))
    assert chain.status=="FILL_UUID_CHAIN_RECONCILED_RESEARCH_ONLY"
    normalized=tuple(Activity(*a) for a in chain.normalized_activities)
    e=Evidence("AMD",str(position),NOW,True,True,True,True,True,False,
               False,lease,normalized,attempts,"2026-11-09")
    return (classify(NOW,e,purpose="entry",holiday_unpaused=True).result,
            classify(NOW,e,purpose="flatten",holiday_unpaused=True).result)

class IntegrationTests(unittest.TestCase):
    def test_verified_old_filled_roundtrip_rearm(self):
        buys=o("b","MBB","buy",4,EARLIER)
        sells=o("s","MBB","sell",4,EARLIER+timedelta(minutes=3))
        self.assertEqual(combined((buys,sells),(
            f("b","buy",4,EARLIER),f("s","sell",4,EARLIER+timedelta(minutes=3))),0),
            ("NEW_SESSION_FIRST_ENTRY_ELIGIBLE_FOR_NORMAL_GATES",
             "VERIFIED_FLAT_NO_EXIT_ORDER"))

    def test_same_session_attempt_blocks_even_when_all_old_fills_closed(self):
        self.assertEqual(combined((),(),0,attempts=1)[0],
                         "SAME_SESSION_REENTRY_REQUIRES_BROKER_PROOF")

    def test_authoritative_order_uuids_still_do_not_substitute_for_lease(self):
        self.assertEqual(combined((o("b","MBB","buy",4,EARLIER),),
                         (f("b","buy",4,EARLIER),),4),
                         ("BLOCK_AND_ESCALATE_OWNERSHIP",
                          "BLOCK_AND_ESCALATE_OWNERSHIP"))

    def test_independent_exclusive_lease_required_for_exit_classification(self):
        self.assertEqual(combined((o("b","MBB","buy",4,EARLIER),),
                         (f("b","buy",4,EARLIER),),4,lease=True)[1],
                         "VERIFIED_MBB_EXIT_OBLIGATION")

    def test_fdr_replacement_after_stale_mbb_roundtrip_blocks_mbb_exit(self):
        orders=(o("b","MBB","buy",4,EARLIER),
                o("s","MBB","sell",4,EARLIER+timedelta(minutes=3)),
                o("f","OTHER","buy",2,EARLIER+timedelta(minutes=5)))
        fills=(f("b","buy",4,EARLIER),
               f("s","sell",4,EARLIER+timedelta(minutes=3)),
               f("f","buy",2,EARLIER+timedelta(minutes=5)))
        self.assertEqual(combined(orders,fills,2,lease=True)[1],
                         "BLOCK_AND_ESCALATE_OWNERSHIP")
if __name__=="__main__":unittest.main()