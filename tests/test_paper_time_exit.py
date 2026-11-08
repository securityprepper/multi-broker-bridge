"""Broker-free tests for RTH PAPER liquidation independent of market-data availability."""
import os
import tempfile
import sqlite3
import unittest
from datetime import datetime,timezone
from unittest.mock import patch

from multi_broker_bridge import auto_paper
from multi_broker_bridge.paper_time_exit import timed_flatten
from multi_broker_bridge.models import OrderRejected,UnknownSubmission

AT_ENTRY=datetime(2026,11,9,18,0,tzinfo=timezone.utc)  # 12:00 CST
AT_EXIT=datetime(2026,11,9,19,41,tzinfo=timezone.utc)   # 13:41 CST
AT_URGENT=datetime(2026,11,9,19,51,tzinfo=timezone.utc) # 13:51 CST
AT_OVERDUE=datetime(2026,11,9,20,1,tzinfo=timezone.utc) # 14:01 CST
AT_LATE=datetime(2026,11,9,22,1,tzinfo=timezone.utc)    # 16:01 CST

class PaperBook:
    def __init__(self):
        self.positions={"AMD":"3","MU":"2"}
        self.orders=[]
        self.posts=[]
        self.cancellations=[]
        self.ambiguous=False
    def request(self,method,path,payload=None):
        if path=="/v2/clock":
            return {"is_open":True}
        if method=="POST" and path=="/v2/orders":
            self.posts.append(payload)
            if self.ambiguous:
                raise UnknownSubmission("simulated lost broker receipt")
            return {"id":"paper_"+str(len(self.posts)),
                    "client_order_id":payload["client_order_id"],
                    "status":"accepted"}
        if method=="DELETE" and path.startswith("/v2/orders/"):
            self.cancellations.append(path)
            self.orders=[o for o in self.orders if o["id"] not in path]
            return {}
        raise AssertionError((method,path))

    def snapshot_positions(self):
        return [{"symbol":symbol,"qty":qty,"qty_available":qty,
                 "side":"long","avg_entry_price":"100.00"}
                for symbol,qty in self.positions.items()]

class TimedFlattenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env=patch.dict(os.environ,{
            "MULTI_BROKER_STATE_DIR":self.tmp.name,
            "MULTI_BROKER_ALLOW_PAPER":"1"})
        self.env.start();self.addCleanup(self.env.stop)
        with auto_paper._state() as db:
            for sym,qty in (("AMD",3),("MU",2)):
                db.execute("INSERT INTO tracked VALUES(?,?,?,?,?)",
                           (sym,"MBB-ENTRY-"+sym,"100.00",
                            AT_ENTRY.isoformat(),qty))
            db.commit()

    def step(self,now,book,*,positions=None):
        with auto_paper._state() as db:
            return timed_flatten(now,
                book.snapshot_positions() if positions is None else positions,
                book.orders[:],db,book.request)

    def test_before_1340_no_time_based_broker_action(self):
        book=PaperBook()
        result=self.step(datetime(2026,11,9,19,39,tzinfo=timezone.utc),book)
        self.assertIsNone(result)
        self.assertEqual(book.posts,[])
    def test_1340_sells_all_verified_managed_stocks_not_one_etf(self):
        book=PaperBook()
        first=self.step(AT_EXIT,book)
        self.assertEqual(first["status"],"FLATTEN_IN_PROGRESS")
        self.assertEqual({p["symbol"] for p in book.posts},{"AMD","MU"})
        self.assertEqual({p["qty"] for p in book.posts},{"2","3"})
        self.assertTrue(all(p["side"]=="sell" and p["type"]=="market"
                            and not p["extended_hours"] for p in book.posts))
        self.assertFalse(first["flat_verified"])
        again=self.step(AT_URGENT,book)
        self.assertEqual(len(book.posts),2)
        self.assertTrue(again["overdue"])
        self.assertTrue(all(a.startswith("FLATTEN_PREVIOUSLY_RESERVED") for a in again["actions"]))
        book.positions.clear()
        last=self.step(AT_OVERDUE,book)
        self.assertTrue(last["flat_verified"])
        self.assertFalse(last["overdue"])
    def test_cancel_open_owned_order_and_wait_readback(self):
        book=PaperBook()
        book.orders=[{"symbol":"AMD","side":"buy","status":"new",
                      "id":"uuid0001","client_order_id":"MBB-OLD-AMD"}]
        first=self.step(AT_EXIT,book)
        self.assertEqual(first["status"],"AWAIT_BROKER_CANCEL_READBACK")
        self.assertEqual(len(book.cancellations),1)
        self.assertEqual(book.posts,[])
        second=self.step(AT_URGENT,book)
        self.assertEqual(second["status"],"FLATTEN_IN_PROGRESS")
        self.assertEqual(len(book.posts),2)
    def test_manual_order_blocks_deleting_or_selling(self):
        book=PaperBook()
        book.orders=[{"symbol":"AMD","side":"sell","status":"new",
                      "id":"some-manual","client_order_id":"MANUAL-01"}]
        result=self.step(AT_EXIT,book)
        self.assertEqual(result["status"],"UNMANAGED_ORDER_BLOCKED")
        self.assertEqual(book.cancellations,[])
        self.assertEqual(book.posts,[])
    def test_do_not_sell_added_untracked_manual_shares(self):
        book=PaperBook()
        book.positions["AMD"]="5"
        with self.assertRaises(OrderRejected):
            self.step(AT_EXIT,book)
        self.assertEqual(book.posts,[])
    def test_broker_receipt_uncertain_never_posts_again(self):
        book=PaperBook()
        book.ambiguous=True
        with self.assertRaises(UnknownSubmission):
            self.step(AT_EXIT,book)
        self.assertEqual(len(book.posts),1)
        book.ambiguous=False
        again=self.step(AT_URGENT,book)
        self.assertEqual(len(book.posts),2)  # two distinct stocks, not AMD retried
        self.assertEqual({p["symbol"] for p in book.posts},{"AMD","MU"})
        self.assertEqual(again["status"],"FLATTEN_IN_PROGRESS")
    def test_no_trading_after_regular_session(self):
        book=PaperBook()
        self.assertIsNone(self.step(AT_LATE,book))
        self.assertEqual(book.posts,[])
    def test_guard_runs_before_fetching_stale_market_bars(self):
        book=PaperBook()
        def broker(method,path,payload=None):
            if path=="/v2/account":
                return {"id":"PAPER","status":"ACTIVE","trading_blocked":False,
                        "cash":"10000"}
            if path=="/v2/positions":return book.snapshot_positions()
            if path.startswith("/v2/orders?"):return book.orders[:]
            return book.request(method,path,payload)
        with patch.object(auto_paper,"paper_api",side_effect=broker):
            with patch.object(auto_paper,"fetch_bars_and_quotes",
                              side_effect=AssertionError("must not rely on data for exit")):
                actual=auto_paper.run(AT_EXIT,execute=True)
        self.assertEqual(actual["status"],"PAPER_DAILY_EXIT_GUARD")
        self.assertEqual({p["symbol"] for p in book.posts},{"AMD","MU"})
        self.assertEqual(actual["gate_allows_new_entries"],False)
        self.assertEqual(actual["exit_guard"]["status"],"FLATTEN_IN_PROGRESS")
    def test_closing_window_never_adds_new_risk(self):
        book=PaperBook()
        with patch.object(auto_paper,"fetch_bars_and_quotes",
                          side_effect=AssertionError("must not enter a new stock")):
            with patch.object(auto_paper,"paper_api",
                              side_effect=lambda method,path,payload=None:
                              {"id":"PAPER","status":"ACTIVE","trading_blocked":False,
                               "cash":"10000"} if path=="/v2/account" else
                              book.snapshot_positions() if path=="/v2/positions" else
                              [] if path.startswith("/v2/orders?") else
                              book.request(method,path,payload)):
                result=auto_paper.run(AT_EXIT,execute=True)
        self.assertEqual(result["mode"],"PAPER_EXECUTION")
        self.assertTrue(all(p["side"]=="sell" for p in book.posts))

if __name__=="__main__":
    unittest.main()
