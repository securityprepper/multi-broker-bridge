"""V2 next-move tests: a forecast may not depend on an unknown future exit."""
import unittest
from collections import defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from research import v2_next_move_first_7sector_walkforward_20261109 as m
ET=ZoneInfo("America/New_York")
DAYS=["2026-01-02","2026-01-05","2026-01-06","2026-01-07","2026-01-08","2026-01-09"]
def candles(future=True,past_days=5,breadth_positive=True):
 c=defaultdict(lambda:defaultdict(dict))
 etf,peers=m.FILES["semiconductors"]
 for sym in (etf,)+peers:
  for d in DAYS[:past_days]:
   for i in range(78):
    dt=datetime.fromisoformat(d).replace(tzinfo=ET,hour=9,minute=30)+timedelta(minutes=5*i)
    c[sym][d][dt.strftime("%H:%M")]=(100,100,100,100)
  d=DAYS[-1]
  c[sym][d]["09:30"]=(100,100,100,100)
  c[sym][d]["09:35"]=(100.7,100.7,100.7,100.7)
  c[sym][d]["09:40"]=(101,101,101,101)
  if not breadth_positive and sym!="SOXX":
   c[sym][d]["09:35"]=(99.5,99.5,99.5,99.5)
   c[sym][d]["09:40"]=(99.5,99.5,99.5,99.5)
  if future:
   c[sym][d]["09:50"]=(101.2,101.2,101.2,101.2)
   c[sym][d]["10:45"]=(102,102,102,102)
   c[sym][d]["14:35"]=(102,102,102,102)
 return c
class TestSignals(unittest.TestCase):
 def test_only_five_completed_prior_sessions(self):
  self.assertEqual(m.make_rows(candles(past_days=4),"semiconductors"),[])
 def test_entry_lag_and_future_marks(self):
  rows=m.make_rows(candles(),"semiconductors")
  policy=(.5,.2,2,0,1.5,1)
  entries,n,empty=m.evaluate(rows,"semiconductors",policy)
  self.assertEqual(n,1)
  self.assertEqual(entries[0]["clock"],"09:45")
  self.assertEqual(entries[0]["p_entry"],101.2)
  self.assertIsNotNone(entries[0]["p_60"])
 def test_future_missing_does_not_cancel_signal(self):
  policy=(.5,.2,2,0,1.5,1)
  complete=m.evaluate(m.make_rows(candles(),"semiconductors"),"semiconductors",policy)[0]
  nofuture=m.evaluate(m.make_rows(candles(future=False),"semiconductors"),"semiconductors",policy)[0]
  self.assertEqual([v["clock"] for v in complete],[v["clock"] for v in nofuture])
  self.assertIsNone(nofuture[0]["p_entry"])
  self.assertIsNone(nofuture[0]["p_60"])
  self.assertEqual(m.stats(nofuture,1,0)["future_60m_unscored"],1)
 def test_peer_breadth_required(self):
  rows=m.make_rows(candles(breadth_positive=False),"semiconductors")
  self.assertEqual(m.evaluate(rows,"semiconductors",(.5,.2,2,0,1.5,1))[0],[])
 def test_directions_are_symmetric(self):
  rows=m.make_rows(candles(),"semiconductors")
  self.assertEqual(m.evaluate(rows,"semiconductors",(.5,.2,2,0,1.5,-1))[0],[])
 def test_max_extension_guard(self):
  rows=m.make_rows(candles(),"semiconductors")
  self.assertEqual(m.evaluate(rows,"semiconductors",(.5,.2,2,0,.6,1))[0],[])
 def test_qualification_uses_only_asof(self):
  rows=m.make_rows(candles(future=False),"semiconductors")
  w=rows[0]["windows"][-1]
  pol=(.5,.2,2,0,1.5,1)
  a=m.qualify(w,pol[-1],*pol[:-1],sector="semiconductors")
  w["p60"]=999999
  b=m.qualify(w,pol[-1],*pol[:-1],sector="semiconductors")
  self.assertEqual(a,b)
 def test_research_has_no_order_function(self):
  self.assertFalse(hasattr(m,"submit_order"))
  self.assertFalse(hasattr(m,"place_order"))
if __name__=="__main__": unittest.main()
