"""Offline tests for real issuer/SEC/Alpaca upstream data collector; NO network/credentials."""
import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch
from zoneinfo import ZoneInfo
from recommendation_paper_bridge.news_clearance_publisher import eligible_bundle,EvidenceBlocked
from recommendation_paper_bridge.news_eligibility import evaluate_news_asof
from recommendation_paper_bridge import news_source_collector as c

NOW=datetime(2026,11,13,20,30,tzinfo=timezone.utc)
CUTOFF=datetime(2026,11,12,6,0,tzinfo=timezone.utc)
def clock():return NOW

def fake_get(url,headers,expected_host,clock):
    if expected_host=="data.sec.gov":
        x={"cik":2488,"name":"ADVANCED MICRO DEVICES INC",
           "tickers":["AMD"],"exchanges":["Nasdaq Global Select Market"],
           "filings":{"recent":{"form":["4","8-K"],
             "acceptanceDateTime":["2026-11-10T10:04:00","2026-11-09T16:00:00"],
             "accessionNumber":["0000002488-26-000111","0000002488-26-000112"],
             "items":["","2.02"]}}}
        return json.dumps(x).encode(),NOW
    if expected_host=="ir.amd.com":
        return b'''<?xml version="1.0"?><rss><channel>
         <item><title>AMD Results</title><link>https://ir.amd.com/old-results</link>
           <pubDate>Tue, 10 Nov 2026 10:00:00 -0500</pubDate></item>
         <item><title>AMD New Product</title><link>https://ir.amd.com/older-announce</link>
           <pubDate>Mon, 09 Nov 2026 11:00:00 -0500</pubDate></item>
         </channel></rss>''',NOW
    if expected_host=="data.alpaca.markets":
        return json.dumps({"news":[],"next_page_token":None}).encode(),NOW
    raise ValueError(expected_host)

class RealSourceEvidence(unittest.TestCase):
    def test_https_only_source_host_allowlist(self):
        with self.assertRaises(c.SourceUnknown):
            c.get("http://ir.amd.com/rss",{},"ir.amd.com",clock)
        with self.assertRaises(c.SourceUnknown):
            c.get("https://someotherhost.com/rss",{},"ir.amd.com",clock)
    def test_real_sec_cik_and_exchange_verified(self):
        out=c.sec_snapshot("AMD",2488,CUTOFF,NOW,clock,getfn=fake_get)
        self.assertEqual(out["exchange"],"NASDAQ")
        self.assertEqual(out["events"],[])
    def test_sec_material_8k_pending_review(self):
        def fake(*args):
            blob,t=fake_get(*args)
            if args[2]=="data.sec.gov":
                x=json.loads(blob);x["filings"]["recent"]["acceptanceDateTime"][0]="2026-11-12T15:00:00"
                x["filings"]["recent"]["form"][0]="8-K"
                return json.dumps(x).encode(),t
            return blob,t
        r=c.sec_snapshot("AMD",2488,CUTOFF,NOW,clock,getfn=fake)
        self.assertEqual(len(r["events"]),1)
        self.assertEqual(r["events"][0]["status"],"review_needed")
    def test_official_issuer_rss_coverage_from_before_window(self):
        x=c.issuer_rss("AMD",CUTOFF,NOW,clock,getfn=fake_get)
        self.assertEqual(x["events"],[])
        self.assertEqual(x["url"],c.ISSUER_RSS["AMD"][0])
    def test_new_frog_marvell_official_feeds_are_explicitly_allowlisted(self):
        self.assertEqual(c.ISSUER_RSS["FROG"],(
            "https://investors.jfrog.com/rss/pressrelease.aspx",
            "investors.jfrog.com"))
        self.assertEqual(c.ISSUER_RSS["MRVL"],(
            "https://investor.marvell.com/news-events/press-releases/rss",
            "investor.marvell.com"))
    def test_unknown_issuer_does_not_invent_ir_coverage(self):
        with self.assertRaisesRegex(c.SourceUnknown,"UNSUPPORTED_OFFICIAL"):
            c.issuer_rss("DDOG",CUTOFF,NOW,clock,getfn=fake_get)
    def test_news_empty_after_full_pagination_is_covered(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"alpaca_data_key_id").write_text("TEST")
            (Path(td)/"alpaca_data_secret").write_text("TEST")
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":td}):
                r=c.news_pages("AMD",CUTOFF,NOW,clock,getfn=fake_get)
        self.assertEqual(r["article_count"],0)
        self.assertEqual(r["events"],[])
        self.assertEqual(r["pages"],1)
    def test_positive_headline_is_not_automatically_cleared(self):
        def get_news(url,headers,host,clock):
            blob,t=fake_get(url,headers,host,clock)
            if host=="data.alpaca.markets":
                x={"news":[{"id":101,"symbols":["AMD"],"source":"benzinga",
                    "headline":"AMD signs partnership","created_at":"2026-11-13T19:20:00Z"}],
                   "next_page_token":None}
                return json.dumps(x).encode(),NOW
            return blob,t
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"alpaca_data_key_id").write_text("TEST")
            (Path(td)/"alpaca_data_secret").write_text("TEST")
            with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":td}):
                r=c.news_pages("AMD",CUTOFF,NOW,clock,getfn=get_news)
        self.assertEqual(r["events"][0]["status"],"review_needed")
    def test_three_real_source_shaped_fake_bundles_can_clear_only_no_events(self):
        def sec(*x):return c.sec_snapshot(*x,getfn=fake_get)
        def ir(*x):return c.issuer_rss(*x,getfn=fake_get)
        def news(*x,**kwargs):return {
            "raw_sha256":"a"*64,"received":NOW,"events":[],
            "url":c.ALPACA_BASE,"pages":1,"article_count":0}
        bundle=c.source_manifest("AMD",2488,NOW,clock,secfn=sec,irfn=ir,newsfn=news)
        self.assertEqual(len(bundle["evidence"]),0)
        clearance=eligible_bundle("AMD",bundle,NOW)
        self.assertEqual(clearance["producer"],"trusted_issuer_sec_news_attestor_v1")
        self.assertEqual(len(bundle["independent_source_receipts"]),3)
    def test_adverse_material_filing_requires_review_not_go(self):
        def sec(*x):
            y=c.sec_snapshot(*x,getfn=fake_get)
            y["events"].append({"published_at":"2026-11-13T19:00:00+00:00",
                "category":"dilution","status":"review_needed",
                "source_reference":"SEC:0000002488-26-000100","content_hash":"a"*64})
            return y
        def ir(*x):return c.issuer_rss(*x,getfn=fake_get)
        def news(*x,**kwargs):return {"raw_sha256":"a"*64,"received":NOW,"events":[],"url":c.ALPACA_BASE}
        bundle=c.source_manifest("AMD",2488,NOW,clock,secfn=sec,irfn=ir,newsfn=news)
        with self.assertRaises(EvidenceBlocked):eligible_bundle("AMD",bundle,NOW)
    def test_real_numeric_upgrade_with_unchanged_rating_is_nonadverse(self):
        a={"source":"fiscal.ai",
           "headline":"Morgan Stanley Adjusts Fortive Price Target to $65 from $59",
           "content":"Morgan Stanley analyst action regarding Fortive Corporation includes an upward revision of the price target to $65 from $59. The firm has maintained its Equalweight rating on the stock."}
        self.assertEqual(c.classify_news_article(a,"FTV","FORTIVE CORPORATION")[:2],
                         ("analyst_upgrade","verified_nonadverse"))
    def test_cannot_auto_clear_bad_news_from_price_target(self):
        a={"source":"fiscal.ai",
           "headline":"Morgan Stanley Adjusts Fortive Price Target to $65 from $59",
           "content":"Firm downgrades Fortive Corporation despite increasing target."}
        self.assertEqual(c.classify_news_article(a,"FTV","FORTIVE CORPORATION")[1],
                         "review_needed")
    def test_another_issuer_cannot_clear_target(self):
        a={"source":"fiscal.ai",
           "headline":"Morgan Stanley Adjusts Intel Price Target to $65 from $59",
           "content":"The firm has maintained its Equalweight rating on the stock."}
        self.assertEqual(c.classify_news_article(a,"FTV","FORTIVE CORPORATION")[1],
                         "review_needed")
    def test_two_corroborated_analyst_sources_can_be_nonadverse(self):
        benz={"id":1,"source":"benzinga",
              "headline":"Morgan Stanley Maintains Equal-Weight on JFrog, Raises Price Target to $114",
              "content":""}
        fiscal={"id":2,"source":"fiscal.ai",
              "headline":"Morgan Stanley Maintains Hold Rating and Raises Price Target for JFrog",
              "content":"Morgan Stanley issued update on JFrog, maintaining its 'Hold' rating on the shares. The firm raised its price target for JFrog to $114."}
        for x in (benz,fiscal):
            result=c.classify_news_article(x,"FROG","JFROG LTD.",[benz,fiscal])
            self.assertEqual(result[:2],("analyst_upgrade","verified_nonadverse"))
    def test_single_uncorroborated_headline_is_review_only(self):
        benz={"id":1,"source":"benzinga",
              "headline":"Morgan Stanley Maintains Equal-Weight on JFrog, Raises Price Target to $114",
              "content":""}
        self.assertEqual(c.classify_news_article(benz,"FROG","JFROG LTD.",[benz])[1],
                         "review_needed")
    def test_corrob_negative_rating_source_is_review_only(self):
        benz={"id":1,"source":"benzinga",
              "headline":"Morgan Stanley Maintains Equal-Weight on JFrog, Raises Price Target to $114",
              "content":""}
        fiscal={"id":2,"source":"fiscal.ai",
              "headline":"Morgan Stanley Maintains Hold Rating and Raises Price Target for JFrog",
              "content":"Morgan Stanley downgraded JFrog despite raising its price target for JFrog to $114."}
        self.assertEqual(c.classify_news_article(benz,"FROG","JFROG LTD.",[benz,fiscal])[1],
                         "review_needed")
    def test_no_order_transport_source(self):
        from pathlib import Path
        text=Path(c.__file__).read_text()
        for token in ("paper_api(", "/v2/orders", "requests.post(", "GenUI", "pushover"):
            self.assertNotIn(token,text)

if __name__=="__main__":unittest.main()
