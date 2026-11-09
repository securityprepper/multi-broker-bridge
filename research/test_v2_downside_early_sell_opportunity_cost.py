"""V2 crash protection classification and non-fill tests, no broker I/O."""
import unittest
from datetime import datetime, date, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_downside_early_sell_opportunity_cost import (
    earliest, normalize_strict, normalize_breadth,normalize_flip,
    price_scenario,period_summary)

T=datetime(2026,11,9,8,30,tzinfo=ET)
def hit(dt=T,price=97.5,nxt=97.5,source="strict_premarket"):
    return {"asof":dt.isoformat(),"source":source,"signal_price":price,
            "next_bar_open":nxt,"total_pct":-2.5}

class Downtest(unittest.TestCase):
    def test_first_asof_no_future_ranking(self):
        a=hit(T+timedelta(minutes=5),source="breadth")
        b=hit(T,source="strict")
        self.assertEqual(earliest([a,b])["source"],"strict")

    def test_price_gapped_below_limit_not_filled(self):
        x=price_scenario(hit(nxt=96),100,90,98)
        self.assertFalse(x["eligible_price_proxy"])
        self.assertEqual(x["advantage_to_next_open_pp"],0)
        self.assertEqual(x["advantage_to_same_morning_open_pp"],0)

    def test_early_sale_benefit_with_realized_down_following_open(self):
        x=price_scenario(hit(nxt=97.5),100,92,95)
        self.assertTrue(x["eligible_price_proxy"])
        self.assertGreater(x["advantage_to_next_open_pp"],0)

    def test_early_sale_early_rebound_cost(self):
        x=price_scenario(hit(nxt=97.5),100,104,99)
        self.assertLess(x["advantage_to_next_open_pp"],0)
        self.assertLess(x["advantage_to_same_morning_open_pp"],0)

    def test_missing_open_is_unscorable_not_assumed(self):
        self.assertIsNone(price_scenario(hit(nxt=None),100,95))

    def test_normalize_breadth_snapshot(self):
        x=normalize_breadth({"asof":T.isoformat(),"observed_price":97.5,
                "next_bar_open":97.3},100)
        self.assertEqual(x["total_pct"],-2.5)
        self.assertEqual(x["source"],"sector_preopen")

    def test_normalize_flip_not_down_returns_none(self):
        self.assertIsNone(normalize_flip({"side":"up"}))

    def test_normalize_strict_includes_observation_time(self):
        start=T-timedelta(minutes=5)
        r=normalize_strict((T,"premarket",start,-.025),{start:[100,100,97.5,97.5,1],T:[97.3,97.4,97.2,97.3,1]})
        self.assertEqual(r["asof"],T.isoformat())
        self.assertEqual(r["next_bar_open"],97.3)

if __name__=="__main__":unittest.main()