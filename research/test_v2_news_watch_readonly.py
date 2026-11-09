import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from research import v2_news_watch_readonly as v

NOW=datetime(2026,11,9,22,0,tzinfo=timezone.utc)
def article(i,h,seconds=10):
    return {"id":i,"headline":h,"created_at":(NOW-timedelta(seconds=seconds)).isoformat(),
            "symbols":["AMD"],"source":"wire","url":"https://example.com/a"}

class TestNewsReadOnly(unittest.TestCase):
    def test_news_categories(self):
        self.assertEqual(v.categorize("AMD raises guidance"),"POSITIVE_NEWS_CANDIDATE_UNVERIFIED")
        self.assertEqual(v.categorize("AMD will report earnings"),"EARNINGS_SCHEDULE_MENTION_UNVERIFIED")
        self.assertEqual(v.categorize("AMD reports Q3 results"),"EARNINGS_RELEASE_CANDIDATE_UNVERIFIED")
        self.assertEqual(v.categorize("AMD cuts guidance"),"REVIEW_POSSIBLY_NEGATIVE")
    def test_delay_is_not_realtime(self):
        a=v.validate_article(article(1,"AMD raises guidance",seconds=1000),NOW)
        self.assertFalse(a["realtime_fresh"])
    def test_dedupe(self):
        j,n=v.ingest([article(1,"AMD will report"),article(1,"AMD will report")],NOW,{})
        self.assertEqual(len(n),1)
        _,n2=v.ingest([article(1,"AMD will report")],NOW,j)
        self.assertEqual(n2,[])
    def test_missing_and_malformed_inputs(self):
        self.assertIsNone(v.validate_article({"headline":"x"},NOW))
        with self.assertRaises(ValueError):
            v.ingest([],NOW,{"seen":"invalid"})
    def test_pagination_fail_closed(self):
        class Resp:
            status=200
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps({"news":[],"next_page_token":"again"}).encode()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"alpaca_data_key_id").write_text("test")
            (p/"alpaca_data_secret").write_text("test")
            with self.assertRaises(ValueError):
                v.get_news(NOW,p,opener=lambda req,timeout:Resp())
    def test_fetch_is_get_only(self):
        seen=[]
        class Resp:
            status=200
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return b'{"news": [], "next_page_token": null}'
        def request(req,timeout):
            seen.append((req.get_method(),req.full_url))
            return Resp()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"alpaca_data_key_id").write_text("test")
            (p/"alpaca_data_secret").write_text("test")
            v.get_news(NOW,p,opener=request)
            self.assertEqual(seen[0][0],"GET")
            self.assertTrue(seen[0][1].startswith(v.BASE+"?"))
    def test_run_no_order_and_writes_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"current.json"
            with patch.dict("os.environ",{"V2_NEWS_WATCH_STATE":str(p)}):
                x=v.run(NOW,news_fetcher=lambda n,c:[article(20,"Company raises guidance")],holiday_checker=lambda now:True)
                self.assertEqual(x["orders_submitted"],0)
                self.assertFalse(x["broker_order_permissions"])
                self.assertEqual(x["new_articles"],1)
                x=v.run(NOW,news_fetcher=lambda n,c:[article(20,"Company raises guidance")],holiday_checker=lambda now:True)
                self.assertEqual(x["new_articles"],0)
    def test_paused_holiday_blocks_all_news_calls(self):
        with patch.dict("os.environ",{"V2_NEWS_WATCH_STATE":"/not/used.json"}):
            x=v.run(NOW,news_fetcher=lambda n,c: (_ for _ in ()).throw(AssertionError("news was fetched")),
                    holiday_checker=lambda now:False)
        self.assertEqual(x["market_data_requests"],0)
        self.assertEqual(x["status"],"HOLIDAY_PAUSED_NO_NEWS_POLL")
    def test_unverified_holiday_fails_closed(self):
        with self.assertRaises(ValueError):
            v.run(NOW,news_fetcher=lambda n,c:[],holiday_checker=lambda now: (_ for _ in ()).throw(ValueError("unknown gate")))
    def test_no_invented_executions(self):
        self.assertFalse(hasattr(v,"place_order"))
        self.assertFalse(hasattr(v,"submit_order"))
        self.assertFalse(hasattr(v,"paper_api"))
if __name__=="__main__":unittest.main()
