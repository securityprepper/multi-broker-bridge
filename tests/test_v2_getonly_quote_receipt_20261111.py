import importlib.util,json,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/"research"/"v2_getonly_quote_receipt_20261111.py"
spec=importlib.util.spec_from_file_location("receipt",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
T=datetime(2026,11,11,19,30,0,tzinfo=timezone.utc)
def q(dt,bid=100,ask=100.2):
    return {"t":dt.isoformat(),"bp":bid,"ap":ask}
class Check(unittest.TestCase):
    def test_corrected_accepts_future_to_scan_but_past_to_receipt(self):
        r=m.evaluate_one(q(T-timedelta(seconds=.25)),T,T-timedelta(seconds=6))
        self.assertEqual(r["corrected"],"ACCEPT")
        self.assertEqual(r["scan_start_clock"],"REJECT_QUOTE_FUTURE")
    def test_stale_quote_rejected(self):
        r=m.evaluate_one(q(T-timedelta(seconds=101)),T,T-timedelta(seconds=6))
        self.assertEqual(r["corrected"],"REJECT_QUOTE_STALE")
    def test_submillisecond_future_rejected_precisely(self):
        r=m.evaluate_one(q(T+timedelta(microseconds=3)),T,T)
        self.assertEqual(r["corrected"],"REJECT_QUOTE_FUTURE")
    def test_too_far_future_rejected(self):
        r=m.evaluate_one(q(T+timedelta(seconds=.1)),T,T-timedelta(seconds=6))
        self.assertEqual(r["corrected"],"REJECT_QUOTE_FUTURE")
    def test_crossed_and_negative_rejected(self):
        self.assertEqual(m.evaluate_one(q(T,101,100),T,T)["corrected"],"REJECT_INVALID_MARKET")
        self.assertEqual(m.evaluate_one(q(T,-1,100),T,T)["corrected"],"REJECT_INVALID_MARKET")
    def test_spread_limit_preserved(self):
        self.assertEqual(m.evaluate_one(q(T,97,100),T,T)["corrected"],"REJECT_SPREAD")
    def test_missing_never_assumed_accept(self):
        self.assertEqual(m.evaluate_one(None,T,T)["corrected"],"REJECT_BAD_QUOTE")
    def test_no_orders_no_credential_in_result(self):
        a=m.classify({"AMD":q(T-timedelta(seconds=.2))},T,T-timedelta(seconds=6),("AMD","MU"))
        self.assertEqual(a["reason_counts"]["corrected"]["ACCEPT"],1)
        self.assertEqual(a["symbols_diagnostic"]["MU"]["corrected"],"REJECT_BAD_QUOTE")
        self.assertEqual(a["orders_submitted"],0)
        self.assertNotIn("APCA-API-SECRET-KEY",json.dumps(a))
    def test_get_only_no_other_host(self):
        self.assertEqual(m.HOST,"https://data.alpaca.markets/v2/stocks/quotes/latest")
        self.assertFalse(hasattr(m,"paper_api"))
if __name__=="__main__":unittest.main()
