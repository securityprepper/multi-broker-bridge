import unittest
from datetime import datetime,timezone,timedelta
from dataclasses import replace
from research.v2_high_signal_entry_plan import Catalyst,Quote,PaperAccount,plan
NOW=datetime(2026,11,9,15,0,tzinfo=timezone.utc)
E=Catalyst("AMD","EARNINGS_RELEASE_CANDIDATE_UNVERIFIED",NOW-timedelta(seconds=35),
           NOW-timedelta(seconds=25),True,True)
Q=Quote(NOW-timedelta(seconds=3),199.2,200.0,195.0,199.0,(1.0,1.5,2,1.7,2))
A=PaperAccount("PAPER-A","PAPER",NOW-timedelta(seconds=7),8000,stop_controller_verified=True)
def doit(e=E,q=Q,a=A,now=NOW,session="RTH",validated=True):
    return plan(e,q,a,now,session,validated)
class TestPlan(unittest.TestCase):
    def test_whole_shares_and_stop(self):
        p=doit()
        self.assertFalse(p["order_submitted"])
        self.assertLessEqual(p["notional"],2000)
        self.assertIsInstance(p["qty"],int)
        self.assertLessEqual(p["estimated_hard_stop_risk"],60.1)
        self.assertLess(p["stop"],p["limit"])
        self.assertGreater(p["profit_target"],p["limit"])
    def test_live_blocked(self):
        self.assertEqual(doit(a=replace(A,broker_environment="LIVE"))["status"],"BLOCKED")
    def test_research_unverified(self):
        self.assertIn("validated",doit(validated=False)["reason"])
    def test_future_quote_rejected(self):
        self.assertIn("future",doit(q=replace(Q,observed_at=NOW+timedelta(seconds=5)))["reason"])
    def test_future_broker_readback_rejected(self):
        self.assertIn("future",doit(a=replace(A,broker_verified_at=NOW+timedelta(seconds=5)))["reason"])
    def test_stale_quote(self):
        self.assertEqual(doit(q=replace(Q,observed_at=NOW-timedelta(minutes=2)))["status"],"BLOCKED")
    def test_unsafe_overnight(self):
        self.assertIn("stop",doit(a=replace(A,stop_controller_verified=False),session="EXTENDED")["reason"])
    def test_overnight_with_verified_stop_is_not_order(self):
        p=doit(session="EXTENDED")
        self.assertFalse(p["order_submitted"])
        self.assertEqual(p["stop_type"],"VERIFIED_SOFTWARE_STOP")
    def test_already_extended(self):
        self.assertIn("extended",doit(q=replace(Q,first_reaction_reference=180))["reason"])
    def test_existing_order(self):
        self.assertEqual(doit(a=replace(A,open_order_symbols=("AMD",)))["status"],"BLOCKED")
    def test_unverified_bullish_headline(self):
        self.assertEqual(doit(e=replace(E,material_bullish_verified=False))["status"],"BLOCKED")
    def test_after_1315_chicago_not_allowed(self):
        t=datetime(2026,11,9,20,15,tzinfo=timezone.utc)
        self.assertEqual(doit(now=t,q=replace(Q,observed_at=t-timedelta(seconds=2)),
                a=replace(A,broker_verified_at=t-timedelta(seconds=1)),
                e=replace(E,published_at=t-timedelta(seconds=35),first_seen_at=t-timedelta(seconds=25)))["status"],"BLOCKED")
    def test_price_above_notional_skip(self):
        q=replace(Q,ask=2500,bid=2490,previous_close=2450,first_reaction_reference=2485)
        self.assertEqual(doit(q=q)["status"],"BLOCKED")
    def test_not_positive_relative_close(self):
        self.assertEqual(doit(q=replace(Q,previous_close=210))["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
