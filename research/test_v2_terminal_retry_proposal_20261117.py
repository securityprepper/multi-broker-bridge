"""Broker-disabled V2 PAPER risk-exit terminal order gap regression.

Until fixed, the two desired recovery tests are expected failures.
No credentials, broker POST, LIVE, production ledger, or service modifications.
"""
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from unittest.mock import patch

import direction_paper as p
from test_v2_paper_signed_short_safety import Broker,seeded,quote,ct

class TerminalOrderBroker(Broker):
    def __init__(self,filled_qty="0",state="expired"):
        super().__init__()
        self.terminal_filled_qty=filled_qty
        self.state=state
    def __call__(self,method,path,body=None):
        if method=="GET" and path.startswith("/v2/orders:by_client_order_id?"):
            key=parse_qs(urlsplit(path).query)["client_order_id"][0]
            for i,original in enumerate(self.posts,1):
                if original["client_order_id"]==key:
                    return {
                        "id":"OFFLINE-MOCK-"+str(i),
                        "client_order_id":key,
                        "symbol":original["symbol"],
                        "status":self.state,
                        "qty":original["qty"],
                        "filled_qty":self.terminal_filled_qty,
                        "filled_avg_price":"101.20" if self.terminal_filled_qty!="0" else None,
                        "filled_at":None}
        return super().__call__(method,path,body)

class TerminalRiskExitRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=p.connect(Path(self.temp.name)/"reproduction.sqlite3")
        p.migrate_audit(self.db)
        self.addCleanup(self.db.close)
        seeded(self.db,shares=4,side="sell",price=100)
        patcher=patch.object(p,"expected_account",return_value="PAPER_TEST_ACCOUNT")
        patcher.start()
        self.addCleanup(patcher.stop)

    def first_limit_expires(self,filled_qty):
        broker=TerminalOrderBroker(filled_qty=filled_qty)
        first=p.software_risk_exits(self.db,ct(17,13,40),broker=broker,quotes=quote)
        self.assertEqual(len(first),1)
        self.assertEqual(len(broker.posts),1)
        p.reconcile_orders(self.db,ct(18,3,5),broker=broker)
        return broker

    def test_zero_fill_expired_day_limit_requires_new_idempotent_attempt(self):
        broker=self.first_limit_expires("0")
        # Desired behavior: terminal broker-verified zero fill and unchanged
        # whole signed inventory permit ONE new deterministic retry ID.
        # Current deployed code silently reuses the same order ID -> no POST.
        second=p.software_risk_exits(self.db,ct(18,3,5),broker=broker,quotes=quote)
        self.assertEqual(len(second),1)
        self.assertEqual(len(broker.posts),2)
        self.assertNotEqual(broker.posts[0]["client_order_id"],
                            broker.posts[1]["client_order_id"])

    def test_partially_filled_then_expired_is_not_zero_fill(self):
        broker=self.first_limit_expires("2")
        # Desired behavior: preserve 2/4 shares' true broker fill, never mark
        # as zero or assume full closure. Require independent reconciliation
        # and exact remaining account-matched position before any further close.
        recorded=self.db.execute(
            "SELECT outcome,filled_qty FROM paper_attempts "
            "WHERE role='RISK_EXIT_SESSION_FLAT_1340_CT'").fetchone()
        self.assertNotEqual(recorded[0],"BROKER_ORDER_TERMINAL_UNFILLED")
        self.assertEqual(recorded[1],2)

if __name__=="__main__":
    unittest.main(verbosity=2)
