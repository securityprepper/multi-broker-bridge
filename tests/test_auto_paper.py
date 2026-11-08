"""Broker-free strategy tests, including real PAPER submission API mock."""
import os
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from unittest.mock import patch
from multi_broker_bridge import auto_paper
from multi_broker_bridge.trend import Bar, TrendMonitor

NOW=datetime(2026,11,6,14,59,tzinfo=timezone.utc)
SECTORS={"semiconductors":("AMD","MU","SNDK")}

def fixtures(now):
    bars={}
    for sym in SECTORS["semiconductors"]:
        bars[sym]=[]
        for i in range(4):
            price=Decimal(100+i)
            bars[sym].append(Bar(sym,now-timedelta(minutes=4-i),
                price+1,price-1,price))
    quotes={sym:(Decimal("102.90"),Decimal("103.10"))
            for sym in SECTORS["semiconductors"]}
    return bars,quotes

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env=patch.dict(os.environ,{
            "MULTI_BROKER_STATE_DIR":self.tmp.name,
            "MULTI_BROKER_ALLOW_PAPER":"1"})
        self.env.start();self.addCleanup(self.env.stop)
        self.mock_sector=patch.object(auto_paper,"SECTORS",SECTORS)
        self.mock_sector.start();self.addCleanup(self.mock_sector.stop)
        self.mock_trend=patch.object(auto_paper,"TrendMonitor",
            side_effect=lambda:TrendMonitor(SECTORS))
        self.mock_trend.start();self.addCleanup(self.mock_trend.stop)
        self.mock_data=patch.object(auto_paper,"fetch_bars_and_quotes",
            side_effect=lambda now,syms,feed:fixtures(now))
        self.mock_data.start();self.addCleanup(self.mock_data.stop)
        self.gate=patch.object(auto_paper,"holiday_gate",return_value=True)
        self.gate.start();self.addCleanup(self.gate.stop)
        self.posts=[]

    def broker(self,method,path,payload=None):
        if path=="/v2/account":
            return {"id":"PAPER","status":"ACTIVE","trading_blocked":False,
                    "cash":"10000.00"}
        if path=="/v2/positions" or path.startswith("/v2/orders?"):
            return []
        if method=="POST" and path=="/v2/orders":
            self.posts.append(payload)
            return {"id":"brokerpaper-"+str(len(self.posts)),
                    "client_order_id":payload["client_order_id"],
                    "status":"accepted"}
        raise AssertionError((method,path))

    def test_simulation_generates_three_independent_buys_without_orders(self):
        with patch.object(auto_paper,"paper_api",side_effect=self.broker):
            result=auto_paper.run(NOW,execute=False)
        self.assertEqual(result["mode"],"SIMULATION")
        self.assertEqual({r["symbol"] for r in result["orders"]},set(SECTORS["semiconductors"]))
        self.assertEqual(self.posts,[])

    def test_live_paper_path_mock_submits_once_per_stock_and_dedupes(self):
        with patch.object(auto_paper,"paper_api",side_effect=self.broker):
            result=auto_paper.run(NOW,execute=True)
            replay=auto_paper.run(NOW+timedelta(minutes=1),execute=True)
        self.assertEqual(len(self.posts),3)
        self.assertEqual(len(result["orders"]),3)
        self.assertEqual(replay["orders"],[])
        for payload in self.posts:
            self.assertEqual(payload["type"],"limit")
            self.assertTrue(payload["extended_hours"])
            self.assertEqual(payload["time_in_force"],"day")
            self.assertEqual(payload["side"],"buy")
            self.assertLessEqual(Decimal(payload["qty"])*Decimal(payload["limit_price"]),Decimal("2000"))

    def test_holiday_pause_blocks_new_entries(self):
        with patch.object(auto_paper,"holiday_gate",return_value=False):
            with patch.object(auto_paper,"paper_api",side_effect=self.broker):
                result=auto_paper.run(NOW,execute=True)
        self.assertFalse(result["gate_allows_new_entries"])
        self.assertEqual(self.posts,[])

    def test_no_order_if_broker_inventory_missing(self):
        def incomplete(method,path,payload=None):
            if path=="/v2/positions":return {}
            return self.broker(method,path,payload)
        with patch.object(auto_paper,"paper_api",side_effect=incomplete):
            with self.assertRaises(Exception):
                auto_paper.run(NOW,execute=True)
        self.assertEqual(self.posts,[])

    def test_sell_at_155pm_ct_is_market_exit_not_unfilled_limit(self):
        close_time=datetime(2026,11,6,19,56,tzinfo=timezone.utc)
        with auto_paper._state() as db:
            db.execute("INSERT INTO tracked VALUES(?,?,?,?,?)",
                ("AMD","MBB-ENTRY-AMD","100.00",
                 (close_time-timedelta(minutes=10)).isoformat(),4))
        def broker(method,path,payload=None):
            if path=="/v2/positions":
                return [{"symbol":"AMD","side":"long","qty":"4",
                         "qty_available":"4","avg_entry_price":"100.00"}]
            return self.broker(method,path,payload)
        with patch.object(auto_paper,"paper_api",side_effect=broker):
            result=auto_paper.run(close_time,execute=True)
        sells=[x for x in self.posts if x["side"]=="sell"]
        self.assertEqual(len(sells),1)
        self.assertEqual(sells[0]["type"],"market")
        self.assertEqual(sells[0]["qty"],"4")
        self.assertFalse(sells[0]["extended_hours"])
        self.assertNotIn("limit_price",sells[0])
        self.assertEqual(result["orders"][0]["symbol"],"AMD")

    def test_only_own_stale_buy_cancels_and_no_same_tick_reentry(self):
        now=NOW
        refs=[]
        def broker(method,path,payload=None):
            if method=="GET" and path.startswith("/v2/orders?"):
                return [
                    {"id":"owned-old","symbol":"AMD","side":"buy",
                     "status":"accepted","client_order_id":"MBB-OLD-AMD",
                     "created_at":(now-timedelta(minutes=5)).isoformat()},
                    {"id":"manual-old","symbol":"MU","side":"buy",
                     "status":"accepted","client_order_id":"EXTERNAL-MU",
                     "created_at":(now-timedelta(minutes=5)).isoformat()}
                ]
            if method=="DELETE":
                refs.append(path)
                return {}
            return self.broker(method,path,payload)
        with patch.object(auto_paper,"paper_api",side_effect=broker):
            result=auto_paper.run(now,execute=True)
        self.assertEqual(refs,["/v2/orders/owned-old"])
        self.assertEqual([x["symbol"] for x in self.posts],["SNDK"])
        self.assertTrue(any(x.get("status")=="CANCEL_REQUESTED" for x in result["orders"]))

    def test_feed_closed_does_not_request_broker(self):
        saturday=datetime(2026,11,7,22,0,tzinfo=timezone.utc)
        with patch.object(auto_paper,"paper_api",side_effect=AssertionError("broker called")):
            result=auto_paper.run(saturday,execute=True)
        self.assertEqual(result["status"],"SESSION_CLOSED")

if __name__=="__main__":
    unittest.main()
