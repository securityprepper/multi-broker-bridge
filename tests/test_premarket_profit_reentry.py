"""PAPER premarket profit and reentry guardrails: zero broker calls."""
import unittest
from datetime import datetime,timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo
from multi_broker_bridge.premarket_policy import (
    premarket_sell_decision,eligible_discount_reentry,
    trading_session_day,is_early_market
)

CT=ZoneInfo("America/Chicago")

class PremarketPolicyTests(unittest.TestCase):
    def setUp(self):
        self.p=datetime(2026,11,9,7,15,tzinfo=CT)
    def test_small_premarket_losses_do_not_trigger_routine_trailing(self):
        for reason in ("premarket standard peak trailing stop",
                       "premarket steady peak trailing stop",
                       "premarket substantial profit reversal",
                       "premarket confirmed trailing profit reversal"):
            self.assertEqual(
                premarket_sell_decision(self.p,D("100"),D("99.45"),reason,
                                        peak=D("104"),steady_confirmed=("steady" in reason)),
                "HOLD_FOR_TREND")
    def test_1_9_percent_gain_not_substantial(self):
        self.assertEqual(premarket_sell_decision(
            self.p,D("100"),D("101.90"),
            "premarket standard peak trailing stop",peak=D("104")),
            "HOLD_FOR_TREND")
    def test_trailing_profit_must_still_be_at_least_2_percent(self):
        self.assertEqual(premarket_sell_decision(
            self.p,D("100"),D("102.10"),
            "premarket standard peak trailing stop",peak=D("104.40")),
            "TRAILING_STOP_SOFTWARE")
    def test_verified_2pct_profit_reversal(self):
        self.assertEqual(premarket_sell_decision(
            self.p,D("100"),D("102.00"),
            "premarket substantial profit reversal",peak=D("103")),
            "SUBSTANTIAL_PROFIT_TAKE")
    def test_emergency_2_5_pct_loss_exception(self):
        self.assertEqual(premarket_sell_decision(
            self.p,D("100"),D("97.50"),
            "premarket emergency downside exit",peak=D("102")),
            "EMERGENCY_DOWNSIDE_EXIT")
    def test_premarket_afterhours_and_rth_boundary(self):
        self.assertTrue(is_early_market(self.p))
        self.assertTrue(is_early_market(datetime(2026,11,8,19,30,tzinfo=CT)))
        self.assertFalse(is_early_market(datetime(2026,11,9,8,30,tzinfo=CT)))
    def eligible(self,**override):
        p=dict(now=datetime(2026,11,9,8,20,tzinfo=CT),
            sell_filled_at=datetime(2026,11,9,7,20,tzinfo=CT),
            sell_filled_price=D("104"),entry_filled_price=D("100"),
            next_verified_ask=D("103.50"),fully_filled=True,
            actual_rising_breadth=True,positions_absent=True,
            pending_orders_absent=True,already_reentered=False)
        p.update(override)
        return eligible_discount_reentry(**p)
    def test_lower_filled_reentry_before_10am(self):
        self.assertTrue(self.eligible())
        self.assertFalse(self.eligible(
            now=datetime(2026,11,9,10,0,tzinfo=CT)))
    def test_reentry_requires_cheaper_ask_and_full_broker_exit(self):
        for kwargs in (
            {"next_verified_ask":D("104.01")},
            {"next_verified_ask":D("103.90")},
            {"sell_filled_price":D("101.9")},
            {"fully_filled":False},
            {"actual_rising_breadth":False},
            {"pending_orders_absent":False},
            {"positions_absent":False},
            {"already_reentered":True},
        ):
            self.assertFalse(self.eligible(**kwargs),kwargs)
    def test_minimum_two_minutes_after_confirmed_filled_sale(self):
        self.assertFalse(self.eligible(
            now=datetime(2026,11,9,7,21,tzinfo=CT)))
    def test_sunday_evening_is_same_monday_trading_session(self):
        sunday=datetime(2026,11,8,19,25,tzinfo=CT)
        monday=datetime(2026,11,9,9,5,tzinfo=CT)
        self.assertEqual(trading_session_day(sunday),trading_session_day(monday))
        self.assertTrue(self.eligible(now=monday,sell_filled_at=sunday))
    def test_friday_sale_cannot_reenter_monday_using_stale_profit(self):
        self.assertFalse(self.eligible(
            sell_filled_at=datetime(2026,11,6,7,0,tzinfo=CT)))

if __name__=="__main__":
    unittest.main()
