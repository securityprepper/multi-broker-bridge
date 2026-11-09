"""As-of threshold replay regression tests; never place orders."""
import unittest
from datetime import datetime,time,timedelta
from zoneinfo import ZoneInfo
from v2_20261109_sector_shock_asof_future import (
    crossed,one_or_confirmed,forward,summarize,valid_regular,day_case,night_case,ET)

def tm(day,hr,minute):
    return datetime.fromisoformat(day+"T%02d:%02d:00"% (hr,minute)).replace(tzinfo=ET)
def regular(day,op=100.,close=100.,jumps=None):
    jumps=jumps or {}
    t=tm(day,9,35)
    out={}
    while t.time()<=time(16):
        c=jumps.get(t.time().strftime("%H:%M"),close)
        out[t]=(op if t.time()==time(9,35) else c,c,c,c)
        t+=timedelta(minutes=5)
    return out

class TestNoFutureLeakage(unittest.TestCase):
    def test_signed_threshold_inclusive(self):
        self.assertEqual(crossed(102,100,2),1)
        self.assertEqual(crossed(97,100,3),-1)
        self.assertEqual(crossed(101.99,100,2),0)
        self.assertEqual(crossed(100,100,2),0)
    def test_one_close_earliest_completed_bar(self):
        d="2026-10-20"
        t=tm(d,9,35)
        bars={t:101,t+timedelta(minutes=5):102,t+timedelta(minutes=10):104}
        e=one_or_confirmed(bars,100,2,"one_close")
        self.assertEqual(e[0],t+timedelta(minutes=5))
        self.assertEqual(e[1],102)
    def test_two_close_needs_consecutive_bars(self):
        d="2026-10-20";t=tm(d,9,35)
        a={t:102,t+timedelta(minutes=5):101.99,t+timedelta(minutes=10):102.6}
        self.assertIsNone(one_or_confirmed(a,100,2,"two_close"))
        a[t+timedelta(minutes=15)]=102.7
        self.assertEqual(one_or_confirmed(a,100,2,"two_close")[0],t+timedelta(minutes=15))
    def test_two_close_missing_bar_not_confirmed(self):
        d="2026-10-20";t=tm(d,9,35)
        self.assertIsNone(one_or_confirmed({t:103,t+timedelta(minutes=10):104},100,2,"two_close"))
    def test_own_direction_peer_breadth_asof_no_future(self):
        d="2026-10-20";t=tm(d,9,35)
        bars={t:102.4,t+timedelta(minutes=5):102.5,
              t+timedelta(minutes=10):102.6}
        up={t+timedelta(minutes=5):100.6}
        future={t+timedelta(minutes=15):100.7}
        still_down={t+timedelta(minutes=5):99.0}
        peers=[(up,100),(future,100),(still_down,100)]
        self.assertIsNone(one_or_confirmed(bars,100,2,"breadth",peers))
        # A later close cannot justify earlier signal; it can qualify at 09:45 only when another peer is present then.
        peers[2]=({t+timedelta(minutes=10):100.6},100)
        e=one_or_confirmed(bars,100,2,"breadth",peers)
        self.assertEqual(e[0],t+timedelta(minutes=10))
        self.assertEqual(e[2],1)
    def test_future_price_does_not_change_first_alert(self):
        d="2026-10-20";t=tm(d,9,35)
        before={t:102.5,t+timedelta(minutes=5):102.1}
        first=one_or_confirmed(before,100,2,"two_close")
        future=dict(before)
        future[t+timedelta(minutes=10)]=88
        future[t+timedelta(minutes=15)]=95
        self.assertEqual(first,one_or_confirmed(future,100,2,"two_close"))
    def test_day_opens_new_reference_even_if_prior_close_is_far(self):
        d="2026-10-21"
        etf={d:regular(d,110,110)}
        cases=day_case(etf,{},[d],d,2,"one_close")
        self.assertIsNone(cases)
    def test_night_prior_close_and_closed_bars_only(self):
        prior="2026-10-20";day="2026-10-21"
        etf={prior:regular(prior,100,100),day:regular(day,110,110)}
        t=tm(prior,16,5)
        etf[prior][t]=(102,103.4,101.9,103.4)
        e=night_case(etf,{},[prior,day],1,3,"one_close")
        self.assertEqual(e["origin"],100)
        self.assertEqual(e["signal_end"],t)
        self.assertAlmostEqual(e["forward"] if "forward" in e else e["price"],103.4)
    def test_forward_score_only_after_signal_not_prior_move(self):
        t=tm("2026-10-20",10,5)
        price=103
        event={"signal_end":t,"side":1,"price":price,
          "future_bars":{t+timedelta(minutes=15):102,t+timedelta(minutes=60):101,
                         tm("2026-10-20",13,30):102,tm("2026-10-20",16,0):102}}
        ret=forward(event,"day")
        self.assertLess(ret["1600"],0)
        self.assertLess(ret["15m"],0)
        self.assertLess(ret["60m"],0)
    def test_flat_never_counted_as_correct(self):
        t=tm("2026-10-20",10,5)
        e={"signal_end":t,"side":1,"forward":{"15m":0.0,"60m":None,"1330":0.0,"1440":0.02,"1600":0.02}}
        r=summarize([e],"2026-10-20","day")
        self.assertEqual(r["1600"]["correct"],0)
        self.assertEqual(r["1600"]["flat_under_005pp"],1)
    def test_night_missing_next_open_not_invented(self):
        t=tm("2026-10-20",16,5)
        e={"signal_end":t,"side":-1,"price":105,"next_open":None,"future_bars":{}}
        self.assertIsNone(forward(e,"night")["next_open"])
if __name__=="__main__":unittest.main()
