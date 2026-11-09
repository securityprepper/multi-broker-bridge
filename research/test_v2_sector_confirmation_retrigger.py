"""Completed-bar re-trigger tests: sector confirmation can arrive later."""
import unittest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from research.v2_sector_confirmation_retrigger import first_confirmed

ET = ZoneInfo("America/New_York")
DAY = date(2026, 11, 6)

def at(h,m):
    return datetime(2026,11,6,h,m,tzinfo=ET)

def bar(price, high=None, low=None):
    return (float(price),float(high if high is not None else price),
            float(low if low is not None else price),float(price),100)

def bearish():
    return {
        at(9,30): bar(98.5),
        at(9,35): bar(98.6),
        at(9,40): bar(98.4),
        at(9,45): bar(97.5),
        at(9,50): bar(97.1),
        at(9,55): bar(97.0), # for outcome scoring ONLY
    }

def ctx_for_buydown(timepoint):
    return {
        "etf_pct": -0.5 if timepoint>=at(9,55) else 0.5,
        "etf_15m_pct": -0.3 if timepoint>=at(9,55) else 0.3,
        "peer_count":7,
        "peer_down": 5 if timepoint>=at(9,55) else 1,
        "peer_up": 1,
    }

class RetriggerTests(unittest.TestCase):
    def test_retrigger_later_when_context_confirms(self):
        first = first_confirmed(bars=bearish(), previous_close=100,
            day=DAY, family="down_close", variant="baseline",
            context_at=ctx_for_buydown)
        confirmed = first_confirmed(bars=bearish(), previous_close=100,
            day=DAY, family="down_close", variant="both",
            context_at=ctx_for_buydown)
        self.assertEqual(first["asof"],at(9,50).isoformat())
        self.assertEqual(confirmed["asof"],at(9,55).isoformat())
        self.assertEqual(confirmed["next_bar_open"],97)

    def test_future_price_does_not_change_alert_time(self):
        first = first_confirmed(bars=bearish(), previous_close=100, day=DAY,
            family="down_close", variant="both", context_at=ctx_for_buydown)
        changed = bearish()
        changed[at(9,55)] = bar(500)
        second = first_confirmed(bars=changed, previous_close=100, day=DAY,
            family="down_close", variant="both", context_at=ctx_for_buydown)
        self.assertEqual(first["asof"],second["asof"])
        self.assertEqual(first["price"],second["price"])
        self.assertNotEqual(first["next_bar_open"],second["next_bar_open"])

    def test_no_confirmation_means_no_event(self):
        self.assertIsNone(first_confirmed(
            bars=bearish(), previous_close=100, day=DAY,
            family="down_close", variant="both",
            context_at=lambda a: None))

    def test_reversal_triggers_while_still_above_previous_close(self):
        bars = {
            at(9,30):bar(104,high=105),
            at(9,35):bar(104),
            at(9,40):bar(103),
            at(9,45):bar(101),
            at(9,50):bar(101),
        }
        evt = first_confirmed(bars=bars, previous_close=100, day=DAY,
            family="down_reversal", variant="baseline",
            context_at=lambda _:None)
        self.assertEqual(evt["asof"], at(9,50).isoformat())
        self.assertGreater(evt["base_change_pct"],0)

    def test_upside_reversal(self):
        bars = {
            at(9,30):bar(96,low=95),
            at(9,35):bar(96.5),
            at(9,40):bar(97),
            at(9,45):bar(98),
            at(9,50):bar(98.1),
        }
        evt = first_confirmed(bars=bars, previous_close=100, day=DAY,
            family="up_reversal", variant="baseline",
            context_at=lambda _:None)
        self.assertEqual(evt["asof"], at(9,50).isoformat())
        self.assertLess(evt["base_change_pct"],0)

    def test_orderless_research_code(self):
        import inspect
        from research import v2_sector_confirmation_retrigger as module
        source = inspect.getsource(module)
        self.assertNotIn("submit_order(",source)
        self.assertNotIn("trading_client(",source)

if __name__ == "__main__":
    unittest.main()
