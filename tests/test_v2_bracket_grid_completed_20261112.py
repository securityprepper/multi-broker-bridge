"""Research-only tests for timestamp ordering and safe unknown classification."""
import datetime as dt
import unittest
import sys
# Package import from research namespace in isolated checkout
from research.v2_bracket_grid_completed_20261112 import (
    parse,prepare,simulate_one,analyze,UTC
)
START=parse("2026-11-09T16:00:17Z")
def trade():
    return {"day":"2026-11-09","symbol":"AMD","source":"MBB",
            "entry_at":"2026-11-09T16:00:17Z","exit_at":"2026-11-09T16:04:02Z",
            "entry":100,"exit":99.5,"qty":4,
            "entry_order_id":"uid-buy-1","exit_order_id":"uid-sell-1"}
def bars(closes, opens=None):
    times=[parse("2026-11-09T16:01:00Z")+dt.timedelta(minutes=i)
           for i in range(len(closes))]
    out={}
    for i,(timestamp,close) in enumerate(zip(times,closes)):
        op=(opens or closes)[i]
        out[timestamp]={"o":op,"c":close,"h":max(op,close),
                        "l":min(op,close)}
    return out
class CounterfactualTests(unittest.TestCase):
    def test_next_bar_not_signal_bar_open(self):
        r=simulate_one(trade(),START,bars([102,103],[100,101.8]),1,1,0)
        self.assertEqual(r["reason"],"TARGET_CLOSE")
        self.assertAlmostEqual(r["gross_proxy_usd"],7.2)
        self.assertEqual(r["verified_executable_alternative_exits"] if "verified_executable_alternative_exits" in r else 0,0)
    def test_first_partial_bar_cannot_signal(self):
        b=bars([100,100,101.5,101.5],[100,100,100,100])
        b[parse("2026-11-09T16:00:00Z")]={"o":100,"h":200,"l":1,"c":90}
        r=simulate_one(trade(),START,b,1,1,0)
        self.assertEqual(r["reason"],"TARGET_CLOSE")
    def test_emergency_overrides_min_hold(self):
        r=simulate_one(trade(),START,bars([97,97],[100,96]),1,1,30)
        self.assertEqual(r["reason"],"EMERGENCY_CLOSE")
    def test_stop_requires_completed_close(self):
        r=simulate_one(trade(),START,bars([98.8,99.4],[100,98.7]),1,1,0)
        self.assertEqual(r["reason"],"STOP_CLOSE")
        self.assertAlmostEqual(r["gross_proxy_usd"],-5.2)
    def test_no_stale_bar_execution(self):
        r=simulate_one(trade(),START,bars([102]),1,1,0)
        self.assertEqual(r["status"],"NO_NEXT_MINUTE_OPEN")
    def test_missing_first_minute(self):
        r=simulate_one(trade(),START,{},1,1,0)
        self.assertEqual(r["status"],"MISSING_1M")
    def test_minimum_hold_defers_ordinary_stop(self):
        r=simulate_one(trade(),START,bars([99,99,100,100,100,100],[100]*6),1,1,5)
        self.assertEqual(r["status"],"MISSING_1M")
    def test_1340_flat_takes_1340_open(self):
        b={}
        t=parse("2026-11-09T16:01:00Z")
        cutoff=parse("2026-11-09T19:40:00Z")
        while t<=cutoff:
            b[t]={"o":100,"h":100,"l":100,"c":100}
            t+=dt.timedelta(minutes=1)
        b[cutoff]["o"]=100.2;b[cutoff]["h"]=100.2
        r=simulate_one(trade(),START,b,1,1,0)
        self.assertEqual(r["reason"],"FLAT_1340_MARK")
        self.assertAlmostEqual(r["gross_proxy_usd"],0.8)
    def test_duplicate_rejected(self):
        t=trade()
        with self.assertRaises(ValueError):
            list(prepare([t,t],{}))
    def test_bad_input_rejected(self):
        with self.assertRaises(ValueError):
            simulate_one(trade(),START,{},0,1,0)
    def test_no_research_go(self):
        dataset={"research_only":True,"broker_orders_submitted":0,
                 "trades":[trade()],"bars":{}}
        r=analyze(dataset)
        self.assertEqual(r["grid_scenarios_all"],100)
        self.assertFalse(r["new_policy_go"])
        self.assertTrue(r["no_quotes_or_executable_alternatives_proven"])
    def test_nonresearch_input_rejected(self):
        dataset={"research_only":False,"broker_orders_submitted":1,
                 "trades":[trade()],"bars":{}}
        with self.assertRaises(ValueError):analyze(dataset)
if __name__=="__main__":unittest.main()