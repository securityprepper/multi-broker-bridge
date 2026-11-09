"""No-future-leak regression checks for research-only cross-sector policy."""
import unittest
from datetime import datetime,timedelta
from research import v2_cross_sector_confirmed_walkforward as v
from research import v2_gold_miner_preopen_lead as g
class SectorTests(unittest.TestCase):
 def f(self,p,mean=.4,prior=1,recent=0,rth=.5):
  return {"pct":p,"mean_abs_prior4":mean,"prior5_trend":prior,
          "recent15":recent,"rth_from_open":rth}
 def make(self,values=(.5,.6,.7),mean=.4):
  return {s:self.f(x,mean=mean) for s,x in zip(("XLE","XOM","CVX"),values)}
 def test_breadth_not_sector_alone(self):
  f=self.make((.5,.6,-.7))
  self.assertTrue(v.signal(f,("XLE","XOM","CVX"),"sector_only","09:25",1))
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"breadth","09:25",1))
 def test_short_and_long_signs(self):
  f=self.make((-.5,-.6,-.7))
  self.assertTrue(v.signal(f,("XLE","XOM","CVX"),"breadth","09:25",-1))
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"breadth","09:25",1))
 def test_strong_breadth_higher_threshold(self):
  f=self.make((.26,.36,.45))
  self.assertTrue(v.signal(f,("XLE","XOM","CVX"),"breadth","09:25",1))
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"strong_breadth","09:25",1))
 def test_prior_five_volatility_no_same_day(self):
  self.assertAlmostEqual(v.abs_prev5_hist([100,102,104.04,106.1208,108.243216]),2)
  self.assertIsNone(v.abs_prev5_hist([99,100]))
  f=self.make((.5,.6,.7),mean=2)
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"prior5_scaled","09:25",1))
 def test_no_future_rth_signal(self):
  f=self.make((2,2,2))
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"opening_followthrough","09:25",1))
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"15m_acceleration","09:25",1))
 def test_missing_recent_complete_window_fails(self):
  f=self.make((2,2,2))
  for x in f.values():x["recent15"]=None
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"15m_acceleration","10:00",1))
 def test_no_rule_from_missing_peer(self):
  f={"XLE":self.f(5),"XOM":self.f(5)}
  self.assertFalse(v.signal(f,("XLE","XOM","CVX"),"sector_only","09:25",1))
 def test_synthetic_unprofitable_training_is_no_trade(self):
  e={"energy_09:25_breadth_UP_etf":[{"day":f"2026-04-{i:02}","net30":-1,
       "gross":-.7,"major":False,"signal_at":"", "exit_adv_next_open_30":None} for i in range(1,31)]}
  out=v.evaluate(e,[],{}, {})
  self.assertIsNone(out["sectors"]["energy"]["locked_qualifying_policy"])
 def test_empty_policy(self):
  self.assertEqual(v.summary_rows([]),{"count":0,"independent_days":0})
if __name__=="__main__":unittest.main()
