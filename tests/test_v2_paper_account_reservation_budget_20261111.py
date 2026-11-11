import unittest
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from research.v2_paper_account_reservation_budget_20261111 import evaluate_with_reservations

NOW=datetime(2026,11,11,15,0,tzinfo=timezone.utc)
AID="fake-receiving-PAPER-account-for-tests"
FP=sha256(AID.encode()).hexdigest()[:24]
def fixture(**override):
    account={"id":AID,"status":"ACTIVE","account_blocked":False,
             "trading_blocked":False,"cash":"5000"}
    monitor={"broker_verified":True,"paper_only":True,
             "paper_account_fingerprint":FP,"session_date":"2026-11-11",
             "asof_utc":(NOW-timedelta(seconds=5)).isoformat(),
             "loss_lockout":False,"daily_loss_limit":"400","combined_exposure_limit":"11800",
             "daily_equity_change":"-10"}
    inventory={"account_id":AID,"account_fingerprint":FP,
               "positions_complete":True,"orders_complete":True,
               "received_at_utc":(NOW-timedelta(seconds=3)).isoformat(),
               "reservations_read_with_exclusive_account_lock":True}
    proposed={"recommendation_id":"new-a","source_task":"Trading Opportunities One",
              "ticket_notional":"1500","session_date":"2026-11-11"}
    args=dict(account=account,positions=[{"market_value":"10000"}],orders=[],
              monitor=monitor,inventory=inventory,reservations=[],
              proposed=proposed,now=NOW,expected_id=AID)
    args.update(override)
    return args

def reservation(id="first",state="RESERVED_UNKNOWN",value="1500",source="Five Day Rebound",**extra):
    r={"recommendation_id":id,"account_fingerprint":FP,
       "session_date":"2026-11-11","committed_notional":value,
       "source_task":source,"status":state}
    r.update(extra)
    return r

class Budget(unittest.TestCase):
    def check(self,d):return evaluate_with_reservations(**d)
    def test_first_ticket_allowed_shadow_only(self):
        out=self.check(fixture())
        self.assertTrue(out["ready"]);self.assertFalse(out["order_authorized"])
        self.assertEqual(out["projected_with_reservations"],"11500")
    def test_two_disjoint_symbols_two_sources_cannot_both_admit(self):
        first=self.check(fixture())
        second=self.check(fixture(reservations=[reservation()]))
        self.assertTrue(first["ready"])
        self.assertFalse(second["ready"])
        self.assertEqual(second["reason"],"ACCOUNT_WIDE_RISK_AND_RESERVED_EXPOSURE")
    def test_unresolved_post_still_consumes_budget(self):
        r=reservation(state="SUBMISSION_UNKNOWN")
        self.assertFalse(self.check(fixture(reservations=[r]))["ready"])
    def test_time_aged_unknown_does_not_release(self):
        r=reservation(state="SUBMISSION_UNKNOWN",claimed_at="2026-01-01")
        self.assertFalse(self.check(fixture(reservations=[r]))["ready"])
    def test_proven_no_post_releases_budget(self):
        r=reservation(state="PROVEN_NO_POST",post_started=False,exclusive_no_post_proof=True)
        self.assertTrue(self.check(fixture(reservations=[r]))["ready"])
    def test_unproven_no_post_not_released(self):
        r=reservation(state="PROVEN_NO_POST",post_started=None,exclusive_no_post_proof=False)
        self.assertEqual(self.check(fixture(reservations=[r]))["reason"],"UNPROVEN_RESERVATION_RELEASE")
    def test_broker_accepted_reflected_order_not_double_counted(self):
        args=fixture(positions=[{"market_value":"9000"}],orders=[
            {"id":"broker-parent","side":"buy","qty":"1","filled_qty":"0","limit_price":"1500"}])
        args["proposed"]["ticket_notional"]="1000"
        r=reservation(state="BROKER_ACCEPTED",broker_order_id="broker-parent",
                      order_id_broker_verified=True)
        self.assertTrue(self.check(dict(args,reservations=[r]))["ready"])
    def test_broker_accepted_not_reflected_counts_again(self):
        args=fixture(positions=[{"market_value":"9000"}],orders=[
            {"id":"broker-parent","side":"buy","qty":"1","filled_qty":"0","limit_price":"1500"}])
        args["proposed"]["ticket_notional"]="1000"
        r=reservation(state="BROKER_ACCEPTED",broker_order_id="other-unmatched",
                      order_id_broker_verified=True)
        self.assertFalse(self.check(dict(args,reservations=[r]))["ready"])
    def test_cross_broker_missing_data_never_invoked(self):
        self.assertTrue(self.check(fixture())["ready"])
    def test_exact_daily_loss_cutoff_blocks(self):
        d=fixture();d["monitor"]["daily_equity_change"]="-400"
        self.assertEqual(self.check(d)["reason"],"DAILY_PAPER_LOSS_LIMIT_REACHED")
    def test_missing_accountwide_lock_fails(self):
        d=fixture();d["inventory"]["reservations_read_with_exclusive_account_lock"]=False
        self.assertEqual(self.check(d)["reason"],"NO_ACCOUNT_WIDE_ATOMIC_LOCK")
    def test_stale_positions_orders_snapshot_fails(self):
        d=fixture();d["inventory"]["received_at_utc"]=(NOW-timedelta(seconds=21)).isoformat()
        self.assertEqual(self.check(d)["reason"],"INVENTORY_STALE")
    def test_different_broker_account_not_accepted(self):
        d=fixture();d["inventory"]["account_id"]="different"
        self.assertEqual(self.check(d)["reason"],"INVENTORY_WRONG_RECEIVING_ACCOUNT")
    def test_closed_requires_broker_reconciliation(self):
        r=reservation(state="CLOSED_VERIFIED",broker_terminal_verified=True,
                      receiving_inventory_reconciled=False)
        self.assertEqual(self.check(fixture(reservations=[r]))["reason"],"UNPROVEN_TERMINAL_RELEASE")
    def test_same_recommendation_no_duplicate_order(self):
        r=reservation(id="new-a")
        self.assertEqual(self.check(fixture(reservations=[r]))["reason"],"ALREADY_RESERVED_SAME_RECOMMENDATION")
    def test_wrong_session_other_account_reservations_not_blocking(self):
        r=reservation(account_fingerprint="not-this-account")
        self.assertTrue(self.check(fixture(reservations=[r]))["ready"])
    def test_unknown_state_fail_closed(self):
        self.assertEqual(self.check(fixture(reservations=[reservation(state="WHATEVER")]))["reason"],"UNKNOWN_RESERVATION_STATE")
    def test_negative_commitment_cannot_mask_positive_risk(self):
        d=fixture(reservations=[reservation(id="r1",value="-1500"),
                                 reservation(id="r2",value="1500")])
        self.assertEqual(self.check(d)["reason"],"INVALID_RESERVATION_AMOUNT")
    def test_zero_active_reservation_rejected(self):
        d=fixture(reservations=[reservation(value="0")])
        self.assertEqual(self.check(d)["reason"],"INVALID_RESERVATION_AMOUNT")
    def test_partial_broker_fill_is_counted_as_pending_remainder(self):
        d=fixture(positions=[{"market_value":"9000"}],orders=[{
            "side":"buy","id":"b","qty":"8","filled_qty":"4","limit_price":"250"}])
        self.assertTrue(self.check(d)["ready"])
        self.assertEqual(self.check(d)["projected_with_reservations"],"11500")
    def test_existing_cross_strategy_pending_at_cap_blocks(self):
        d=fixture(positions=[{"market_value":"9500"}],orders=[{
            "side":"buy","id":"b","qty":"4","filled_qty":"0","limit_price":"500"}])
        self.assertEqual(self.check(d)["reason"],"RECEIVING_BROKER_COMBINED_EXPOSURE")
if __name__=="__main__":unittest.main()
