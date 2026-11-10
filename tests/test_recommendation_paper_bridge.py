import os
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import patch
from recommendation_paper_bridge.bridge import (
    validate_recommendation, safe_client_id, bracket_payload,
    Unsafe, BrokerRejected, SubmissionUnknown, entry_window, preflight,
    require_commissioned,process_once
)

NOW=datetime(2026,11,10,16,0,tzinfo=timezone.utc) # 10am Chicago
def rec(**updates):
    r={"recommendation_id":"TO-20261110-AMD-T1-RUN42",
       "issued_at_utc":"2026-11-10T15:59:50Z",
       "quote_at_utc":"2026-11-10T15:59:35Z",
       "symbol":"AMD","action":"BUY NOW",
       "quote_last":"100.00","quote_bid":"99.98","quote_ask":"100.05",
       "limit":"100.10","profit_target":"101.60","stop_loss":"98.50",
       "rationale":"Official company guidance upgrade and non-extended pullback",
       "source_task":"Task - Trading Opportunities One","source_run_id":"run.42"}
    r.update(updates)
    return r
class TestValidation(unittest.TestCase):
 def test_valid(self):
    x=validate_recommendation(rec(),NOW)
    self.assertEqual(x["qty"],19)
    self.assertEqual(x["status"],"PENDING")
 def test_idempotent(self):
    self.assertEqual(safe_client_id(rec()["recommendation_id"]),safe_client_id(rec()["recommendation_id"]))
 def test_quote_stale(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(quote_at_utc="2026-11-10T15:30:00Z"),NOW)
 def test_recommendation_stale(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(issued_at_utc="2026-11-10T15:30:00Z"),NOW)
 def test_no_chase(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(limit="100.00"),NOW)
 def test_stop_above_limit(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(stop_loss="100.90"),NOW)
 def test_bad_source(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(source_task="Research"),NOW)
 def test_mismatched_symbol(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(symbol="NVDA"),NOW)
 def test_float_input(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(quote_last=100.0),NOW)
 def test_crossover_quote(self):
    with self.assertRaises(Unsafe):validate_recommendation(rec(quote_bid="100.30"),NOW)
 def test_after_cutoff_record_without_order(self):
    t=datetime(2026,11,10,20,0,tzinfo=timezone.utc) # 14:00 CT
    r=rec(issued_at_utc="2026-11-10T19:59:50Z",quote_at_utc="2026-11-10T19:59:30Z")
    self.assertEqual(validate_recommendation(r,t)["status"],"NOT_PLACED_CUTOFF")
 def test_one_bracket_with_exact_levels(self):
    x=validate_recommendation(rec(),NOW)
    row={"symbol":x["symbol"],"limit_price":x["limit"],"profit_target":x["target"],
         "stop_loss":x["stop"],"intended_qty":x["qty"],"client_order_id":x["client_id"]}
    b=bracket_payload(row)
    self.assertEqual(b["type"],"limit")
    self.assertEqual(b["order_class"],"bracket")
    self.assertEqual(b["take_profit"]["limit_price"],"101.60")
    self.assertEqual(b["stop_loss"]["stop_price"],"98.50")
    self.assertIs(b["extended_hours"],False)
 def test_window(self):
    self.assertTrue(entry_window(NOW))
    self.assertFalse(entry_window(datetime(2026,11,10,19,16,tzinfo=timezone.utc)))
    self.assertFalse(entry_window(datetime(2026,11,10,13,0,tzinfo=timezone.utc)))
 def test_commissioning_gate(self):
    for k in ("PAPER_BRIDGE_COMMISSIONED","PAPER_BRIDGE_SHARED_LOCK_ATTESTED",
              "PAPER_BRIDGE_EXIT_GUARD_ATTESTED","PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT"):
        with patch.dict(os.environ,{k:""},clear=False):
            with self.assertRaises(Unsafe):require_commissioned()
 def test_no_network_when_not_commissioned(self):
    with patch.dict(os.environ,{"PAPER_BRIDGE_COMMISSIONED":"0"}):
        with self.assertRaises(Unsafe):process_once(NOW,connect=lambda *_:self.fail("DB touched"),
          httpfn=lambda *_a,**_k:self.fail("BROKER touched"))
if __name__=="__main__":unittest.main()
