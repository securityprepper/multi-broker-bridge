"""Tests for the broker-order-ID-safe, conservative PAPER target reachability study."""
import unittest
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from v2_rth_target_reachability_20261111 import assess,aggregate,rth_trade
CT=ZoneInfo("America/Chicago")
ENTRY="2026-11-11T14:30:05+00:00"
EXIT="2026-11-11T14:32:05+00:00"
def lot(source="MBB",entry=ENTRY):
    return {"source":source,"day":"2026-11-11","symbol":"AMD",
            "entry_at":entry,"exit_at":EXIT,"entry":100.0,"exit":99.9,
            "qty":10,"entry_order_id":"MBB_BUY_A","exit_order_id":"MBB_SELL_A"}
def bar(hhmm,lo,hi,cl):
    ts=datetime.fromisoformat("2026-11-11T"+hhmm+":00").replace(tzinfo=CT)
    return {"t":ts.astimezone(timezone.utc).isoformat(),"l":lo,"h":hi,"c":cl}
class TargetTests(unittest.TestCase):
    def test_same_minute_stop_first_not_target_fill(self):
        r=assess(lot(),[bar("08:31",98.5,102,98.9)],(0.01,))[0.01]
        self.assertTrue(r["high_touch"])
        self.assertFalse(r["first_high_before_loss"])
        self.assertFalse(r["first_close_before_loss"])
    def test_strict_after_entry_excludes_entry_candle(self):
        r=assess(lot(),[bar("08:30",99,110,109),bar("08:31",99.7,100.5,100.0)],(0.01,))[0.01]
        self.assertFalse(r["high_touch"])
    def test_full_completed_after_entry_can_precede_loss(self):
        r=assess(lot(),[bar("08:31",99.9,101.5,101.1),bar("08:32",98.5,100,98.9)],(0.01,))[0.01]
        self.assertTrue(r["first_high_before_loss"])
        self.assertTrue(r["first_close_before_loss"])
    def test_missing_before_target_not_counted_first(self):
        r=assess(lot(),[bar("08:31",99,100.2,100),bar("08:33",99,103,102)],(0.01,))[0.01]
        self.assertTrue(r["high_touch"])
        self.assertFalse(r["first_high_before_loss"])
        self.assertTrue(r["missing_path"])
    def test_no_premarket_or_fdr_contamination(self):
        self.assertFalse(rth_trade(lot(source="FDR")))
        self.assertFalse(rth_trade(lot(entry="2026-11-11T13:29:00+00:00")))
        self.assertTrue(rth_trade(lot()))
    def test_reject_duplicate_broker_order_ids(self):
        x=lot()
        source={"research_only":True,"broker_orders_submitted":0,"trades":[x,x],"bars":{}}
        with self.assertRaises(ValueError):aggregate(source)
    def test_one_lot_without_bars_not_claimed_success(self):
        source={"research_only":True,"broker_orders_submitted":0,"trades":[lot()],"bars":{}}
        out=aggregate(source)
        self.assertEqual(out["trades"],1)
        self.assertEqual(out["distinct_sessions"],1)
        self.assertTrue(all(x["high_touch_upper_bound"]==0 for x in out["targets"]))
        self.assertTrue(all(x["missing_or_censored_first_event_paths"]==1 for x in out["targets"]))
    def test_reject_order_capability_input(self):
        source={"research_only":True,"broker_orders_submitted":1,"trades":[],"bars":{}}
        with self.assertRaises(ValueError):aggregate(source)
if __name__=="__main__":unittest.main()