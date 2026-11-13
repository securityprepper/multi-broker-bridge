"""No-broker unit tests for fixed RTH P/L and trail-order comparisons."""
from __future__ import annotations
import json
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from research.v2_paper_rth_trail_shadow_20261112 import (
    Rule,RULES,loc,ceil_minute,rth_entry,full_path,decide,
    quote_at_flat,simulate,evaluate
)
CT=ZoneInfo("America/Chicago")
def bar(minute,open_=100,high=100.1,low=99.9,close=100):
    t=datetime(2026,11,12,13,minute,tzinfo=CT)
    return {"t":t.isoformat(),"o":open_,"h":high,"l":low,"c":close,"v":100}
def trade(when="13:34:20",source="MBB"):
    a=datetime.fromisoformat("2026-11-12T"+when+"-06:00")
    b=a+timedelta(minutes=1)
    return {"source":source,"symbol":"FAKE","day":"2026-11-12",
        "entry_at":a.isoformat(),"exit_at":b.isoformat(),
        "entry":100,"exit":99.8,"qty":2,
        "entry_order_id":"MBB-FAKE-B","exit_order_id":"MBB-FAKE-S"}
class TrailResearchTests(unittest.TestCase):
    def test_1pct_profit_preempts_profit_activated_trail(self):
        b={"h":101.4,"l":100.8,"c":101.01}
        self.assertEqual(decide(100,b,101.4,Rule("x",.01,.01,.015)),"PROFIT_CLOSE")
    def test_tiny_peak_reversal_activates_current_not_larger_guard(self):
        b={"h":100.61,"l":100.0,"c":100.0}
        self.assertEqual(decide(100,b,100.61,Rule("current",.01,.005,.005)),"PEAK_REVERSAL")
        self.assertIsNone(decide(100,b,100.61,Rule("alt",.01,.01,.01)))
    def test_hard_loss_preempts_trail_no_profit(self):
        b={"h":100,"l":98.8,"c":98.99}
        self.assertEqual(decide(100,b,101.9,Rule("x",None,.01,.015)),"LOSS_CLOSE")
    def test_1pct_profit_preempts_current_trailing_reversal(self):
        b={"h":102,"l":100.9,"c":101.02}
        self.assertEqual(decide(100,b,102,Rule("x",.01,.005,.005)),"PROFIT_CLOSE")
    def test_meaningful_trail_after_gain_with_no_immediate_profit(self):
        b={"h":101.2,"l":100.0,"c":100.03}
        self.assertEqual(decide(100,b,101.2,Rule("x",None,.01,.01)),"PEAK_REVERSAL")
    def test_missing_completed_bar_censors_entire_comparison(self):
        r=trade()
        x=[bar(35),bar(36),bar(38),bar(39)]
        path,status=full_path(r,x)
        self.assertIsNone(path);self.assertEqual(status,"MISSING_COMPLETE_1M_PATH")
    def test_causal_next_minute_open_not_same_bar_high(self):
        r=trade()
        p=[(loc(x["t"]),x) for x in [bar(35,100,100.2,98.8,98.9),bar(36,98.5,99,98,98.8),bar(37),bar(38),bar(39)]]
        z=simulate(r,p,100,Rule("stop",.01,.005,.005))
        self.assertEqual(z["reason"],"LOSS_CLOSE")
        self.assertEqual(z["price_basis"],"NEXT_MINUTE_OPEN_MARK_NOT_EXECUTABLE")
        self.assertAlmostEqual(z["gross_proxy"],-3)
        self.assertEqual(z["minutes"],1.667)
    def test_no_extra_high_low_after_exit_in_excursions(self):
        r=trade()
        p=[(loc(x["t"]),x) for x in [bar(35,100,100.2,98.8,98.9),bar(36,98.5,120,90,110),bar(37),bar(38),bar(39)]]
        z=simulate(r,p,100,Rule("stop",.01,.005,.005))
        self.assertAlmostEqual(z["mfe_pct"],.2)
        self.assertAlmostEqual(z["mae_pct"],-1.2)
    def test_flat_quote_must_be_trusted_and_sized(self):
        self.assertIsNone(quote_at_flat({"status":"STALE_OR_UNSIZEABLE","bid":100,"ask":101,"bid_size":10},2))
        self.assertIsNone(quote_at_flat({"status":"FRESH_TIGHT_INDICATIVE_QUOTE","bid":100,"ask":101,"bid_size":1},2))
        self.assertEqual(quote_at_flat({"status":"FRESH_TIGHT_INDICATIVE_QUOTE","bid":100,"ask":100.1,"bid_size":5},2),100)
    def test_exclude_premarket_and_fdr(self):
        self.assertTrue(rth_entry(trade("10:34:20")))
        self.assertFalse(rth_entry(trade("07:06:20")))
        self.assertFalse(rth_entry(trade("13:34:20")))
        self.assertFalse(rth_entry(trade(source="FDR")))
    def test_no_privileged_broker_order_operations(self):
        from research import v2_paper_rth_trail_shadow_20261112 as m
        src=Path(m.__file__).read_text()
        for prohibited in ("urllib.request","paper_api(", "requests.post(", "broker_api(", "POST /v2/orders"):
            self.assertNotIn(prohibited,src)
    def test_duplicate_round_trip_is_rejected(self):
        tr=trade()
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"in.json"; q=Path(td)/"quotes.json"
            obj={"research_only":True,"broker_orders_submitted":0,"scope":"SINGLE",
                 "trades":[tr,tr],"bars":{"2026-11-12|FAKE":[bar(x) for x in range(35,40)]}}
            f.write_text(json.dumps(obj));q.write_text(json.dumps({"quotes":{}}))
            with self.assertRaisesRegex(ValueError,"duplicate broker round trip"):
                evaluate([(str(f),str(q))])
    def test_all_trail_variants_still_trading_research_only(self):
        self.assertEqual(len(RULES),9)
        self.assertTrue(all(x.loss==.01 for x in RULES))
if __name__=="__main__":unittest.main()
