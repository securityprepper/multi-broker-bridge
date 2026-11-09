"""Research-only semiconductor causal warning/followthrough regression tests."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from research import v2_semi_postalert_followthrough as v

class SemiFollowthroughTests(unittest.TestCase):
 def e(self):
  return {"sym":"AMD","day":"2026-11-02","alert_at":"2026-11-02T09:40:00-05:00",
    "sell_proxy":100,"total_pct":-2.5,"last15_pp":-1,"major":True,
    "before_5":True,"gap_already":False,"benefit_vs_open_30bp":1,
    "close_pct":-6}
 def test_future_bar_open_not_close(self):
  et=ZoneInfo("America/New_York")
  ser={"AMD":{"2026-11-02":{"10:10":(datetime(2026,11,2,10,10,tzinfo=et),97,95)}}}
  self.assertEqual(v.forward_price(ser,self.e(),30),97)
 def test_missing_forward_bar_not_false_winner(self):
  self.assertIsNone(v.forward_price({"AMD":{}},self.e(),30))
 def test_causal_filter_uses_only_signal_features(self):
  x=self.e();a=v.classify(x);x["major"]=False;x["close_pct"]=20
  self.assertEqual(v.classify(x),a)
 def test_forward_advantage_after_cost(self):
  et=ZoneInfo("America/New_York")
  ser={"AMD":{"2026-11-02":{"10:10":(datetime(2026,11,2,10,10,tzinfo=et),98,101)}}}
  x=v.add_outcomes(self.e(),ser)
  self.assertAlmostEqual(x["next30_early_sale_after30bp"],1.70)
 def test_score_positive_and_false_alarm_counts(self):
  x=self.e();x["next30_early_sale_after30bp"]=.5;x["next30_drop_pct"]=1.2
  y=dict(x);y["major"]=False;y["next30_early_sale_after30bp"]=-.7;y["next30_drop_pct"]=0
  r=v.score([x,y],1)
  self.assertEqual(r["major_hits"],1)
  self.assertEqual(r["nonmajor_warnings"],1)
  self.assertEqual(r["30min_early_sale_positive"],1)
 def test_empty_score(self):
  self.assertEqual(v.score([],0)["alerts"],0)
if __name__=="__main__":unittest.main()
