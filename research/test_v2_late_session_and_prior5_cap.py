"""Tests of V2 late-session causal observation and prior-five selection rules."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_late_session_and_prior5_cap import (
    late_context, qualifies, late_first, first_of, prior_five_return, cap_allowed
)

D=date(2026,11,9)
def dt(hour,minute):return datetime.combine(D,time(hour,minute),ET)

def bars():
    base={
        dt(9,30):[100,101,99,100,100],
        dt(10,15):[99,99,98.5,98.5,100],
        dt(10,30):[98,98.5,96.9,97,100],
        dt(10,35):[97,97.3,96.7,96.8,100],
    }
    others={p:{dt(10,30):[100,101,98,98.5,100]} for p in ("AMD","MU","NVDA","SNDK","WDC")}
    others["WDC"]=base
    others["SOXX"]={dt(10,30):[100,101,98,98.5,100]}
    return others

def prevs():
    return {p:100 for p in ("AMD","MU","NVDA","SNDK","WDC","SOXX")}

class LateSignalTests(unittest.TestCase):
    def test_timestamps_completed_bar_only(self):
        b=bars()
        at=dt(10,35)
        c=late_context(b,D,"WDC",at,prevs())
        self.assertEqual(c["signal_price"],97)
        b["WDC"][at][3]=20
        self.assertEqual(late_context(b,D,"WDC",at,prevs())["signal_price"],97)

    def test_strict_overlapping_threshold(self):
        c=late_context(bars(),D,"WDC",dt(10,35),prevs())
        self.assertTrue(qualifies("late_strict",c))
        self.assertAlmostEqual(c["total_pct"],-3)
        self.assertAlmostEqual(c["last15_pp"],-1.5)

    def test_open_relative_reversal(self):
        self.assertTrue(qualifies("late_open_1p5",late_context(
            bars(),D,"WDC",dt(10,35),prevs())))

    def test_sector_breadth_uses_completed_peers(self):
        b=bars()
        c=late_context(b,D,"WDC",dt(10,35),prevs())
        self.assertTrue(qualifies("late_sector_breadth",c))
        for sym in ("AMD","MU","NVDA","SNDK"):
            b[sym][dt(10,30)][3]=100
        self.assertFalse(qualifies("late_sector_breadth",late_context(
            b,D,"WDC",dt(10,35),prevs())))

    def test_pre_window_rejected(self):
        self.assertIsNone(late_context(bars(),D,"WDC",dt(10,30),prevs()))
        self.assertIsNone(late_context(bars(),D,"WDC",dt(16,0),prevs()))

    def test_nextbar_is_scoring_only(self):
        b=bars()
        r=late_first(b,D,"WDC",prevs(),"late_strict")
        self.assertEqual(r["asof"],dt(10,35).isoformat())
        self.assertEqual(r["next_bar_open"],97)
        b["WDC"][dt(10,35)][0]=50
        r2=late_first(b,D,"WDC",prevs(),"late_strict")
        self.assertEqual(r2["asof"],r["asof"])
        self.assertEqual(r2["signal_price"],r["signal_price"])

    def test_missing_past_no_strict(self):
        b=bars()
        del b["WDC"][dt(10,15)]
        c=late_context(b,D,"WDC",dt(10,35),prevs())
        self.assertIsNone(c["last15_pp"])
        self.assertFalse(qualifies("late_strict",c))

    def test_invalid_reference_fails_closed(self):
        p=prevs();del p["SOXX"]
        self.assertIsNone(late_context(bars(),D,"WDC",dt(10,35),p))

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            late_context(bars(),D,"WDC",datetime(2026,11,9,10,35),prevs())

    def test_unknown_rules_rejected(self):
        with self.assertRaises(ValueError):qualifies("invalid",{})
        with self.assertRaises(ValueError):cap_allowed("invalid",0,0)

    def test_first_of_chronology(self):
        a={"asof":dt(10,50).isoformat(),"source":"a"}
        b={"asof":dt(10,35).isoformat(),"source":"b"}
        self.assertEqual(first_of(None,a,b),b)

    def test_previous_five_only(self):
        days=[date(2026,10,1)+timedelta(days=i) for i in range(8)]
        closes={"WDC":{days[i]:100+2*i for i in range(8)}}
        self.assertIsNone(prior_five_return(closes,days,5,"WDC"))
        self.assertAlmostEqual(prior_five_return(closes,days,6,"WDC"),10)
        closes["WDC"][days[6]]=999
        self.assertAlmostEqual(prior_five_return(closes,days,6,"WDC"),10)

    def test_missing_complete_session_fails_closed(self):
        days=[date(2026,10,1)+timedelta(days=i) for i in range(7)]
        self.assertIsNone(prior_five_return({"WDC":{days[0]:100}},days,6,"WDC"))
        missing_mid={days[i]:100+i for i in (0,1,3,4,5)}
        self.assertIsNone(prior_five_return({"WDC":missing_mid},days,6,"WDC"))

    def test_cap_no_future_fallback(self):
        self.assertTrue(cap_allowed("first_only",None,None))
        self.assertFalse(cap_allowed("first_both_positive_p5",None,10))
        self.assertTrue(cap_allowed("first_both_positive_p5",0,0))
        self.assertFalse(cap_allowed("first_no_weak_stock_p5",-5,20))
        self.assertFalse(cap_allowed("first_stock_positive_p5",-0.1,20))

if __name__=="__main__":unittest.main()