import unittest
from datetime import datetime
from v2_order_source_collision_audit import analyze,family

def order(cid,symbol,side,at,qty=1):
    return {"client_order_id":cid,"symbol":symbol,"side":side,
            "filled_at":"2026-11-09T"+at+"Z","filled_qty":str(qty),
            "status":"filled","strategy":"test"}
def inv(rows):
    return {"paper_only":True,"broker_verified":True,"recent_orders_complete":True,
            "asof_utc":"2026-11-09T20:00:00Z","recent_orders":rows}
class CollisionAudit(unittest.TestCase):
    def test_family_tag(self):
        self.assertEqual(family("FDR-x"),"FDR")
        self.assertEqual(family("MBB-y"),"MBB")
        self.assertEqual(family(""),"UNATTRIBUTED")
    def test_distinct_orders_pair_without_overlap(self):
        rows=[order("MBB-1","MU","buy","14:00:00"),order("MBB-2","MU","sell","14:01:00"),
              order("FDR-1","MU","buy","14:02:00"),order("FDR-2","MU","sell","14:03:00")]
        r=analyze(inv(rows))
        self.assertEqual(r["filled_orders_total"],4)
        self.assertEqual(r["simultaneously_open_both_strategies"],[])
        self.assertEqual(r["minutes_between_nearest_exposure"]["MU"],1.)
    def test_overlap_flagged(self):
        rows=[order("MBB-1","MU","buy","14:00:00"),order("MBB-2","MU","sell","14:03:00"),
              order("FDR-1","MU","buy","14:02:00"),order("FDR-2","MU","sell","14:04:00")]
        self.assertEqual(analyze(inv(rows))["simultaneously_open_both_strategies"],["MU"])
    def test_duplicate_cid_visible(self):
        rows=[order("MBB-1","MU","buy","14:00:00"),order("MBB-1","MU","sell","14:01:00")]
        self.assertEqual(analyze(inv(rows))["duplicate_client_order_ids"],1)
    def test_no_live_inventory(self):
        d=inv([]);d["paper_only"]=False
        with self.assertRaises(ValueError):analyze(d)
    def test_incomplete_fails(self):
        d=inv([]);d["recent_orders_complete"]=False
        with self.assertRaises(ValueError):analyze(d)
if __name__=="__main__":unittest.main()
