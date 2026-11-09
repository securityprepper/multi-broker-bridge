"""Unit tests: research-only no broker actions and no future leakage."""
from datetime import datetime,timedelta,time
import unittest
from research import v2_gold_confirmed_walkforward as v
from research import v2_gold_miner_preopen_lead as old

class GoldWalkforwardTests(unittest.TestCase):
    def fake(self, net, day, policy="p", major=False):
        return {"day":day,"symbol":"GDX","policy":policy,
             "decision_ts":day+"T09:25:00","gross_to14":net+.30,
             "net30":net,"gross_next_open":net+.3,
             "gdx_major_up":major,"gdx_major_down":False}
    def test_clock_prevents_rth_before_open(self):
        f={"GLD":{"pct":1},"GDX":{"pct":1},
           "NEM":{"pct":1},"AEM":{"pct":1},"KGC":{"pct":1}}
        self.assertFalse(v.miner_signal(f,"gold_miner_rth","09:25",{},"2026-09-01"))
        self.assertFalse(v.miner_signal(f,"gold_miner_15m","09:25",{},"2026-09-01"))
    def test_prior_five_required(self):
        f={"GLD":{"pct":1,"prior5":-1},"GDX":{"pct":1,"prior5":4},
           "NEM":{"pct":1},"AEM":{"pct":1},"KGC":{"pct":1}}
        self.assertFalse(v.miner_signal(f,"gold_miner_prior5","09:25",{},"2026-09-01"))
    def test_gold_vs_miners(self):
        f={"GLD":{"pct":1},"GDX":{"pct":-.1},
           "NEM":{"pct":1},"AEM":{"pct":1},"KGC":{"pct":1}}
        self.assertTrue(v.miner_signal(f,"gold_only","09:25",{},"2026-09-01"))
        self.assertFalse(v.miner_signal(f,"gold_miners","09:25",{},"2026-09-01"))
    def test_top_miner_only_known_asof(self):
        self.assertEqual(v.choose_asset({"NEM":{"pct":1},"AEM":{"pct":2},"KGC":{"pct":0}},"best_producer"),"AEM")
        self.assertEqual(v.choose_asset({},"best_producer"),None)
    def test_completed_price_is_start_timestamp(self):
        d=datetime(2026,7,1,10,0,tzinfo=old.ET)
        bars={d-timedelta(minutes=5):(1,1,1,100,1),
              d:(1,1,1,200,1),
              d-timedelta(minutes=20):(1,1,1,99,1)}
        self.assertAlmostEqual(v.completed_change(bars,d,15),(100/99-1)*100)
        self.assertLess(v.completed_change(bars,d,15),2)
    def test_later_cannot_select_strategy(self):
        early=[f"2026-04-{i:02}" for i in range(1,31)]
        late=[f"2026-10-{i:02}" for i in range(1,31)]
        events={"alpha":[self.fake(1,x) for x in early]+[self.fake(-2,x) for x in late],
                "beta":[self.fake(.1,x) for x in early]+[self.fake(5,x) for x in late]}
        audit=[{"day":x,"gdx_major_up":False,"gdx_major_down":False} for x in early+late]
        r=v.evaluate(events,audit)
        self.assertEqual(r["selection_by_earlier_only"],"alpha")
        self.assertLess(r["selected_later_metrics"]["mean_net30"],0)
    def test_cash_when_all_training_strategies_lose(self):
        early=[f"2026-04-{i:02}" for i in range(1,31)]
        late=[f"2026-10-{i:02}" for i in range(1,31)]
        events={"alpha":[self.fake(-.2,x) for x in early]+[self.fake(3,x) for x in late],
                "beta":[self.fake(-.5,x) for x in early]+[self.fake(5,x) for x in late]}
        audit=[{"day":x,"gdx_major_up":False,"gdx_major_down":False} for x in early+late]
        r=v.evaluate(events,audit)
        self.assertIsNone(r["selection_by_earlier_only"])
        self.assertEqual(r["earlier_best_rejected_shadow"],"alpha")
    def test_report_days_and_cost(self):
        r=v.report([self.fake(.2,"2026-10-01"),self.fake(-.5,"2026-10-02")])
        self.assertEqual(r["trades"],2)
        self.assertEqual(r["winners30"],1)
        self.assertAlmostEqual(r["mean_net30"],-.15)
    def test_empty_no_winners(self):
        self.assertEqual(v.report([]),{"trades":0,"days":0})
if __name__=="__main__":unittest.main()
