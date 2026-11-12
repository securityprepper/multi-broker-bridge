import unittest
from datetime import datetime,timezone
from decimal import Decimal
from urllib.parse import parse_qs,urlsplit
from recommendation_paper_bridge import reconcile

OID="11111111-1111-1111-1111-111111111111"
TP="22222222-2222-2222-2222-222222222222"
STOP="33333333-3333-3333-3333-333333333333"
CID="TEST-PAPER-CLIENT"

ROW={"recommendation_id":"TO-20261110-AMD-T1-DEMO","broker_order_id":OID,
     "client_order_id":CID,"symbol":"AMD","limit_price":Decimal("100.10"),
     "profit_target":Decimal("105"),"stop_loss":Decimal("98"),
     "intended_qty":4}
PARENT={"id":OID,"client_order_id":CID,"symbol":"AMD","side":"buy",
        "order_class":"bracket","type":"limit","limit_price":"100.10",
        "filled_qty":"4",
        "legs":[
            {"id":TP,"symbol":"AMD","side":"sell","type":"limit","limit_price":"105",
             "status":"filled","qty":"4","filled_qty":"4"},
            {"id":STOP,"symbol":"AMD","side":"sell","type":"stop","stop_price":"98",
             "status":"canceled","qty":"4","filled_qty":"0"}]}
def activity(id,oid,side,qty,price,t):
    return {"id":id,"order_id":oid,"activity_type":"FILL","symbol":"AMD",
            "side":side,"qty":qty,"price":price,"transaction_time":t}
FILLS={
 OID:[activity("fill-a",OID,"buy","2","100.00","2026-11-10T16:01:03Z"),
      activity("fill-b",OID,"buy","2","100.05","2026-11-10T16:01:10Z")],
 TP:[activity("fill-c",TP,"sell","4","105.00","2026-11-10T17:20:00Z")],
 STOP:[]}

class ActualFillReadback(unittest.TestCase):
    def http(self,method,path,body=None,data=False):
        if method!="GET":raise AssertionError("read-only only")
        if path.startswith("/v2/orders/"):
            return dict(PARENT)
        if "/account/activities?" in path:
            key=parse_qs(urlsplit(path).query)["order_id"][0]
            return [dict(x) for x in FILLS.get(key,[])]
        raise AssertionError("unrecognized GET "+path)
    def test_completed_4_shares_two_entry_fill_uuids_only(self):
        result=reconcile.reconcile_one(dict(ROW),httpfn=self.http)
        self.assertEqual(result["state"],"CLOSED_NEEDS_FEE_RECON")
        self.assertEqual(result["gross_pnl"],"19.90")
        self.assertIsNone(result["net_pnl"])
        entry=result["verified_entry_fill"]
        self.assertEqual(entry["first_fill_activity_id"],"fill-a")
        self.assertEqual(entry["filled_average_price"],"100.025")
        self.assertEqual(entry["filled_quantity"],"4")
        self.assertEqual(len(entry["fill_activity_ids"]),2)
        self.assertTrue(entry["fill_not_order_acceptance"])
    def test_duplicate_fill_uuid_rejected(self):
        duplicate={k:list(v) for k,v in FILLS.items()}
        duplicate[OID]=FILLS[OID]+[dict(FILLS[OID][0])]
        def http(*args,**kwargs):
            path=args[1]
            if "/account/activities?" in path:
                key=parse_qs(urlsplit(path).query)["order_id"][0]
                return [dict(x) for x in duplicate.get(key,[])]
            return self.http(*args,**kwargs)
        with self.assertRaises(reconcile.Unsafe):
            reconcile.reconcile_one(dict(ROW),httpfn=http)

if __name__=="__main__":unittest.main()
