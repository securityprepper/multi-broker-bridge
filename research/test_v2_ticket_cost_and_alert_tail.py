import unittest
from research.v2_ticket_cost_and_alert_tail import (
    cost_return,stats,by_day_bootstrap,wilson_lower,split_rows,downside
)

class CostAndTailTests(unittest.TestCase):
    def test_round_trip_one_share_fee(self):
        self.assertAlmostEqual(cost_return(1,20,1,30,1),-9.3)
    def test_quantity_dilutes_flat_ticket_fee(self):
        self.assertGreater(cost_return(1,20,10),cost_return(1,20,1))
    def test_friction_monotone(self):
        self.assertGreater(cost_return(1,20,1,15),cost_return(1,20,1,60))
    def test_bad_inputs_rejected(self):
        for args in [(0,1,30,1),(20,0,30,1),(20,1,-2,1),(20,1,30,-1)]:
            with self.assertRaises(ValueError):cost_return(1,*args)
    def test_before_after_no_data_leak(self):
        rows=[{"day":"2026-08-31"},{"day":"2026-09-01"}]
        self.assertEqual(len(split_rows(rows)["earlier"]),1)
        self.assertEqual(len(split_rows(rows)["later"]),1)
    def test_cluster_is_not_independent_trades(self):
        rows=[{"day":"d1","x":1},{"day":"d1","x":2},{"day":"d2","x":-1}]
        self.assertEqual(stats(rows,lambda x:x["x"])["days"],2)
        self.assertIsNotNone(by_day_bootstrap(rows,lambda x:x["x"]))
    def test_wilson_lower_bound(self):
        self.assertLess(wilson_lower(8,10),.8)
    def test_repeated_day_signal_rejected(self):
        row={"day":"2026-10-01","symbol":"AMD","sell_adv_30bp":1,"major":True,
             "before_minus5":True,"at":"2026-10-01T10:00:00-04:00"}
        with self.assertRaisesRegex(ValueError,"duplicate"):
            downside({"fixed2":[row,row],"fixed2p5":[],"fixed3":[]})
    def test_negative_warnings_are_outcome_not_signal(self):
        row={"day":"2026-10-01","symbol":"AMD","sell_adv_30bp":-3,"major":False,
             "before_minus5":True,"at":"2026-10-01T10:00:00-04:00"}
        res=downside({"fixed2":[row],"fixed2p5":[],"fixed3":[]})
        self.assertEqual(res["fixed2"]["later"]["warnings_with_2pp_or_more_missed_rebound"],1)
        self.assertEqual(res["fixed2"]["later"]["major_hits"],0)

if __name__=="__main__":unittest.main()