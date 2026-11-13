import unittest
from v2_alpaca_paper_roundtrip_audit_20261113 import audit_roundtrips

def order(oid, side, source="MBB", sym="AMD", typ="limit"):
    return {"id": oid, "client_order_id": source+"-"+oid,
            "side": side, "symbol": sym, "type": typ,
            "order_class": "", "status":"filled"}

def fill(fid, oid, qty, price, clock, sym="AMD"):
    return {"id": fid, "order_id": oid, "qty":str(qty),
            "price":str(price), "symbol":sym,
            "transaction_time":"2026-11-09T"+clock+"Z"}

class PaperRoundtripAudit(unittest.TestCase):
    def test_partial_fills_are_one_roundtrip(self):
        os={"b":order("b","buy"),"s":order("s","sell")}
        fs=[fill("1","b",2,100,"14:00:00"),fill("2","b",2,101,"14:00:01"),
            fill("3","s",4,102,"14:04:00")]
        r=audit_roundtrips(fs,os)
        self.assertEqual(r["complete_entry_orders"],1)
        self.assertEqual(r["unique_fill_activities"],3)
        self.assertEqual(r["by_source"]["MBB"]["gross_usd"],"6.00")
        self.assertEqual(r["by_source"]["MBB"]["rapid_at_most_min"]["5"],1)

    def test_same_symbol_two_sources_do_not_double_count(self):
        os={"fb":order("fb","buy","FDR"),"fs":order("fs","sell","FDR"),
            "mb":order("mb","buy"),"ms":order("ms","sell")}
        fs=[fill("1","fb",2,100,"13:00:00"),fill("2","fs",2,98,"13:24:00"),
            fill("3","mb",2,99,"14:00:00"),fill("4","ms",2,101,"14:02:00")]
        r=audit_roundtrips(fs,os)
        self.assertEqual(r["complete_entry_orders"],2)
        self.assertEqual(r["by_source"]["FDR"]["gross_usd"],"-4.00")
        self.assertEqual(r["by_source"]["MBB"]["gross_usd"],"4.00")
        self.assertFalse(r["cross_source_segments"])

    def test_duplicate_id_deduplicated(self):
        os={"b":order("b","buy"),"s":order("s","sell")}
        fs=[fill("1","b",1,100,"14:00:00"),fill("1","b",1,100,"14:00:00"),
            fill("2","s",1,101,"14:05:00")]
        r=audit_roundtrips(fs,os)
        self.assertEqual(r["complete_entry_orders"],1)
        self.assertEqual(r["unresolved"]["repeated_fill_id_deduplicated"],1)

    def test_conflicting_duplicate_id_is_failure(self):
        os={"b":order("b","buy"),"s":order("s","sell")}
        fs=[fill("1","b",1,100,"14:00:00"),fill("1","b",1,101,"14:00:00")]
        with self.assertRaises(ValueError):audit_roundtrips(fs,os)

    def test_unmatched_exit_not_counted_as_pnl(self):
        os={"s":order("s","sell")}
        r=audit_roundtrips([fill("1","s",1,100,"14:00:00")],os)
        self.assertEqual(r["complete_entry_orders"],0)
        self.assertEqual(r["unmatched_sell_qty"]["AMD"],"1")

    def test_open_entry_does_not_count_closed(self):
        os={"b":order("b","buy")}
        r=audit_roundtrips([fill("1","b",3,100,"14:00:00")],os)
        self.assertEqual(r["complete_entry_orders"],0)
        self.assertEqual(r["incomplete_entry_orders"],1)

    def test_broker_acceptance_is_not_fill(self):
        os={"b":order("b","buy"),"s":order("s","sell")}
        os["s"]["status"]="pending_new"
        r=audit_roundtrips([fill("1","b",1,100,"14:00:00")],os)
        self.assertEqual(r["complete_entry_orders"],0)

    def test_market_exit_is_not_native_bracket(self):
        os={"b":order("b","buy"),"s":order("s","sell",typ="market")}
        r=audit_roundtrips([fill("1","b",1,100,"14:00:00"),
             fill("2","s",1,99,"19:40:00")],os)
        self.assertEqual(r["complete_entry_orders"],1)
        self.assertEqual(r["filled_order_type_classes"]["('', 'market')"],1)
        self.assertEqual(r["market_exit_details"][0]["symbol"],"AMD")

if __name__=="__main__":unittest.main()
