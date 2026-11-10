"""Regression tests for V2 high-threshold serious-loss recall (NO BROKER CONNECTION)."""
import unittest
from collections import defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import v2_sector_alert_severe_stock_recall_20261109 as m

ET=ZoneInfo("America/New_York")
def bars(points,day="2026-10-01"):
 b={}
 z=datetime.fromisoformat(day+"T09:30:00").replace(tzinfo=ET)
 for i,px in enumerate(points):
  t=z+timedelta(minutes=5*i)
  b[t]=(px,px,px,px)
 return b
def mock_cache(etfs=[100,105.5,105.5],peerprices=[[100,102,102],[100,102,102],[100,102,102]],symbol="SOXX"):
 x=defaultdict(lambda:defaultdict(dict))
 for s,values in [(symbol,etfs)]+list(zip(("AMD","MU","NVDA"),peerprices)):
  x[s]["2026-10-01"]=bars(values)
 return x

class ResearchTests(unittest.TestCase):
 def test_overlap_exact_2p5_total_includes_one_pp_last15(self):
  b=bars([98.5,98.5,98.5,97.5])
  total,strict=m.stock_weakness_day(b,100)
  self.assertIsNotNone(strict)
  self.assertEqual(strict["total_from_previous_close_pct"],-2.5)
  self.assertEqual(strict["last15_change_pp"],-1.0)
  self.assertEqual(strict["time"][11:16],"09:50")
 def test_slow_decline_cannot_fake_momentum(self):
  b=bars([98.0,97.9,97.8,97.5])
  total,strict=m.stock_weakness_day(b,100)
  self.assertIsNotNone(total)
  self.assertIsNone(strict)
 def test_single_completed_close_not_enough(self):
  d=mock_cache(etfs=[100,100,106])
  self.assertEqual(m.sector_shock_day(d,"semiconductors","2026-10-01",5),{})
 def test_two_completed_closes_and_breadth(self):
  d=mock_cache(etfs=[100,106,106],peerprices=[[100,102,102],[100,102,102],[100,102,102]])
  sig=m.sector_shock_day(d,"semiconductors","2026-10-01",5)
  self.assertIn(1,sig)
  self.assertEqual(sig[1]["time"][11:16],"09:45")
  self.assertEqual(sig[1]["qualified_peer_count"],3)
 def test_breadth_rejects_isolated_etf(self):
  d=mock_cache(etfs=[100,106,106],peerprices=[[100,100,100],[100,102,102],[100,100,100]])
  self.assertEqual(m.sector_shock_day(d,"semiconductors","2026-10-01",5),{})
 def test_no_future_bar_needed_for_signal(self):
  d=mock_cache(etfs=[100,106,106])
  sig=m.sector_shock_day(d,"semiconductors","2026-10-01",5)
  d["SOXX"]["2026-10-01"].update(bars([110,110,110],"2026-10-02"))
  self.assertEqual(sig,m.sector_shock_day(d,"semiconductors","2026-10-01",5))
 def test_down_sign_is_symmetric(self):
  d=mock_cache(etfs=[100,94,94],peerprices=[[100,98,98],[100,98,98],[100,98,98]])
  sig=m.sector_shock_day(d,"semiconductors","2026-10-01",5)
  self.assertIn(-1,sig)
  self.assertNotIn(1,sig)
 def test_no_order_writes(self):
  self.assertFalse(hasattr(m,"place_order"))
  self.assertFalse(hasattr(m,"submit_order"))

if __name__=="__main__":unittest.main()
