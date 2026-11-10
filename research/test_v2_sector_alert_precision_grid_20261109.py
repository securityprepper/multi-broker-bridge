import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
from research import v2_sector_alert_precision_grid_20261109 as m

ET=ZoneInfo("America/New_York")
PRIOR=("2026-10-01","2026-10-02","2026-10-05","2026-10-06","2026-10-07")
TODAY="2026-10-08"

def cache_with_today(future=True,strong_two_bars=True,days=PRIOR):
    d=defaultdict(lambda:defaultdict(dict))
    etf,peers=m.SECTOR["semiconductors"]
    for sym in (etf,)+peers:
        for date in days:
            z=datetime.fromisoformat(date).replace(tzinfo=ET,hour=9,minute=30)
            for i in range(78):
                d[sym][date][z+timedelta(minutes=5*i)]=(100,100,100,100)
        z=datetime.fromisoformat(TODAY).replace(tzinfo=ET,hour=9,minute=30)
        d[sym][TODAY][z]=(100,100,100,100)
        px=(106 if sym==etf else 102)
        if strong_two_bars:
            d[sym][TODAY][z+timedelta(minutes=5)]=(px,px,px,px)
        else:
            d[sym][TODAY][z+timedelta(minutes=5)]=(101,101,101,101)
        px2=(106.5 if sym==etf else 102)
        d[sym][TODAY][z+timedelta(minutes=10)]=(px2,px2,px2,px2)
        if future:
            later=z+timedelta(minutes=70)
            d[sym][TODAY][later]=(110,110,110,110)
    return d

class TestPrecisionGrid(unittest.TestCase):
    def test_day_snapshot_does_not_require_future_close(self):
        d=cache_with_today(future=False)
        etf,peers=m.SECTOR["semiconductors"]
        self.assertIsNotNone(m.compute_day_snapshot(d,(etf,)+peers,TODAY))
    def test_requires_five_completed_prior_sessions(self):
        d=cache_with_today(days=PRIOR[:4])
        self.assertEqual(m.day_signals("semiconductors",d,5),[])
    def test_signal_with_two_bars_and_breadth(self):
        d=cache_with_today()
        rows=m.day_signals("semiconductors",d,5)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["event"]["signal_at_ET"],"09:45")
        self.assertGreater(rows[0]["event"]["signed_forward_60m_pct"],0)
    def test_no_signal_from_single_bar_above_cutoff(self):
        d=cache_with_today(strong_two_bars=False)
        self.assertIsNone(m.day_signals("semiconductors",d,5)[0]["event"])
    def test_future_bar_does_not_change_signal(self):
        now=m.day_signals("semiconductors",cache_with_today(future=False),5)
        late=m.day_signals("semiconductors",cache_with_today(future=True),5)
        self.assertEqual(now[0]["event"]["signal_at_ET"],late[0]["event"]["signal_at_ET"])
        self.assertIsNone(now[0]["event"]["forward_60m_price"])
        self.assertEqual(m.summary(now,5)["unscored_future_data"],1)
    def test_no_broker_order_capability(self):
        self.assertFalse(hasattr(m,"submit_order"))
        self.assertFalse(hasattr(m,"place_order"))
if __name__=="__main__":unittest.main()
