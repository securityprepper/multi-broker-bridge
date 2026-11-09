"""Regression for next-open outcome audit; no broker interface."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from v2_52week_0935_downside_nextopen import summarize
def row(day,significant,alert,benefit=None,gapped=False):
    return {"sector":"semi","day":day,"symbol":"AMD","observed_warning_0935":alert,
      "severe_down":significant,"already_down5_at_warning":gapped,
      "early_sale_vs_next_open_gross_pp":benefit}
class DownsideAuditTests(unittest.TestCase):
    def test_hits_misses_and_false_alert(self):
        r=summarize([row("2026-01-01",True,True,1),
                     row("2026-01-02",True,False),
                     row("2026-01-03",False,True,-1),
                     row("2026-01-04",False,False)])
        self.assertEqual((r["severe_hits"],r["severe_missed"],r["nonsevere_warnings"]),(1,1,1))
        self.assertEqual(r["early_sale_better_vs_next_open_30bp"],1)
    def test_missing_following_open_excluded_from_denominator(self):
        r=summarize([row("2026-01-01",True,True,None),
                     row("2026-01-02",False,True,.6)])
        self.assertEqual(r["warned_next_open_comparable"],1)
        self.assertEqual(r["early_sale_better_vs_next_open_30bp"],1)
    def test_early_warning_gapped_does_not_count_as_pre_gap(self):
        r=summarize([row("2026-01-01",True,True,2,True),
                     row("2026-01-02",True,True,0,False)])
        self.assertEqual(r["severe_hits"],2)
        self.assertEqual(r["severe_hits_after_already_down5"],1)
    def test_earliest_warning_is_first_chronological_hit(self):
        r=summarize([row("2026-02-02",True,True,1),
                     row("2026-01-01",True,True,1)])
        self.assertTrue(r["earliest_major_warning"].startswith("2026-01-01T09:35"))
if __name__=="__main__":unittest.main()
