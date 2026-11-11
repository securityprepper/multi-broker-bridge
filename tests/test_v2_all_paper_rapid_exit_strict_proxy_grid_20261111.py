import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from research import v2_all_paper_rapid_exit_strict_proxy_grid_20261111 as replay
CT=ZoneInfo("America/Chicago")
DAY="2026-11-11"
def bar(hm,op,hi,lo,cl):
 ts=datetime.fromisoformat(DAY+"T"+hm+":00-06:00").astimezone(timezone.utc)
 return {"t":ts.isoformat(),"o":op,"h":hi,"l":lo,"c":cl,"v":100}
def trade():
 return {"day":DAY,"symbol":"AAA","source":"MBB",
         "entry_at":DAY+"T13:36:40-06:00","exit_at":DAY+"T13:37:42-06:00",
         "entry":100.,"exit":99.,"qty":4.}
def simple(a=None,b=None,c=None):
 return {DAY+"|AAA":[
    bar("13:36",100,110,80,100),
    a or bar("13:37",100,100.1,99.9,100),
    b or bar("13:38",100,100.1,99.9,100),
    c or bar("13:39",100,100.1,99.9,100)]}
class ReplayIntegrity(unittest.TestCase):
 def test_entry_containing_bar_never_used_to_trigger(self):
  x=replay.outcome(trade(),simple(),1,1,0)
  self.assertEqual(x["status"],"PRICE_MARK_PROXY")
  self.assertEqual(x["why"],"FORCED_FLAT_MARK")
 def test_stop_first_on_ambiguous_candle_with_next_open_execution(self):
  a=bar("13:37",100,102,98.9,100)
  b=bar("13:38",98.8,99,98,98.7)
  x=replay.outcome(trade(),simple(a=a,b=b),1,1,0)
  self.assertEqual(x["why"],"STOP_FIRST")
  self.assertTrue(x["ambiguous_both_intrabar"])
  self.assertEqual(x["exit_mark"],98.8)
  self.assertEqual(x["mark_at_CT"],DAY+"T13:38:00-06:00")
 def test_emergency_overrides_thirty_minimum_hold(self):
  a=bar("13:37",100,100,97.2,97.4)
  x=replay.outcome(trade(),simple(a=a),1,1,30)
  self.assertEqual(x["why"],"EMERGENCY_2_5")
 def test_minimum_hold_does_not_use_pre_eligibility_high_low(self):
  a=bar("13:37",100,101.8,99.9,101.3)
  x=replay.outcome(trade(),simple(a=a),1,2,30)
  self.assertEqual(x["why"],"FORCED_FLAT_MARK")
 def test_one_missing_1m_bar_is_not_accepted(self):
  z=simple()
  z[DAY+"|AAA"].pop(2)
  x=replay.outcome(trade(),z,1,1,0)
  self.assertEqual(x["status"],"UNKNOWN_PATH")
  self.assertEqual(x["quality"],"MISSING_INTRA_SESSION_MINUTE")
 def test_flat_missing_does_not_invent_return(self):
  z=simple()
  z[DAY+"|AAA"].pop(-1)
  x=replay.outcome(trade(),z,1,1,0)
  self.assertEqual(x["status"],"UNKNOWN_PATH")
 def test_malformed_no_after_entry_bars(self):
  z={DAY+"|AAA":[bar("13:36",100,110,80,100)]}
  x=replay.outcome(trade(),z,1,1,0)
  self.assertEqual(x["status"],"UNKNOWN_PATH")
if __name__=="__main__":unittest.main()
