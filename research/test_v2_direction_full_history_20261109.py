"""Research-only tests for full-history serious sector move audit."""
import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("full",Path(__file__).with_name("v2_direction_full_history_20261109.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(day,clock,pred="UP",actual="UP"):
 return {"day":day,"checkpoint":clock,"prediction":pred,"actual":actual,
         "sector_mark_price":1.0,"regular_close_price":1.1,
         "bar_available_at":"2026-09-01T10:00:00-04:00",
         "significant_up":True,"significant_down":False}
class FullHistoryTests(unittest.TestCase):
 def test_earliest_nonabstain_selected(self):
  a=m.choose_first([row("2026-09-01","10:00",pred="DOWN"),
                    row("2026-09-01","08:30",pred="UP")])
  self.assertEqual(a[0]["prediction"],"UP")
 def test_no_signal_remains_abstain(self):
  a=m.choose_first([row("2026-09-01","10:00",pred="ABSTAIN")])
  self.assertEqual(a[0]["prediction"],"ABSTAIN")
 def test_severe_semis_from_prior_close_or_open(self):
  a={"close_pct":-2,"rth_pct":-5.1,"significant_up":False,"significant_down":False}
  self.assertEqual(m.severe_label(a,"semiconductors"),(False,True))
 def test_other_sector_specific_severity(self):
  a={"close_pct":-2,"rth_pct":-5.1,"significant_up":False,"significant_down":True}
  self.assertEqual(m.severe_label(a,"gold_miners"),(False,True))
 def test_empty_study_no_training_rule(self):
  self.assertEqual(m.analyze_sector("semiconductors",{"sectors":{"semiconductors":{
     "checkpoint_results":{}}}})["status"],"NO_TRAINING_QUALIFIED_RULE")
if __name__=="__main__":unittest.main()