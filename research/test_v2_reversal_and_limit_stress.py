"""No-lookahead and minimum-price tests for candidate streaming exits."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_reversal_and_limit_stress import (
    candidate, first_day_signals, executable_proxy,
)


class ReversalTests(unittest.TestCase):
    def test_overlapping_thresholds(self):
        self.assertTrue(candidate("down",100,100,98.5,97.4))
        self.assertFalse(candidate("down",100,100,98.5,97.6))
        self.assertTrue(candidate("up",100,100,101.5,102.6))

    def test_reversal_without_minus_2p5_from_prev_close(self):
        d=date(2026,11,20)
        t=lambda minute:datetime.combine(d,time(9,minute),ET)
        bars={t(30):[102.5,106.4,102,105,100],
              t(35):[105,106.2,103,104,100],
              t(40):[104,105,102,103,100],
              t(45):[103,103,101,101.9,100],
              t(50):[101.9,102,99,100.5,100],
              t(55):[100.5,101,100,100.1,100]}
        out=first_day_signals(bars,d,100)
        self.assertIn("down_reversal",out)
        self.assertNotIn("down_close",out)
        self.assertEqual(out["down_reversal"]["asof"],t(50).isoformat())
        self.assertEqual(out["down_reversal"]["next_bar_open"],101.9)

    def test_latest_high_not_future(self):
        d=date(2026,3,9)
        t=lambda m:datetime.combine(d,time(9,m),ET)
        bars={t(30):[100,100.1,99,100,100],t(35):[100,100,99,99.5,100],
              t(40):[99.5,100,99,100,100],t(45):[100,100,98,98,100],
              t(50):[98,110,97,107,100]}
        out=first_day_signals(bars,d,100)
        self.assertNotIn("down_reversal",out)
        self.assertIn("up_reversal",out)
        self.assertEqual(out["up_reversal"]["asof"],t(55).isoformat())

    def test_limit_fails_when_next_open_below_limit(self):
        e={"price":97.5,"next_bar_open":96.0}
        result=executable_proxy(e,94,"down",30)
        self.assertFalse(result["price_eligible"])
        self.assertEqual(result["bounded_advantage_pp"],0)
        self.assertGreater(result["proxy_unbounded_advantage_pp"],0)

    def test_limit_is_price_eligible_not_verified(self):
        e={"price":97.5,"next_bar_open":97.4}
        result=executable_proxy(e,94,"down",30)
        self.assertTrue(result["price_eligible"])
        self.assertGreater(result["bounded_advantage_pp"],0)

    def test_buy_limit_can_miss_gap_up(self):
        e={"price":102.5,"next_bar_open":104.0}
        result=executable_proxy(e,106,"up",30)
        self.assertFalse(result["price_eligible"])
        self.assertEqual(result["bounded_advantage_pp"],0)


if __name__ == "__main__":
    unittest.main()
