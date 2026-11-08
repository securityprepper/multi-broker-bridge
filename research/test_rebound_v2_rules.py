import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from research.rebound_v2_rules import decide_from_completed_premarket_bar

ET = ZoneInfo("America/New_York")


class ConditionalExitV2Tests(unittest.TestCase):
    def mark(self):
        return datetime(2026,8,12,8,30,tzinfo=ET)

    def test_profitable_mark_exits_before_open(self):
        t=self.mark()
        d=decide_from_completed_premarket_bar(t,t,Decimal("101"),Decimal("100"))
        self.assertEqual(d.action,"EXIT_PREMARKET")
        self.assertGreater(d.estimated_net_per_share,0)

    def test_unprofitable_mark_only_proposes_research_hold(self):
        t=self.mark()
        d=decide_from_completed_premarket_bar(t,t,Decimal("99"),Decimal("100"))
        self.assertEqual(d.action,"RESEARCH_HOLD_FOR_RTH")
        self.assertLess(d.estimated_net_per_share,0)

    def test_no_lookahead_before_bar_finishes(self):
        t=self.mark()
        with self.assertRaises(ValueError):
            decide_from_completed_premarket_bar(t-timedelta(seconds=2),t,Decimal("101"),Decimal("100"))

    def test_wrong_day_or_stale_bar_rejected(self):
        t=self.mark()
        for observed_end in (t-timedelta(days=1),t-timedelta(minutes=5)):
            with self.assertRaises(ValueError):
                decide_from_completed_premarket_bar(t,observed_end,Decimal("101"),Decimal("100"))

    def test_net_profit_after_sell_cost_not_gross(self):
        t=self.mark()
        d=decide_from_completed_premarket_bar(t,t,Decimal("100.10"),Decimal("100"))
        self.assertEqual(d.action,"RESEARCH_HOLD_FOR_RTH")

    def test_no_naive_datetime_or_nonpositive_price(self):
        t=self.mark()
        with self.assertRaises(ValueError):
            decide_from_completed_premarket_bar(t.replace(tzinfo=None),t,Decimal("101"),Decimal("100"))
        with self.assertRaises(ValueError):
            decide_from_completed_premarket_bar(t,t,Decimal("101"),Decimal("0"))


if __name__=="__main__":
    unittest.main()
