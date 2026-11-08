"""PAPER-only rebound runner safety/clock tests. No network access."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from multi_broker_bridge import paper_rebound_runner as runner


class TimeSafetyTests(unittest.TestCase):
    def moment(self,year,month,day,hour,minute):
        return datetime(year,month,day,hour,minute,tzinfo=ZoneInfo("America/New_York"))

    def test_sunday_closed_before_overnight(self):
        dt=self.moment(2026,11,8,14,0)
        self.assertIsNone(runner._next_session(dt))
        self.assertFalse(runner._entering_window(dt))
        self.assertEqual(runner.run(dt,execute=False),{"status":"SESSION_CLOSED","orders":[]})

    def test_sunday_overnight_targets_monday(self):
        dt=self.moment(2026,11,8,20,10)
        self.assertEqual(runner._next_session(dt).isoformat(),"2026-11-09")
        self.assertTrue(runner._entering_window(dt))

    def test_thursday_evening_targets_friday(self):
        dt=self.moment(2026,11,5,16,30)
        self.assertEqual(runner._next_session(dt).isoformat(),"2026-11-06")
        self.assertTrue(runner._entering_window(dt))

    def test_friday_premarket_allowed_friday_evening_blocked(self):
        self.assertTrue(runner._entering_window(self.moment(2026,11,13,7,45)))
        self.assertFalse(runner._entering_window(self.moment(2026,11,13,20,10)))
        self.assertIsNone(runner._next_session(self.moment(2026,11,13,20,10)))

    def test_execute_flag_protected(self):
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(runner.OrderRejected):
                runner.run(self.moment(2026,11,9,7,0),execute=True)

    def test_paused_holiday_never_queries_new_buys(self):
        import sqlite3
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE owned(trading_day TEXT,symbol TEXT,buy_client_id TEXT,purchased_qty INTEGER,status TEXT)")
        with patch.object(runner,"_db",return_value=db),patch.object(runner,"_broker_inventory",return_value=(
            {"status":"ACTIVE","cash":"100000","trading_blocked":False},[],[])),patch.object(
            runner,"holiday_gate",return_value=False),patch.object(runner,"_fetch_daily") as history,patch.object(
            runner,"_submit") as send:
            result=runner.run(self.moment(2026,11,9,6,15),execute=False)
            self.assertEqual(result["status"],"HOLIDAY_GATE_PAUSED")
            history.assert_not_called()
            send.assert_not_called()

    def test_bullish_alert_can_be_generated_without_order_execution(self):
        import sqlite3
        from unittest.mock import Mock
        from multi_broker_bridge.five_day_rebound import SectorDecision
        now=self.moment(2026,11,5,17,10)
        db=sqlite3.connect("file:rebound_alert_fixture?mode=memory&cache=shared",uri=True)
        readback=sqlite3.connect("file:rebound_alert_fixture?mode=memory&cache=shared",uri=True)
        db.executescript("""
        CREATE TABLE owned(trading_day TEXT,symbol TEXT,buy_client_id TEXT,purchased_qty INTEGER,status TEXT);
        CREATE TABLE attempts(trading_day TEXT,symbol TEXT,side TEXT,count INTEGER,client_id TEXT,state TEXT);
        CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,time_utc TEXT,trading_day TEXT,type TEXT,symbol TEXT,details TEXT);
        """)
        closes={s:[Decimal("100")]*5+[Decimal("95")] for s in runner.SYMBOLS}
        signal=SectorDecision("down",{}, {}, {}, True,"BUY_WATCH",now)
        with patch.object(runner,"_db",return_value=db),patch.object(runner,"_broker_inventory",return_value=(
            {"status":"ACTIVE","cash":"100000","trading_blocked":False},[],[])),patch.object(
            runner,"holiday_gate",return_value=True),patch.object(runner,"_fetch_daily",return_value=closes),patch.object(
            runner,"_fetch_sector_bars",return_value={}),patch.object(runner,"evaluate",return_value=signal),patch.object(
            runner,"_quotes",return_value={s:(Decimal("99"),Decimal("100")) for s in runner.BASKET}),patch.object(
            runner,"paper_api",return_value={"tradable":True,"overnight_tradable":True}),patch.object(
            runner,"_submit") as submit:
            result=runner.run(now,execute=False)
            self.assertEqual(result["status"],"BULLISH_SIGNAL")
            self.assertEqual(len(result["orders"]),9)
            self.assertEqual(readback.execute("SELECT COUNT(*) FROM events WHERE type='BULLISH_ALERT'").fetchone()[0],1)
            submit.assert_not_called()

    def test_existing_open_sell_blocks_duplicate_exit(self):
        import sqlite3
        now=self.moment(2026,11,9,8,25)
        db=sqlite3.connect(":memory:")
        db.executescript("""
        CREATE TABLE owned(trading_day TEXT,symbol TEXT,buy_client_id TEXT,purchased_qty INTEGER,status TEXT);
        CREATE TABLE attempts(trading_day TEXT,symbol TEXT,side TEXT,count INTEGER,client_id TEXT,state TEXT);
        CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,time_utc TEXT,trading_day TEXT,type TEXT,symbol TEXT,details TEXT);
        """)
        db.execute("INSERT INTO owned VALUES(?,?,?,?,?)",("2026-11-09","AMD","FDR-20261109-B-AMD-1",2,"ENTRY_ACCEPTED_NOT_FILLED"))
        order={"symbol":"AMD","side":"sell","status":"new","client_order_id":"FDR-20261109-E-AMD-1",
               "id":"example-order","created_at":self.moment(2026,11,9,8,24).isoformat()}
        position={"symbol":"AMD","side":"long","qty":"2","qty_available":"2"}
        with patch.object(runner,"_db",return_value=db),patch.object(runner,"_broker_inventory",return_value=(
            {"status":"ACTIVE","cash":"100000","trading_blocked":False},[position],[order])),patch.object(
            runner,"_quotes",return_value={"AMD":(Decimal("100"),Decimal("101"))}),patch.object(
            runner,"_cancel_open") as cancel,patch.object(runner,"_submit") as submit:
            result=runner.run(now,execute=False)
            self.assertEqual(result["status"],"EXIT_MANAGEMENT")
            self.assertIn("AWAIT_SELL_FILL:AMD",result["orders"])
            cancel.assert_not_called()
            submit.assert_not_called()


if __name__=="__main__":
    unittest.main()
