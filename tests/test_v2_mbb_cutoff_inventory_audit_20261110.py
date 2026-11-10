from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"research"))
import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from v2_mbb_cutoff_inventory_audit_20261110 import broker_audit, journal_audit, stamp
CHI=ZoneInfo("America/Chicago")
DAY="2026-11-10"
END=stamp("2026-11-10T13:30:00-06:00")
def order(id,side,qty,price,at,filled=None,status="filled",symbol="AAA"):
    return {"client_order_id":id,"side":side,"symbol":symbol,"filled_qty":str(qty),
            "filled_avg_price":str(price),"submitted_at":at,
            "filled_at":filled or at,"status":status}
def snap(orders):
    return {"broker_verified":True,"recent_orders_complete":True,
            "asof_utc":"2026-11-10T19:28:00Z","recent_orders":orders,
            "positions":[],"open_orders_count":0}
class CutoffAudit(unittest.TestCase):
    def test_win_loss_fifo(self):
        os=[order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T12:01:00-06:00"),
            order("MBB-20261110-S-AAA","sell",4,101,"2026-11-10T12:03:00-06:00")]
        d=broker_audit(snap(os),DAY,END)
        self.assertEqual(d["gross_realized_paper_usd"],"4.00")
        self.assertEqual(d["winning_lots"],1)
        self.assertEqual(d["remaining_mbb_fill_lots"],{})
    def test_after_cutoff_flagged(self):
        o=order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T13:15:00-06:00")
        self.assertEqual(broker_audit(snap([o]),DAY,END)["buy_submissions_after_1315_CT"],["AAA"])
    def test_filled_after_cutoff_not_late_submission(self):
        o=order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T13:14:00-06:00",filled="2026-11-10T13:17:00-06:00")
        self.assertFalse(broker_audit(snap([o]),DAY,END)["buy_submissions_after_1315_CT"])
    def test_ignore_FDR_and_previous_date(self):
        os=[order("FDR-ABC","buy",4,100,"2026-11-10T13:20:00-06:00"),
            order("MBB-20261109-B-AAA","buy",4,100,"2026-11-09T13:20:00-06:00")]
        self.assertEqual(broker_audit(snap(os),DAY,END)["orders_in_session"],0)
    def test_fail_closed_incomplete(self):
        d=snap([]);d["recent_orders_complete"]=False
        with self.assertRaises(ValueError): broker_audit(d,DAY,END)
    def test_no_future_snapshot(self):
        d=snap([]);d["asof_utc"]="2026-11-10T20:00:00Z"
        with self.assertRaises(ValueError): broker_audit(d,DAY,END)
    def test_duplicate_order_id(self):
        o=order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T12:00:00-06:00")
        with self.assertRaises(ValueError): broker_audit(snap([o,o]),DAY,END)
    def test_unmatched_sell_not_zero_pnl_proof(self):
        o=order("MBB-20261110-S-AAA","sell",4,100,"2026-11-10T12:00:00-06:00")
        self.assertEqual(broker_audit(snap([o]),DAY,END)["unmatched_sells"],["AAA"])
    def test_aggregate_shares_not_ownership(self):
        o=order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T12:00:00-06:00")
        d=snap([o]);d["positions"]=[{"symbol":"AAA","qty":"4"}]
        self.assertFalse(broker_audit(d,DAY,END)["strategy_ownership_proven"])
    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError): stamp("2026-11-10T13:15:00")
    def test_journal_cutoff_and_holiday_flag_distinct(self):
        def line(tm,reason=None):
            d={"status":"SCAN_COMPLETE","candidate_count":1,"buy_watch_symbols":["AAA"],
               "skipped_buy_reasons":[{"reason":reason}] if reason else [],
               "gate_allows_new_entries":True,"orders":[]}
            t=stamp(tm)
            return json.dumps({"__REALTIME_TIMESTAMP":str(int(t.timestamp()*1e6)),"MESSAGE":json.dumps(d)})
        rows=[line("2026-11-10T13:14:59-06:00","NO_FRESH_BID_ASK"),
              line("2026-11-10T13:15:00-06:00","AFTER_ENTRY_CUTOFF")]
        d=journal_audit(rows,DAY,stamp("2026-11-10T13:00:00-06:00"),END)
        self.assertEqual(d["before_entry_cutoff"]["scans"],1)
        self.assertEqual(d["after_entry_cutoff"]["scans"],1)
        self.assertEqual(d["after_entry_cutoff"]["holiday_gate_true_scans"],1)
    def test_closed_order_without_fill_ignored(self):
        o=order("MBB-20261110-B-AAA","buy",4,100,"2026-11-10T12:00:00-06:00",status="canceled")
        self.assertEqual(broker_audit(snap([o]),DAY,END)["filled_buys"],0)
if __name__=="__main__":
    unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]
