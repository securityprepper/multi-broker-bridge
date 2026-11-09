import unittest
from research.v2_sector_hourly_precision import candidate,prior5_delta,current_delta,outcome,summarize
def mockseries(prev=.9,one=1.01,next_o=1.03,close=.98,dates=8):
 d={}
 for i in range(dates):d[f"2026-07-{i+1:02d}"]={"15:30":(prev,prev,prev,prev)}
 d["2026-07-09"]={"09:30":(1,1.01,1,one),"10:30":(next_o,next_o,next_o,next_o),
                 "15:30":(close,close,close,close)}
 return d
class SectorResearchTests(unittest.TestCase):
 def test_no_current_day_close_needed_to_generate(self):
  x=mockseries()
  basket={"GLD":x,"GDX":x,"GDXJ":x,"NEM":x}
  q=candidate(basket,"2026-07-09","GLD","GDX",("GDXJ","NEM"),.25,.5,"dual_breadth")
  x["2026-07-09"]["15:30"]=(100,100,100,100)
  self.assertEqual(q,candidate(basket,"2026-07-09","GLD","GDX",("GDXJ","NEM"),.25,.5,"dual_breadth"))
 def test_missing_peer_fails_closed(self):
  x=mockseries()
  self.assertFalse(candidate({"GLD":x,"GDX":x,"GDXJ":{}},"2026-07-09","GLD","GDX",("GDXJ",),.25,.5,"dual_breadth"))
 def test_previous_five_only(self):
  x=mockseries()
  self.assertIsNotNone(prior5_delta(x,"2026-07-09"))
  x["2026-07-09"]["15:30"]=(100,100,100,100)
  self.assertEqual(prior5_delta(x,"2026-07-09"),0)
 def test_return_future_only_outcome(self):
  x=mockseries()
  o=outcome({"GDX":x},"2026-07-09","GDX")
  self.assertLess(o["net_30bp_pct"],0)
 def test_no_false_wins_on_empty(self):
  self.assertIsNone(summarize([])["precision"])
if __name__=="__main__":
 unittest.main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]