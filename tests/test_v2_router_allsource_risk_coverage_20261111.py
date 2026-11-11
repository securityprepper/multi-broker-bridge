import unittest
from datetime import datetime,timedelta,timezone
from hashlib import sha256
from research.v2_router_allsource_risk_coverage_20261111 import evaluate

NOW=datetime(2026,11,11,15,0,tzinfo=timezone.utc)
ID="11111111-2222-3333-4444-555555555555"
def sample(**kw):
    account={"id":ID,"status":"ACTIVE","account_blocked":False,
             "trading_blocked":False,"cash":"5000"}
    risk={"broker_verified":True,"paper_only":True,
          "paper_account_fingerprint":sha256(ID.encode()).hexdigest()[:24],
          "session_date":"2026-11-11",
          "asof_utc":(NOW-timedelta(seconds=10)).isoformat(),
          "loss_lockout":False,"daily_loss_limit":"400",
          "combined_exposure_limit":"11800","daily_equity_change":"-10"}
    d=dict(account=account,positions=[],orders=[],monitor=risk,
           now=NOW,expected_id=ID,cost="2000")
    d.update(kw);return d

class AllSourceRisk(unittest.TestCase):
    def test_valid_shadow_never_order(self):
        r=evaluate(**sample())
        self.assertTrue(r["ready"]);self.assertFalse(r["order_authorized"])
        self.assertEqual(r["broker_calls"],0)
    def test_lockout(self):
        d=sample();d["monitor"]["loss_lockout"]=True
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_RISK_LOCK_OR_CONFIGURATION")
    def test_daily_loss(self):
        d=sample();d["monitor"]["daily_equity_change"]="-401"
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_DAILY_LOSS_LIMIT")
    def test_aggregate_exposure_including_partial_pending(self):
        d=sample(positions=[{"market_value":"8200"}],orders=[
            {"side":"buy","qty":"10","filled_qty":"2","limit_price":"250"}])
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_COMBINED_EXPOSURE")
    def test_short_exposure_absolute(self):
        d=sample(positions=[{"market_value":"-10500"}])
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_COMBINED_EXPOSURE")
    def test_monitor_stale(self):
        d=sample();d["monitor"]["asof_utc"]=(NOW-timedelta(seconds=96)).isoformat()
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_RISK_STALE")
    def test_monitor_wrong_account(self):
        d=sample();d["monitor"]["paper_account_fingerprint"]="000"
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_RISK_WRONG_ACCOUNT")
    def test_missing_own_orders_blocks(self):
        self.assertEqual(evaluate(**sample(orders=None))["reason"],"RECEIVING_BROKER_INVENTORY_INCOMPLETE")
    def test_broker_account_mismatch_blocks(self):
        self.assertEqual(evaluate(**sample(expected_id="not-the-current-account"))["reason"],"RECEIVING_PAPER_ACCOUNT_NOT_VERIFIED")
    def test_ticket_cap(self):
        self.assertEqual(evaluate(**sample(cost="2000.01"))["reason"],"RECEIVING_BROKER_TICKET_CASH_LIMIT")
    def test_ibkr_and_robinhood_not_used(self):
        self.assertTrue(evaluate(**sample())["ready"])
    def test_missing_risk_evidence_is_not_zero_loss(self):
        d=sample();del d["monitor"]["daily_equity_change"]
        self.assertEqual(evaluate(**d)["reason"],"RECEIVING_BROKER_RISK_DATA_INVALID")

if __name__=="__main__":unittest.main()
