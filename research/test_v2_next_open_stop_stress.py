"""Next-open price stress: not live executions or fill claims."""
import unittest
from research.v2_next_open_stop_stress import price_scenario

def ev(price=100, nxt=100):
    return {"price":price, "next_bar_open":nxt}

class NextOpenStopStressTests(unittest.TestCase):
    def test_stopping_before_next_open_can_save_downside(self):
        x = price_scenario(ev(),90,100,"down")
        self.assertTrue(x["price_eligible"])
        self.assertAlmostEqual(x["bounded_advantage_nextopen_pp"],9.985)

    def test_stopping_before_next_open_can_miss_recovery(self):
        x=price_scenario(ev(),110,100,"down")
        self.assertTrue(x["price_eligible"])
        self.assertLess(x["bounded_advantage_nextopen_pp"],-9.9)

    def test_unfilled_limit_is_not_assumed_executed(self):
        x=price_scenario(ev(nxt=99),90,100,"down")
        self.assertFalse(x["price_eligible"])
        self.assertEqual(x["bounded_advantage_nextopen_pp"],0)
        self.assertGreater(x["unbounded_advantage_nextopen_pp"],0)

    def test_next_open_upside_returns_net_of_friction(self):
        x=price_scenario(ev(),102,100,"up")
        self.assertTrue(x["price_eligible"])
        self.assertGreater(x["bounded_advantage_nextopen_pp"],1.0)
        self.assertLess(x["bounded_advantage_nextopen_pp"],2.0)

    def test_buy_limit_skips_unfavorable_gap(self):
        x=price_scenario(ev(nxt=102),110,100,"up")
        self.assertFalse(x["price_eligible"])
        self.assertEqual(x["bounded_advantage_nextopen_pp"],0)

    def test_missing_outcome_is_not_zero(self):
        self.assertIsNone(price_scenario(ev(),None,100,"down"))
        self.assertIsNone(price_scenario(ev(nxt=None),95,100,"down"))

    def test_bad_side_is_not_permitted(self):
        with self.assertRaises(ValueError):
            price_scenario(ev(),100,100,"short")

if __name__=="__main__":
    unittest.main()
