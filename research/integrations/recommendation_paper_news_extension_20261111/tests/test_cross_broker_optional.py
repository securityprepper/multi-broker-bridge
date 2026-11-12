"""Broker-scoped order authorization: other brokers are advisory only."""
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from unittest.mock import patch
from recommendation_paper_bridge import bridge,earnings_ibkr_guard,earnings_portfolio_guard
NOW=datetime(2026,11,11,15,20,tzinfo=timezone.utc)
ACCOUNT="11111111-2222-3333-4444-555555555555"

def quote_broker(method,path,body=None,data=False):
    if path=="/v2/account":
        return {"id":ACCOUNT,"status":"ACTIVE","trading_blocked":False,
                "account_blocked":False,"cash":"10000"}
    if path=="/v2/positions":return []
    if path.startswith("/v2/orders?"):return []
    if data and path.startswith("/v2/stocks/bars?"):
        return {"bars":{"AMD":[{"t":"2026-11-10T05:00:00Z",
                                  "c":100.00}]}, "next_page_token":None}
    if "/quotes/latest" in path:
        return {"quote":{"t":(NOW-timedelta(seconds=10)).isoformat(),
                         "bp":"100.04","ap":"100.10"}}
    raise AssertionError("unexpected broker call "+method+" "+path)
ROW={"source_task":bridge.EARN_TASK,"symbol":"AMD",
     "issued_at_utc":(NOW-timedelta(seconds=12)).replace(tzinfo=None),
     "expires_at_utc":(NOW+timedelta(minutes=3)).replace(tzinfo=None),
     "limit_price":Decimal("100.10"),"stop_loss":Decimal("99"),
     "profit_target":Decimal("103"),"intended_qty":19,"action":"BUY NOW",
     "quote_last":Decimal("100.05"),"quote_ask":Decimal("100.10")}

class CrossBrokerAdvisoryTests(unittest.TestCase):
    def test_absent_ibkr_inventory_does_not_block_alpaca(self):
        with tempfile.TemporaryDirectory() as d:
            proof=earnings_ibkr_guard.advisory("AMD",NOW,Path(d)/"absent.json")
            self.assertEqual(proof["status"],"UNAVAILABLE_STALE_OR_INCOMPLETE")
            self.assertIs(proof["blocks_order"],False)
    def test_stale_ibkr_inventory_does_not_block(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"stale.json"
            path.write_text(json.dumps({"asof_utc":(NOW-timedelta(days=2)).isoformat()}))
            result=earnings_ibkr_guard.advisory("AMD",NOW,path)
            self.assertFalse(result["blocks_order"])
    def test_verified_ibkr_overlap_is_annotation_not_veto(self):
        with patch.object(earnings_ibkr_guard,"require",side_effect=earnings_ibkr_guard.MissingIBKREvidence("already held/pending in IBKR")):
            result=earnings_ibkr_guard.advisory("AMD",NOW)
        self.assertEqual(result["status"],"VERIFIED_SAME_SYMBOL_OVERLAP")
        self.assertFalse(result["blocks_order"])
    def preflight(self,own_risk=None,external=None):
        if own_risk is None:
            own_risk={"risk_status":"PAPER_LOSS_AND_EXPOSURE_VALIDATED"}
        if external is None:
            external={"other_broker":"IBKR","status":"UNAVAILABLE_STALE_OR_INCOMPLETE",
                      "blocks_order":False,"advisory_only":True}
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(bridge,"expected_paper_account",return_value=ACCOUNT),patch.object(bridge,"require_clear",return_value={"status":"NEWS_CLEAR_ASOF","evidence_sha256":"mock"}),patch.object(earnings_portfolio_guard,"require",return_value=own_risk),patch.object(earnings_ibkr_guard,"advisory",return_value=external):
            return bridge.preflight(dict(ROW),NOW,httpfn=quote_broker)
    def test_alpaca_preflight_passes_without_ibkr(self):
        result=self.preflight()
        self.assertEqual(result["other_broker_advisory"]["status"],"UNAVAILABLE_STALE_OR_INCOMPLETE")
    def test_alpaca_preflight_passes_verified_other_broker_overlap(self):
        result=self.preflight(external={"other_broker":"IBKR",
                "status":"VERIFIED_SAME_SYMBOL_OVERLAP","advisory_only":True,
                "blocks_order":False})
        self.assertEqual(result["other_broker_advisory"]["status"],"VERIFIED_SAME_SYMBOL_OVERLAP")
    def test_own_alpaca_loss_lockout_still_blocks(self):
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(bridge,"expected_paper_account",return_value=ACCOUNT),patch.object(earnings_portfolio_guard,"require",side_effect=earnings_portfolio_guard.RiskUnavailable("own broker daily loss lockout")),patch.object(earnings_ibkr_guard,"advisory") as cross:
            with self.assertRaises(bridge.Unsafe):
                bridge.preflight(dict(ROW),NOW,httpfn=quote_broker)
            cross.assert_not_called()
    def test_own_alpaca_broker_inventory_missing_still_blocks(self):
        def no_positions(method,path,body=None,data=False):
            if path=="/v2/positions":return None
            return quote_broker(method,path,body,data)
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(bridge,"expected_paper_account",return_value=ACCOUNT):
            with self.assertRaises(bridge.Unsafe):
                bridge.preflight(dict(ROW),NOW,httpfn=no_positions)
if __name__=="__main__":unittest.main()
