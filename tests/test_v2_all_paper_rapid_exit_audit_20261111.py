import sys,unittest
from datetime import datetime,timezone,timedelta
from decimal import Decimal
sys.path.insert(0,"/tmp")
from v2_all_paper_rapid_exit_audit_20261111 import audit,session_day,source_for

def order(cid,sym,side,minute,qty,price,status="filled"):
 return {"client_order_id":cid,"symbol":sym,"side":side,"filled_at":"2026-11-11T"+minute+":00Z",
         "filled_qty":str(qty),"filled_avg_price":str(price),"status":status}

def envelope(orders):
 return {"paper_only":True,"broker_verified":True,"recent_orders_complete":True,
         "asof_utc":"2026-11-11T23:00:00Z","recent_orders_since_utc":"2026-11-08T23:00:00Z",
         "recent_orders":orders}

class ResearchEvidenceTests(unittest.TestCase):
 def test_mbb_and_fdr_same_symbol_do_not_cross_match(self):
  x=envelope([order("MBB-a","AMD","buy","13:00",4,100),
              order("FDR-a","AMD","buy","13:01",4,120),
              order("MBB-b","AMD","sell","13:02",4,99),
              order("FDR-b","AMD","sell","13:03",4,110)])
  y=audit(x)
  self.assertEqual(y["closed_order_level_lots"],2)
  self.assertEqual(Decimal(y["gross_pnl_usd"]),Decimal("-44"))
  self.assertEqual(y["cohorts"]["2026-11-11|MBB"]["gross_pnl_usd"],"-4")
  self.assertEqual(y["cohorts"]["2026-11-11|FDR"]["gross_pnl_usd"],"-40")
 def test_other_unlinked_flow_still_included(self):
  y=audit(envelope([order("OTHER-1","CAT","buy","14:00",1,100),
                    order("OTHER-2","CAT","sell","14:04",1,101)]))
  self.assertEqual(y["closed_order_level_lots"],1)
  self.assertIn("2026-11-11|OTHER_UNLINKED",y["cohorts"])
 def test_duplicate_client_order_not_double_counted(self):
  x=order("MBB-1","AMD","buy","13:00",4,100)
  with self.assertRaisesRegex(ValueError,"duplicate client"):
   audit(envelope([x,x]))
 def test_not_filled_is_not_a_trade(self):
  y=audit(envelope([order("MBB-1","AMD","buy","13:00",4,100,status="canceled")]))
  self.assertEqual(y["actual_filled_orders"],0)
  self.assertEqual(y["nonfilled_orders"],1)
 def test_partial_lot_order_level_qty_balance(self):
  y=audit(envelope([order("MBB-1","AMD","buy","13:00",5,100),
                    order("MBB-2","AMD","sell","13:02",2,101),
                    order("MBB-3","AMD","sell","13:05",3,102)]))
  self.assertEqual(y["closed_order_level_lots"],2)
  self.assertEqual(Decimal(y["gross_pnl_usd"]),Decimal("8"))
  self.assertEqual(y["unmatched"],[])
 def test_unmatched_exit_never_creates_imaginary_entry(self):
  y=audit(envelope([order("MBB-sell","AMD","sell","13:00",1,99)]))
  self.assertEqual(y["closed_order_level_lots"],0)
  self.assertEqual(y["unmatched"][0]["kind"],"SELL_WITHOUT_SAME_SOURCE_BUY")
 def test_open_unpaired_rejected_from_complete_roundtrip_denominator(self):
  y=audit(envelope([order("MBB-b","AMD","buy","13:00",1,100)]))
  self.assertEqual(y["closed_order_level_lots"],0)
  self.assertEqual(y["unmatched"][0]["kind"],"OPEN_OR_UNPAIRED_BUY_ORDER")
 def test_unverified_broker_scope_fails_closed(self):
  x=envelope([]);x["recent_orders_complete"]=False
  with self.assertRaisesRegex(ValueError,"coverage"):audit(x)
 def test_source_timestamps_require_timezone(self):
  x=envelope([order("MBB-b","AMD","buy","13:00",1,100)])
  x["recent_orders"][0]["filled_at"]="2026-11-11T13:00:00"
  with self.assertRaisesRegex(ValueError,"naive"):audit(x)
 def test_session_day_handles_evening_for_next_session(self):
  t=datetime(2026,11,12,2,5,tzinfo=timezone.utc)
  self.assertEqual(session_day(t),"2026-11-12")
 def test_current_derived_cumulative_thresholds_are_inclusive(self):
  y=audit(envelope([order("MBB-b","AMD","buy","13:00",1,100),
                    order("MBB-s","AMD","sell","13:02",1,99)]))
  self.assertEqual(y["cohorts"]["2026-11-11|MBB"]["cumulative_hold_minutes"]["2"],1)
 def test_broker_order_average_not_claimed_to_be_fill_activity_timing(self):
  y=audit(envelope([]))
  self.assertTrue(y["no_fill_activity_timing_or_spread_proof"])
  self.assertFalse(y["net_after_fees_established"])
  self.assertEqual(y["exit_reasons_verified"],0)

if __name__=="__main__":unittest.main()
