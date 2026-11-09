"""Causality checks for isolated V2 filters; NO market/broker access."""
import unittest
from datetime import datetime,timedelta,timezone
from research.v2_causal_entry_sell_confirm import (
    observed_close,five_minute_move,has_upside_filter,confirmed_five_minute, prior_close_asof
)

T=datetime(2026,11,9,15,0,tzinfo=timezone.utc)
B=lambda c:(float(c),float(c),float(c),float(c),100)

class AsOfTwoTrackTests(unittest.TestCase):
    def test_previous_close_cannot_be_same_day(self):
        from datetime import date
        p=date(2026,11,6)
        day=date(2026,11,9)
        closes={"MU":{p:100,day:80}}
        self.assertEqual(prior_close_asof(closes,"MU",p,day),100)
        self.assertIsNone(prior_close_asof(closes,"MU",None,day))
        with self.assertRaises(ValueError):
            prior_close_asof(closes,"MU",day,day)
        with self.assertRaises(ValueError):
            prior_close_asof(closes,"MU",date(2026,11,10),day)
    def test_only_completed_candle_may_be_used(self):
        bars={"SOXX":{T-timedelta(minutes=5):B(95),
                      T:B(999),T-timedelta(minutes=10):B(95.2)}}
        self.assertEqual(observed_close(bars,"SOXX",T),95)
        self.assertAlmostEqual(five_minute_move(bars,"SOXX",T,100),-.2)
    def test_future_bars_cannot_change_signal(self):
        bars={"MU":{T-timedelta(minutes=5):B(97),
                    T-timedelta(minutes=10):B(97.3)}}
        old=five_minute_move(bars,"MU",T,100)
        bars["MU"][T]=B(900)
        self.assertEqual(old,five_minute_move(bars,"MU",T,100))
    def test_missing_history_rejects_nonbaseline(self):
        for filter_name in ("sector_5m","stock_sector_5m",
                            "sector_5m_020","no_weak_prior5",
                            "sector_5m_no_weak_prior5"):
            self.assertFalse(has_upside_filter(filter_name,None,None,None))
        self.assertTrue(has_upside_filter("baseline",None,None,None))
    def test_filter_boundaries(self):
        self.assertTrue(has_upside_filter("sector_5m",0,-.3,-10))
        self.assertFalse(has_upside_filter("stock_sector_5m",0,-.3,2))
        self.assertTrue(has_upside_filter("stock_sector_5m",0,0,-10))
        self.assertTrue(has_upside_filter("sector_5m_020",.2,0,0))
        self.assertFalse(has_upside_filter("sector_5m_020",.19,0,0))
        self.assertFalse(has_upside_filter("no_weak_prior5",0,0,-5))
        self.assertTrue(has_upside_filter("no_weak_prior5",0,0,-4.999))
    def test_following_5min_completed_first(self):
        self.assertTrue(confirmed_five_minute("stock_down_010",B(97.40),97.5,100,100))
        self.assertFalse(confirmed_five_minute("stock_down_010",B(97.41),97.5,100,100))
        self.assertFalse(confirmed_five_minute("stock_down_010",None,97.5,100,100))
    def test_sector_confirmation_not_from_future(self):
        aug=(99,99,99,99,99.2)
        self.assertTrue(confirmed_five_minute("sector_down_000",B(97.5),97.5,100,100,aug,99.2))
        aug=(99,99,99,99,98.8)
        self.assertFalse(confirmed_five_minute("sector_down_000",B(97.5),97.5,100,100,aug,98.8))
        self.assertFalse(confirmed_five_minute("stock_sector_down_010",B(97.3),97.5,100,100,aug,98.8))
        aug=(99,99,99,99,99.2)
        self.assertTrue(confirmed_five_minute("stock_sector_down_010",B(97.3),97.5,100,100,aug,99.2))
    def test_unknown_variants_fail_closed(self):
        with self.assertRaises(ValueError):has_upside_filter("retrospective",0,0,0)
        with self.assertRaises(ValueError):confirmed_five_minute("retrospective",B(1),1,1,1)
    def test_solely_causal_upside_filters(self):
        self.assertTrue(has_upside_filter("sector_5m_no_weak_prior5",.1,-9,-4.99))
        self.assertFalse(has_upside_filter("sector_5m_no_weak_prior5",-.1,-9,-4.99))
        self.assertFalse(has_upside_filter("sector_5m_no_weak_prior5",.1,-9,-5.1))
if __name__=="__main__":unittest.main()