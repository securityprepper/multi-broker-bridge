from datetime import datetime,timezone,timedelta
import unittest
from research.v2_quote_quality_20261112 import classify
E=datetime(2026,11,9,13,0,tzinfo=timezone.utc)
S=E-timedelta(seconds=5)
D={'t':'2026-11-09T12:59:59Z','bp':100,'ap':100.2,'bs':10,'as':10}
def check(data,side='entry',qty=4):
    return classify(data,start=S,end=E,side=side,filled_qty=qty)
class TestQuality(unittest.TestCase):
    def test_fresh(self):self.assertEqual(check({'quotes':[D]})['status'],'FRESH_ASOF_DISPLAYED_QUOTE')
    def test_no_proof_of_fill(self):self.assertIs(check({'quotes':[D]})['executable_fill_verified'],False)
    def test_null_quote_list(self):self.assertEqual(check({'quotes':None})['status'],'MALFORMED_RESPONSE')
    def test_null_size_is_parse_not_provider_failure(self):
        self.assertEqual(check({'quotes':[dict(D,bs=None)]})['status'],'NO_VALID_QUOTE')
        self.assertTrue(check({'quotes':[dict(D,bs=None)]})['parse_error_present'])
    def test_null_ask_is_parse(self):self.assertEqual(check({'quotes':[dict(D,ap=None)]})['rejected_rows'],1)
    def test_keep_good_after_bad(self):self.assertEqual(check({'quotes':[{**D,'as':None},D]})['status'],'FRESH_ASOF_DISPLAYED_QUOTE')
    def test_crossed(self):self.assertEqual(check({'quotes':[dict(D,ap=99)]})['status'],'NO_VALID_QUOTE')
    def test_future(self):self.assertEqual(check({'quotes':[dict(D,t='2026-11-09T13:00:01Z')]})['status'],'NO_VALID_QUOTE')
    def test_stale(self):self.assertEqual(check({'quotes':[dict(D,t='2026-11-09T12:59:56Z')]})['status'],'STALE_OR_FUTURE_QUOTE')
    def test_pagination(self):self.assertEqual(check({'quotes':[D],'next_page_token':'next'})['status'],'PAGINATION_UNRESOLVED')
    def test_size(self):self.assertEqual(check({'quotes':[{**D,'as':1}]})['status'],'DISPLAYED_SIZE_INSUFFICIENT')
    def test_exit_size(self):self.assertEqual(check({'quotes':[dict(D,bs=1)]},side='exit')['status'],'DISPLAYED_SIZE_INSUFFICIENT')
    def test_bad_args(self):
        with self.assertRaises(ValueError):check({'quotes':[D]},qty=0)
    def test_nan(self):self.assertEqual(check({'quotes':[dict(D,bp=float('nan'))]})['status'],'NO_VALID_QUOTE')
if __name__=='__main__': unittest.main()
