"""Deterministic as-of and locked out-of-sample tests; no broker I/O."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_locked_exit_policy_walkforward import (
    policy_outcome, choose_from_previous, walkforward, CHECKS, nextbar_sell)

D=date(2026,11,9)
def t(h,m):return datetime.combine(D,time(h,m),ET)
def event(at=t(9,40),signal=100,entry=100.05):
    return {"at":at.isoformat(),"price":signal,"next_bar_open":entry}

def bars(*items):
    out={}
    for tm, o, c in items:
        out[tm]=[o,max(o,c),min(o,c),c,200]
    return out

class PolicyTests(unittest.TestCase):
    def test_no_buy_if_nextbar_exceeds_limit(self):
        r=policy_outcome({},event(entry=101),101,"hold_1400")
        self.assertFalse(r["eligible_entry"])
        self.assertEqual(r["net_pct"],0)

    def test_observation_cannot_exit_on_signal_bar(self):
        # 09:35-09:40 candle close was known when signal fired at 09:40.
        # It cannot be used to trigger exit for an entry at 09:40.
        b=bars((t(9,35),100,99.00),(t(9,40),100.05,100.10),
               (t(9,45),100.10,100.20))
        r=policy_outcome(b,event(),100.50,"sl075_only")
        self.assertEqual(r["exit_kind"],"NO_TRIGGER_MARK_1400")

    def test_takeprofit_nextbar_timing(self):
        b=bars((t(9,40),100.05,100.9),(t(9,45),101,101.1))
        r=policy_outcome(b,event(),100.2,"tp05_only")
        self.assertEqual(r["exit_at"],t(9,45).isoformat())
        self.assertEqual(r["exit_kind"],"BOUNDED_EXIT_PRICE_ELIGIBLE")

    def test_unfilled_limit_does_not_fabricate_exit(self):
        b=bars((t(9,40),100.05,99),
               (t(9,45),98.50,98.50))
        r=policy_outcome(b,event(),92,"sl075_only")
        self.assertEqual(r["exit_kind"],"UNFILLED_THEN_MARK_1400")
        self.assertFalse(r["exit_eligible"])

    def test_no_signal_after_14(self):
        b=bars((t(13,55),100.1,99), (t(14,0),100,100))
        r=policy_outcome(b,event(),100,"sl075_only")
        self.assertEqual(r["exit_at"],t(14,0).isoformat())

    def test_guard_invalid_policy(self):
        with self.assertRaises(ValueError):
            policy_outcome({},event(),100,"retrospective_max_profit")

    def test_reject_unfavorable_sell_proxy(self):
        self.assertIsNone(nextbar_sell(100,99.5))
        self.assertIsNotNone(nextbar_sell(100,99.9))

    def test_select_only_from_supplied_prior_rows(self):
        def row(day,p0,p1):
            return {"day":day,"scores":{
                name:{"net_pct":p0 if name=="hold_1400" else p1,"eligible_entry":True}
                for name in CHECKS}}
        before=[row("2026-08-%02d"%d,5,0) for d in range(1,21)]
        later=[row("2026-09-%02d"%d,-100,200) for d in range(1,21)]
        p=choose_from_previous(before,CHECKS)
        self.assertEqual(p,"hold_1400")
        # Future data was not in the training sample.
        self.assertEqual(choose_from_previous(before,CHECKS),p)
        self.assertNotEqual(choose_from_previous(later,CHECKS),p)

    def test_walkforward_select_monthly_using_past_only(self):
        def rec(day,pref,alt):
            return {"day":day, "scores":{
                k:{"net_pct":pref if k=="hold_1400" else alt,"eligible_entry":True}
                for k in CHECKS}}
        history=[rec("2026-03-%02d"%d,2,0) for d in range(1,26)]
        later=[rec("2026-04-%02d"%d,-2,3) for d in range(1,26)]
        out=walkforward(history+later,monthly_first=date(2026,4,1))
        self.assertEqual(out["monthly_choices"][0]["policy"],"hold_1400")
        self.assertEqual(out["all"]["signals"],25)
        self.assertEqual(out["all"]["net_mean_pct"],-2)
        self.assertEqual(out["all"]["baseline_mean_pct"],-2)

if __name__=="__main__": unittest.main()