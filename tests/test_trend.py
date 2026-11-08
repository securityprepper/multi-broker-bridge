"""Deterministic 1-minute rising-high/low tests, including rejects and exits."""
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from multi_broker_bridge.trend import Bar,Holding,TrendMonitor

UTC=timezone.utc
BASE=datetime(2026,11,6,14,59,tzinfo=UTC)  # Nov 6 at 08:59 America/Chicago

def b(symbol,i,high=None,low=None,close=None):
    d=Decimal
    hi=d(str(high)) if high is not None else d(101+i)
    lo=d(str(low)) if low is not None else d(99+i)
    cl=d(str(close)) if close is not None else d(100+i)
    return Bar(symbol,BASE+timedelta(minutes=i),hi,lo,cl,
               cl-d("0.10"),cl+d("0.10"))

def loaded(sectors=None):
    m=TrendMonitor(sectors or {"semiconductors":("AMD","MU","SNDK")})
    for i in range(4):
        for ticker in ("AMD","MU","SNDK"):
            m.add(b(ticker,i))
    return m

class TrendTests(unittest.TestCase):
    def test_three_higher_highs_lows_and_breadth(self):
        m=loaded()
        result=m.scan(BASE+timedelta(minutes=3,seconds=15),executable_session=True)
        buys=[x for x in result if x["action"]=="BUY_LIMIT_CANDIDATE"]
        self.assertEqual({x["symbol"] for x in buys},{"AMD","MU","SNDK"})
        self.assertTrue(all(x["rising_breadth"]==1 for x in buys))
        self.assertEqual([x["symbol"] for x in result if x["action"]=="ETF_ALTERNATIVE_WATCH"],["SOXX"])
    def test_one_actionable_entry_per_symbol_per_day(self):
        m=loaded()
        now=BASE+timedelta(minutes=3,seconds=5)
        first=m.scan(now,executable_session=True)
        second=m.scan(now+timedelta(seconds=15),executable_session=True)
        first_ids={x["symbol"] for x in first if x["action"]=="BUY_LIMIT_CANDIDATE"}
        second_ids={x["symbol"] for x in second if x["action"]=="BUY_LIMIT_CANDIDATE"}
        self.assertEqual(first_ids,{"AMD","MU","SNDK"})
        self.assertEqual(second_ids,set())
    def test_no_live_broker_calls_when_only_bars_are_fed(self):
        m=loaded()
        result=m.scan(BASE+timedelta(minutes=3,seconds=15),executable_session=False)
        self.assertTrue(all(x["action"] in ("BUY_WATCH","ETF_ALTERNATIVE_WATCH") for x in result))
    def test_spike_blocks_entry(self):
        m=TrendMonitor({"semiconductors":("AMD","MU","SNDK")})
        for i in range(4):
            for ticker in ("AMD","MU","SNDK"):
                if ticker=="AMD" and i>=2:
                    m.add(b(ticker,i,high=112+i,low=110+i,close=111+i))
                else:m.add(b(ticker,i))
        result=m.scan(BASE+timedelta(minutes=3,seconds=10))
        self.assertNotIn("AMD",{x["symbol"] for x in result if x["action"]=="BUY_WATCH"})
    def test_insufficient_fresh_sector_breadth_blocks(self):
        m=TrendMonitor({"semiconductors":("AMD","MU","SNDK","WDC","NVDA","AVGO","INTC","TSM")})
        for i in range(4):
            for ticker in ("AMD","MU","SNDK"):
                m.add(b(ticker,i))
        self.assertFalse(m.breadth("semiconductors",BASE+timedelta(minutes=3))["qualified"])
    def test_stale_price_blocks_fresh_entry(self):
        m=loaded()
        result=m.scan(BASE+timedelta(minutes=10))
        self.assertFalse(any(x["action"]=="BUY_WATCH" for x in result))
    def test_dip_reversal_generates_software_limit_exit_candidate(self):
        m=TrendMonitor({"semiconductors":("AMD","MU","SNDK")})
        for i,(hi,lo,cl) in enumerate(((110,108,109),(109,107,108),(108,106,107))):
            m.add(b("AMD",i,hi,lo,cl))
        hold={"AMD":Holding("AMD",4,Decimal("105"),Decimal("110"))}
        result=m.scan(BASE+timedelta(minutes=2,seconds=5),hold,executable_session=True)
        self.assertEqual(result[0]["action"],"SELL_LIMIT_CANDIDATE")
        self.assertEqual(result[0]["quantity"],4)
        self.assertIsNotNone(result[0]["reference_bid"])
    def test_feed_stale_warns_software_stop_wont_work(self):
        m=TrendMonitor({"semiconductors":("AMD","MU","SNDK")})
        m.add(b("AMD",0))
        result=m.scan(BASE+timedelta(minutes=6),{"AMD":Holding("AMD",1,Decimal("100"),Decimal("100"))})
        self.assertEqual(result[0]["action"],"FEED_STALE_HOLDING")
    def test_exit_by_155pm_chicago_no_more_entries(self):
        base=datetime(2026,11,6,19,54,tzinfo=UTC)  # 13:54 CT
        m=TrendMonitor({"semiconductors":("AMD","MU","SNDK")})
        for i in range(4):
            for ticker in ("AMD","MU","SNDK"):
                m.add(Bar(ticker,base+timedelta(minutes=i),
                          Decimal(101+i),Decimal(99+i),Decimal(100+i),
                          Decimal("102.90"),Decimal("103.10")))
        result=m.scan(base+timedelta(minutes=3,seconds=5),
                      {"AMD":Holding("AMD",1,Decimal("100"),Decimal("104"))},
                      executable_session=True)
        self.assertTrue(any(x["action"]=="SELL_LIMIT_CANDIDATE" and "2 PM" in x["reason"] for x in result))
        self.assertFalse(any(x["action"]=="BUY_LIMIT_CANDIDATE" for x in result))

if __name__=="__main__":unittest.main()
