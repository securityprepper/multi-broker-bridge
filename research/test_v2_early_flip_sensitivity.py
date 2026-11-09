"""Tests that early flip thresholds are causal, complete-bar and two-sided."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_early_flip_sensitivity import (
    ETF, PEERS, VARIANTS, point_in_time_returns, direction_from_anchor,
    qualifying_flip, first_flip, prior5_return, price_mark14)

TODAY = date(2026, 11, 9)
PRIOR = date(2026, 11, 6)

def sample(symbols=None, pre=101.0, now=100.4, at=time(9, 30)):
    symbols = symbols or (*PEERS, ETF)
    bars = {}
    closes = {}
    for sym in symbols:
        bars[sym] = {
            datetime.combine(TODAY, time(9, 10), ET): [pre]*4+[100],
            datetime.combine(TODAY, at, ET): [now]*4+[100],
        }
        closes[sym] = {PRIOR: 100.0}
    return bars, closes

class EarlyFlipTest(unittest.TestCase):
    def test_preopen_valid_and_two_sided(self):
        bars, closes = sample()
        pre = point_in_time_returns(bars, closes, PRIOR, TODAY, time(9, 10))
        self.assertEqual(direction_from_anchor(pre), 1)
        now = point_in_time_returns(bars, closes, PRIOR, TODAY, time(9, 30))
        self.assertEqual(qualifying_flip(pre, now, "MU", VARIANTS["early_050"])[0],"down")
        self.assertIsNone(qualifying_flip(pre, now, "MU", VARIANTS["base_100"]))

    def test_exact_thresholds(self):
        pre = {s: 1.0 for s in (*PEERS, ETF)}
        now = {s: 0.5 for s in (*PEERS, ETF)}
        self.assertEqual(qualifying_flip(pre, now, "MU", VARIANTS["early_050"])[0], "down")
        now["MU"] = 0.51
        self.assertIsNone(qualifying_flip(pre, now, "MU", VARIANTS["early_050"]))

    def test_first_asof_does_not_use_next_bar(self):
        bars, closes = sample()
        event = first_flip(bars, closes, "MU", PRIOR, TODAY, VARIANTS["early_050"])
        self.assertEqual(event["at"][11:16],"09:35")
        self.assertIsNone(event["next_bar_open"])
        bars["MU"][datetime.combine(TODAY,time(9,35),ET)] = [101,101,101,90,100]
        event2 = first_flip(bars,closes,"MU",PRIOR,TODAY,VARIANTS["early_050"],
                           cutoff=time(9,35))
        self.assertEqual(event2["price"],100.4)

    def test_future_bar_cannot_be_used_early(self):
        bars, closes = sample(pre=101.0, now=101.0)
        for sym in (*PEERS,ETF):
            bars[sym][datetime.combine(TODAY,time(9,35),ET)] = [100,100,100,100,100]
        self.assertIsNone(first_flip(bars,closes,"MU",PRIOR,TODAY,
                                     VARIANTS["early_050"],cutoff=time(9,35)))
        self.assertEqual(first_flip(bars,closes,"MU",PRIOR,TODAY,
                                     VARIANTS["early_050"])["at"][11:16],"09:40")

    def test_missing_peer_fails_closed(self):
        bars,closes=sample()
        del bars["AMD"][datetime.combine(TODAY,time(9,30),ET)]
        self.assertIsNone(first_flip(bars,closes,"MU",PRIOR,TODAY,VARIANTS["early_050"]))

    def test_missing_prior_close_fails_closed(self):
        bars,closes=sample()
        del closes["AVGO"][PRIOR]
        self.assertIsNone(first_flip(bars,closes,"MU",PRIOR,TODAY,VARIANTS["early_050"]))

    def test_no_broad_preopen_no_event(self):
        bars,closes=sample(pre=100.1)
        self.assertIsNone(first_flip(bars,closes,"MU",PRIOR,TODAY,VARIANTS["early_050"]))

    def test_symmetric_up_flip(self):
        bars,closes=sample(pre=99.0,now=99.6)
        self.assertEqual(first_flip(bars,closes,"MU",PRIOR,TODAY,
                                    VARIANTS["early_050"])["side"],"up")

    def test_require_majority_peer_confirmation(self):
        pre={s:1.0 for s in (*PEERS,ETF)}
        curr={s:1.0 for s in (*PEERS,ETF)}
        curr["SOXX"]=0.4
        curr["MU"]=0.4
        for sym in ("AMD","NVDA","WDC"):
            curr[sym]=0.4
        self.assertIsNone(qualifying_flip(pre,curr,"MU",VARIANTS["early_050"]))

    def test_pre_anchor_is_fixed_to_0910(self):
        bars,closes=sample()
        del bars["MU"][datetime.combine(TODAY,time(9,10),ET)]
        self.assertIsNone(first_flip(bars,closes,"MU",PRIOR,TODAY,VARIANTS["early_050"]))

    def test_prior_five_uses_only_previous_completed_sessions(self):
        from datetime import timedelta
        dates=[date(2026,10,28)+timedelta(days=i) for i in range(7)]
        closes={"SOXX": {d: 100+i for i,d in enumerate(dates)}}
        self.assertIsNone(prior5_return(closes,dates,5))
        self.assertAlmostEqual(prior5_return(closes,dates,6),5.0)
        closes["SOXX"][dates[6]]=5000
        self.assertAlmostEqual(prior5_return(closes,dates,6),5.0)

    def test_zero_fill_when_limit_ineligible(self):
        event={"side":"down","price":100.0,"next_bar_open":99.0}
        score=price_mark14(event,90.0,100.0)
        self.assertEqual(score["bounded_advantage_14_pp"],0.0)
        self.assertFalse(score["price_eligible"])

if __name__ == "__main__":
    unittest.main()