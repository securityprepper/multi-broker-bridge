"""Research-only monthly walk-forward tests; no future data or broker actions."""
import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("monthly",Path(__file__).with_name("v2_direction_monthly_walkforward_20261109.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fake(day,pred="UP"):
 return {"day":day,"prediction":pred,"actual":"UP","emergency":False,
 "significant_up":False,"significant_down":False}
class MonthlyTests(unittest.TestCase):
 def test_first_checkpoint_wins(self):
  x={("08:30","etf",.1):{"2026-04-01":fake("2026-04-01","UP")},
     ("10:00","etf",.1):{"2026-04-01":fake("2026-04-01","DOWN")}}
  r,c=m.first_monthly_forecasts(["2026-04-01"],{"08:30":("08:30","etf",.1),
     "10:00":("10:00","etf",.1)},x)
  self.assertEqual(r[0]["prediction"],"UP")
  self.assertEqual(c,{"08:30":1})
 def test_no_train_qualification_counts_abstain(self):
  x={("10:00","etf",.1):{"2026-04-01":fake("2026-04-01","UP")}}
  r,_=m.first_monthly_forecasts(["2026-04-01"],{},x)
  self.assertEqual(r[0]["prediction"],"ABSTAIN")
 def test_no_future_month_for_selection(self):
  rows={}
  for day in ("2026-03-01","2026-04-01"):
   rows[day]=fake(day)
  choice=m.train_choice({("10:00","etf",.1):rows},"10:00","2026-04-01")
  self.assertIsNone(choice)
 def test_no_signal_maintains_denominator(self):
  xs={("10:00","etf",.1):{"2026-04-01":fake("2026-04-01")}}
  y,_=m.first_monthly_forecasts(["2026-04-01"],{},xs)
  self.assertEqual(len(y),1)
 def test_clock_order(self):
  self.assertLess(m.CLOCKS.index("09:25"),m.CLOCKS.index("10:00"))
 def test_frozen_prior_month(self):
  self.assertEqual(m.MONTHS[0],"2026-04-01")
  self.assertEqual(m.MONTHS[-1],"2026-11-01")
if __name__=="__main__":unittest.main()