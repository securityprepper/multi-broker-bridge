"""Research-only regression tests for post-signal future 60 minute outcomes."""
import unittest
from collections import defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import v2_stock_weakness_future_60m_20261109 as m

ET=ZoneInfo("America/New_York")
def example(stop=96,start=100,later=97):
 cache=defaultdict(lambda:defaultdict(dict))
 z=datetime(2026,10,9,9,30,tzinfo=ET)
 data={z:(100,100,100,start),
       z+timedelta(minutes=60):(later,later,later,later)}
 cache["AMD"]["2026-10-09"]=data
 row={"symbol":"AMD","date":"2026-10-09"}
 trigger={"time":(z+timedelta(minutes=5)).isoformat(),"mark":start}
 return cache,row,trigger

class AsOfTests(unittest.TestCase):
 def test_forward_down_is_positive_sell_benefit(self):
  c,r,t=example(start=100,later=99)
  v=m.score_one(c,r,t)
  self.assertEqual(v["signed_sell_vs_hold_60m_pct"],1)
  self.assertTrue(v["outcome_60m_after_30bp_positive"])
 def test_forward_rebound_is_negative_sell_benefit(self):
  c,r,t=example(start=100,later=103)
  v=m.score_one(c,r,t)
  self.assertEqual(v["signed_sell_vs_hold_60m_pct"],-3)
  self.assertFalse(v["outcome_60m_after_30bp_positive"])
  self.assertTrue(v["forward_rebound_over_2pct"])
 def test_missing_future_is_unscored(self):
  c,r,t=example()
  c["AMD"]["2026-10-09"].pop(datetime(2026,10,9,10,30,tzinfo=ET))
  v=m.score_one(c,r,t)
  self.assertIsNone(v["signed_sell_vs_hold_60m_pct"])
  self.assertIsNone(v["outcome_60m_after_30bp_positive"])
 def test_late_signal_never_hypothetically_exited_after_flat(self):
  c,r,t=example()
  z=datetime(2026,10,9,14,40,tzinfo=ET)
  c["AMD"]["2026-10-09"][z-timedelta(minutes=5)]=(100,100,100,100)
  t={"time":z.isoformat(),"mark":100}
  v=m.score_one(c,r,t)
  self.assertIsNone(v["signed_sell_vs_hold_to1340CT_pct"])
 def test_no_order_capability(self):
  self.assertFalse(hasattr(m,"submit_order"))
  self.assertFalse(hasattr(m,"place_order"))

if __name__=="__main__":unittest.main()
