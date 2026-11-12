"""Research regression: minor two-bar RTH declines never directly submit PAPER sell candidates.
No broker calls. Run against isolated V2 and independently against installed PAPER path.
"""
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from multi_broker_bridge.trend import TrendMonitor, Holding, Bar
CT=ZoneInfo("America/Chicago")

def decimal(v): return Decimal(str(v))

def scan(prices,local_time="10:04:40",entry="100",highest="100",has_bid=True, executable=True):
    hh,mm,ss=map(int,local_time.split(":"))
    today=datetime(2026,11,12,hh,mm,ss,tzinfo=CT)
    mon=TrendMonitor(sectors={})
    for i,(high,low,close) in enumerate(prices):
        when=today.replace(second=0,microsecond=0)-timedelta(minutes=len(prices)-1-i)
        mon.add(Bar("AMD",when.astimezone(timezone.utc),decimal(high),decimal(low),decimal(close),
                    bid=decimal(low) if has_bid else None,ask=decimal(high) if has_bid else None))
    holding=Holding("AMD",1,decimal(entry),decimal(highest))
    return mon.scan(today.astimezone(timezone.utc),{"AMD":holding},executable_session=executable)

DESCENDING=[
    ("100.02","99.96","99.98"),
    ("100.00","99.93","99.95"),
    ("99.99","99.90","99.92"),
]

class RthAntiChurn(unittest.TestCase):
    def test_two_falling_bars_alone_cannot_sell_tiny_loss(self):
        self.assertEqual(scan(DESCENDING),[])
    def test_two_falling_bars_alone_cannot_sell_modest_profit(self):
        p=[("100.70","100.40","100.55"),
           ("100.68","100.35","100.50"),
           ("100.65","100.32","100.40")]
        self.assertEqual(scan(p,entry="100",highest="100.7"),[])
    def test_loss_at_or_below_one_percent_remains_authorized(self):
        r=scan([("99.1","98.95","99"),("99.02","98.92","98.99"),("99.01","98.9","98.91")])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["reason"],"loss threshold reached")
        self.assertEqual(r[0]["action"],"SELL_LIMIT_CANDIDATE")
    def test_profit_at_one_percent_remains_authorized(self):
        r=scan([("101.01","100.95","101"),("101.03","100.94","101"),("101.05","100.93","101")])
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["reason"],"profit target reached")
    def test_existing_peak_reversal_remains_active(self):
        r=scan([("100.4","100.1","100.2"),("100.25","100.05","100.15"),("100.2","99.9","100")],highest="100.9")
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["reason"],"trailing peak reversal")
    def test_1340_flat_remains_mandatory(self):
        r=scan(DESCENDING,local_time="13:40:40")
        self.assertEqual(len(r),1)
        self.assertIn("mandatory exit",r[0]["reason"])
    def test_no_executable_price_becomes_watch_not_order(self):
        r=scan([("101.01","100.95","101"),("101.03","100.94","101"),("101.05","100.93","101")],has_bid=False)
        self.assertEqual(r[0]["action"],"EXIT_WATCH")
    def test_non_executable_session_becomes_watch_not_order(self):
        r=scan([("101.01","100.95","101"),("101.03","100.94","101"),("101.05","100.93","101")],executable=False)
        self.assertEqual(r[0]["action"],"EXIT_WATCH")
    def test_stale_bars_never_assert_software_stop(self):
        r=scan(DESCENDING,local_time="10:04:40")
        self.assertEqual(r,[])
    def test_no_broker_order_interface_in_pure_trend_monitor(self):
        self.assertFalse(hasattr(TrendMonitor,"paper_api"))
        self.assertFalse(hasattr(TrendMonitor,"place_order"))

if __name__=="__main__": unittest.main()
