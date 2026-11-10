import unittest
from research import v2_nextbar_stop_risk_20261109 as m
def bars(first=100,loss_close=97,later_open=96,late_close=110,low=96):
 return {"SOXX":{"2026-11-09":{
  "09:50":(first,max(first,loss_close),min(first,low),loss_close),
  "09:55":(later_open,later_open,later_open,later_open),
  "14:35":(late_close,late_close,late_close,late_close)
 }}}
class RiskTests(unittest.TestCase):
 def test_nextbar_only_and_hard_flat(self):
  x=m.replay_one(bars(),"semiconductors",{"day":"2026-11-09","clock":"09:45","side":"UP"},stop_pct=2.5)
  self.assertTrue(x["stop_touched"])
  self.assertEqual(x["stop_event"]["execute_next_bar_start"],"09:55")
  self.assertEqual(x["exit_proxy"],96)
  self.assertGreater(x["flat_1340_CT_net_pct"],0)
  self.assertLess(x["nextbar_stop_net_pct"],0)
 def test_intrabar_low_alone_does_not_trigger(self):
  x=m.replay_one(bars(loss_close=100,later_open=100,late_close=110,low=93),
                "semiconductors",{"day":"2026-11-09","clock":"09:45","side":"UP"},stop_pct=2.5)
  self.assertFalse(x["stop_touched"])
  self.assertLessEqual(x["max_adverse_pct"],-7)
 def test_short_direction_stop(self):
  x=m.replay_one(bars(first=100,loss_close=104,later_open=105,late_close=95,low=100),
                "semiconductors",{"day":"2026-11-09","clock":"09:45","side":"DOWN"},stop_pct=2.5)
  self.assertTrue(x["stop_touched"])
  self.assertLess(x["nextbar_stop_net_pct"],0)
  self.assertGreater(x["flat_1340_CT_net_pct"],0)
 def test_missing_flat_mark_fails_closed(self):
  d=bars();d["SOXX"]["2026-11-09"].pop("14:35")
  x=m.replay_one(d,"semiconductors",{"day":"2026-11-09","clock":"09:45","side":"UP"})
  self.assertFalse(x["data_available"])
 def test_missing_next_execution_mark_fails_closed(self):
  d=bars();d["SOXX"]["2026-11-09"].pop("09:55")
  x=m.replay_one(d,"semiconductors",{"day":"2026-11-09","clock":"09:45","side":"UP"})
  self.assertFalse(x["data_available"])
 def test_no_order_calls(self):
  self.assertFalse(hasattr(m,"submit_order"))
  self.assertFalse(hasattr(m,"paper_api"))
if __name__=="__main__":unittest.main()
