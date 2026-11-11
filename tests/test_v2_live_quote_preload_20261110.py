"""Offline tests for independent bars-then-quotes GET-only timing reproduction."""
import json
import unittest
from datetime import datetime,timezone
from urllib.parse import parse_qs, urlsplit
from research.v2_live_quote_receipt_readonly_20261110 import preload_bars_like_mbb
T=datetime(2026,11,11,3,37,37,tzinfo=timezone.utc)
class FakeResponse:
    status=200
    def __init__(self,body):self.body=json.dumps(body).encode()
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n):return self.body[:n]
class ReadOnlyBarPreload(unittest.TestCase):
    def test_bounded_get_only(self):
        requests=[]
        def opener(req,timeout=12):
            requests.append(req)
            return FakeResponse({"bars":{"AMD":[{"t":"2026-11-11T03:00:00Z"}]},"next_page_token":None})
        res=preload_bars_like_mbb(["AMD"],"boats",{},T,opener=opener)
        self.assertEqual(res["bar_rows"],1)
        self.assertEqual(len(requests),1)
        self.assertEqual(requests[0].get_method(),"GET")
        parts=urlsplit(requests[0].full_url)
        self.assertEqual(parts.hostname,"data.alpaca.markets")
        self.assertEqual(parts.path,"/v2/stocks/bars")
        q=parse_qs(parts.query)
        self.assertEqual(q["feed"],["boats"])
        self.assertEqual(q["timeframe"],["1Min"])
    def test_pagination_truncated_fails(self):
        with self.assertRaisesRegex(ValueError,"truncated"):
            preload_bars_like_mbb(["AMD"],"sip",{},T,
                opener=lambda *a,**k:FakeResponse({"bars":{},"next_page_token":"p2"}))
    def test_bad_format_rejected(self):
        with self.assertRaisesRegex(ValueError,"bad bars"):
            preload_bars_like_mbb(["AMD"],"sip",{},T,
                opener=lambda *a,**k:FakeResponse({"wrong":{}}))
    def test_invalid_feed_no_network(self):
        with self.assertRaises(ValueError):
            preload_bars_like_mbb(["AMD"],"iex",{},T,
                opener=lambda *a,**k:self.fail("untrusted network"))
if __name__=="__main__":unittest.main()
