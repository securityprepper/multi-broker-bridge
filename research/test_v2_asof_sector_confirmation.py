"""Causal tests for as-of SOXX and breadth confirmations (research only)."""
import unittest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from research.v2_asof_sector_confirmation import (
    PEERS, ETF, asof_context, gate, prior_regular_closes
)

ET = ZoneInfo("America/New_York")
DAY = date(2026, 11, 6)
PREV = date(2026, 11, 5)
AT = datetime(2026, 11, 6, 9, 55, tzinfo=ET)
START = AT - timedelta(minutes=5)
PREV_BAR = datetime(2026, 11, 5, 15, 55, tzinfo=ET)


def bar(price):
    p = float(price)
    return (p, p, p, p, 100)


def sample():
    bars = {}
    for sym in (*PEERS, ETF):
        bars[sym] = {PREV_BAR: bar(100), START: bar(100.5)}
    bars[ETF][START-timedelta(minutes=15)] = bar(100.1)
    return bars


class AsOfSectorConfirmationTests(unittest.TestCase):
    def test_complete_context_and_no_self_peer(self):
        bars = sample()
        ctx = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertEqual(ctx["peer_count"], 7)
        self.assertEqual(ctx["peer_up"], 7)
        self.assertTrue(gate(ctx, "up", "both"))
        self.assertTrue(gate(ctx, "up", "both_momentum"))
        self.assertFalse(gate(ctx, "down", "both"))

    def test_no_future_bar_leakage(self):
        bars = sample()
        before = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        for sym in (*PEERS, ETF):
            bars[sym][AT] = bar(500)
        after = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertEqual(before, after)

    def test_missing_data_fails_closed(self):
        for mutated in ("missing_current", "missing_close", "missing_history"):
            bars = sample()
            if mutated == "missing_current":
                del bars["NVDA"][START]
            elif mutated == "missing_close":
                del bars["NVDA"][PREV_BAR]
            else:
                del bars[ETF][START-timedelta(minutes=15)]
            self.assertIsNone(asof_context(
                bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT))

    def test_early_bar_cannot_be_used(self):
        bars = sample()
        self.assertIsNone(asof_context(
            bars, prior_regular_closes(bars), "AMD", DAY, PREV,
            AT-timedelta(minutes=1)))

    def test_missing_time_zone_fails_closed(self):
        bars = sample()
        self.assertIsNone(asof_context(
            bars, prior_regular_closes(bars), "AMD", DAY, PREV,
            datetime(2026, 11, 6, 9, 55)))

    def test_momentum_gate_uses_completed_etf_data(self):
        bars = sample()
        bars[ETF][START-timedelta(minutes=15)] = bar(100.5)
        ctx = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertTrue(gate(ctx, "up", "both"))
        self.assertFalse(gate(ctx, "up", "both_momentum"))

    def test_breadth_threshold_exact_and_sector_exclusion(self):
        bars = sample()
        for sym in ("NVDA","AVGO","WDC"):
            bars[sym][START] = bar(99.5)
        ctx = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertEqual(ctx["peer_up"], 4)
        self.assertTrue(gate(ctx, "up", "both"))
        bars["INTC"][START] = bar(99.5)
        ctx = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertFalse(gate(ctx, "up", "both"))
        etf_ctx = asof_context(bars, prior_regular_closes(bars), "SOXX", DAY, PREV, AT)
        self.assertEqual(etf_ctx["peer_count"], 8)

    def test_bear_confirmation(self):
        bars = sample()
        for sym in (*PEERS, ETF):
            bars[sym][START] = bar(99.0)
        bars[ETF][START-timedelta(minutes=15)] = bar(99.5)
        ctx = asof_context(bars, prior_regular_closes(bars), "AMD", DAY, PREV, AT)
        self.assertTrue(gate(ctx, "down", "both_momentum"))
        self.assertFalse(gate(ctx, "up", "both"))

    def test_invalid_gate(self):
        with self.assertRaises(ValueError):
            gate(None, "down", "invalid")

if __name__ == "__main__":
    unittest.main()
