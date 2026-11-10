"""Research-only commissioning blockers: DECIMAL(18,6) equality and backlog overflow."""
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

from recommendation_paper_bridge.reconcile import (
    check_parent, reconcile_once, Unsafe
)
from recommendation_paper_bridge.exit_guard import run_guard_once


def parent(price):
    return {
        "id": "broker-parent", "client_order_id": "TO-P-frozen",
        "symbol": "AMD", "side": "buy", "order_class": "bracket",
        "type": "limit", "limit_price": price,
    }


ROW = {
    "broker_order_id": "broker-parent", "client_order_id": "TO-P-frozen",
    "symbol": "AMD", "limit_price": Decimal("100.100000"),
}


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []
    def execute(self, query, params=None):
        self.queries.append(query)
    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, rows):
        self.cur = FakeCursor(rows)
        self.closed = False
    def cursor(self, dictionary=False):
        return self.cur
    def commit(self):
        pass
    def close(self):
        self.closed = True


def account_response(method, path):
    if (method, path) == ("GET", "/v2/account"):
        return {"id": "allowed-paper-account", "trading_blocked": False}
    raise AssertionError("No order/position/network calls allowed in overflow test")


class TestPriceAndQueueSafety(unittest.TestCase):
    def test_decimal_mysql_scale_equal_to_broker_shorter_string(self):
        check_parent(ROW, parent("100.1"))
        check_parent(ROW, parent("100.10"))
        check_parent(ROW, parent("100.100000"))

    def test_decimal_precision_differences_still_rejected(self):
        for bad in ("100.100001", "100.11", "NaN", "inf", "", None):
            with self.subTest(price=bad), self.assertRaises(Unsafe):
                check_parent(ROW, parent(bad))

    def test_active_reconcile_query_excludes_terminal_closed_but_rechecks_unfilled(self):
        conn = FakeConn([])
        with patch.dict(os.environ, {"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT": "allowed-paper-account"}):
            self.assertEqual(reconcile_once(connect=lambda _: conn, httpfn=account_response), [])
        sql = conn.cur.queries[0]
        self.assertNotIn("CLOSED_NEEDS_FEE_RECON", sql)
        self.assertIn("'UNFILLED'", sql)
        self.assertIn("'PARTIAL_UNPROTECTED' THEN 0", sql)
        self.assertIn("LIMIT 51", sql)
        self.assertTrue(conn.closed)

    def test_reconciler_never_silently_skips_51st_active_intent(self):
        conn = FakeConn([{} for _ in range(51)])
        with patch.dict(os.environ, {"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT": "allowed-paper-account"}):
            with self.assertRaisesRegex(Unsafe, "backlog exceeds 50"):
                reconcile_once(connect=lambda _: conn, httpfn=account_response)
        self.assertTrue(conn.closed)

    def test_exit_guard_never_silently_skips_76th_active_intent(self):
        conn = FakeConn([{} for _ in range(76)])
        with patch.dict(os.environ, {"PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT": "allowed-paper-account"}), \
             patch("recommendation_paper_bridge.exit_guard.require_commissioned", return_value=None):
            with self.assertRaisesRegex(Unsafe, "backlog exceeds 75"):
                run_guard_once(connect=lambda _: conn, httpfn=account_response)
        self.assertTrue(conn.closed)


if __name__ == "__main__":
    unittest.main()
