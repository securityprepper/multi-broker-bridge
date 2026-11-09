"""Point-in-time and prior-five boundaries for research-only cohort study."""
import unittest
from datetime import date, timedelta
from research.v2_prior5_cohort_stress import five_completed_return, cohort, summarise

def days(n):
    start = date(2026,1,1)
    return [start + timedelta(days=i) for i in range(n)]

class PriorFiveTests(unittest.TestCase):
    def test_exactly_five_completed_returns(self):
        d=days(9)
        prices={day:100+10*i for i,day in enumerate(d)}
        self.assertIsNone(five_completed_return(prices,d,d[5]))
        self.assertAlmostEqual(five_completed_return(prices,d,d[6]),50)
        self.assertAlmostEqual(five_completed_return(prices,d,d[7]),(160/110-1)*100)
    def test_current_and_future_prices_never_used(self):
        d=days(9)
        p={day:100+i for i,day in enumerate(d)}
        original=five_completed_return(p,d,d[6])
        p[d[6]]=100000
        p[d[7]]=200000
        p[d[8]]=300000
        self.assertEqual(original,five_completed_return(p,d,d[6]))
    def test_missing_one_of_six_closes_fails_closed(self):
        d=days(7);p={day:100 for day in d}
        del p[d[0]]
        self.assertIsNone(five_completed_return(p,d,d[6]))
        q={day:100 for day in d}
        del q[d[3]]
        self.assertIsNone(five_completed_return(q,d,d[6]))
    def test_cohort_boundaries(self):
        self.assertEqual(cohort(-5,-8)["sector"],"weak")
        self.assertEqual(cohort(-5,-8)["relative"],"lagging")
        self.assertEqual(cohort(5,8)["sector"],"strong")
        self.assertEqual(cohort(5,8)["relative"],"leading")
        self.assertEqual(cohort(0,0)["sector"],"neutral")
        self.assertEqual(cohort(0,0)["relative"],"neutral")
        self.assertIsNone(cohort(None,5))
    def test_missing_outcome_not_counted_as_eligible(self):
        a={"side":"up","later":False,"cohort":{"sector":"weak"},
           "major":True,"event":{"price":101},"score":None}
        result=summarise([a],"up","all","all",None)
        self.assertEqual(result["major_hits"],1)
        self.assertEqual(result["scorable_next_open"],0)
        self.assertIsNone(result["mean_bounded_nextopen_pp_or_pct"])
    def test_retrospective_label_never_used_by_cohort(self):
        self.assertEqual(cohort(2,5),cohort(2,5))

if __name__=="__main__":
    unittest.main()
