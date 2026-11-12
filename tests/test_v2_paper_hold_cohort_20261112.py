"""Offline checks for research-only broker-FILL cohort accounting."""
import importlib.util
import unittest
from pathlib import Path

mod_path=Path(__file__).resolve().parents[1]/"research"/"v2_paper_hold_cohort_20261112.py"
spec=importlib.util.spec_from_file_location("cohorts", mod_path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def trade(n, start="2026-11-09T15:00:00Z", end="2026-11-09T15:02:00Z", entry=100, exit_=99,
          source="MBB", qty=2):
    return {"source":source,"day":"2026-11-09","symbol":"TST",
            "entry_at":start,"exit_at":end,"entry":entry,"exit":exit_,
            "qty":qty,"entry_order_id":f"buy-{n}","exit_order_id":f"sell-{n}"}

class CohortTests(unittest.TestCase):
    def test_two_minute_inclusive(self):
        self.assertEqual(m.cohort(trade(1))["hold_bucket"],"<=2m")
    def test_five_minute_inclusive(self):
        self.assertEqual(m.cohort(trade(1,end="2026-11-09T15:05:00Z"))["hold_bucket"],">2-5m")
    def test_ten_minute_inclusive(self):
        self.assertEqual(m.cohort(trade(1,end="2026-11-09T15:10:00Z"))["hold_bucket"],">5-10m")
    def test_thirty_minute_inclusive(self):
        self.assertEqual(m.cohort(trade(1,end="2026-11-09T15:30:00Z"))["hold_bucket"],">10-30m")
    def test_more_than_thirty(self):
        self.assertEqual(m.cohort(trade(1,end="2026-11-09T15:30:01Z"))["hold_bucket"],">30m")
    def test_fill_gross_calculation(self):
        self.assertEqual(m.analyze([trade(1)])["all_completed"]["broker_fill_gross_usd"],"-2.00")
    def test_source_separation(self):
        out=m.analyze([trade(1),trade(2,source="FDR",exit_=101)])
        self.assertEqual(out["by_source"]["MBB"]["losing"],1)
        self.assertEqual(out["by_source"]["FDR"]["winning"],1)
    def test_duplicate_entry_rejected(self):
        x=trade(1);y=trade(2);y["entry_order_id"]=x["entry_order_id"]
        with self.assertRaises(ValueError):m.analyze([x,y])
    def test_duplicate_exit_rejected(self):
        x=trade(1);y=trade(2);y["exit_order_id"]=x["exit_order_id"]
        with self.assertRaises(ValueError):m.analyze([x,y])
    def test_same_uuid_buy_and_sell_rejected(self):
        x=trade(1);x["exit_order_id"]=x["entry_order_id"]
        with self.assertRaises(ValueError):m.analyze([x])
    def test_no_timezone_rejected(self):
        x=trade(1);x["entry_at"]="2026-11-09T09:00:00"
        with self.assertRaises(ValueError):m.analyze([x])
    def test_wrong_chicago_day_rejected(self):
        x=trade(1);x["day"]="2026-11-10"
        with self.assertRaises(ValueError):m.analyze([x])
    def test_negative_or_zero_price_rejected(self):
        with self.assertRaises(ValueError):m.analyze([trade(1,entry=0)])
    def test_exit_before_entry_rejected(self):
        with self.assertRaises(ValueError):m.analyze([trade(1,end="2026-11-09T14:59:00Z")])
    def test_no_order_submission(self):
        self.assertEqual(m.analyze([trade(1)])["broker_orders_submitted"],0)
    def test_unknown_exit_reason_not_guessed(self):
        self.assertEqual(m.analyze([trade(1)])["exit_trigger_for_ordinary_mbb"],"UNKNOWN")

if __name__=="__main__":unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]