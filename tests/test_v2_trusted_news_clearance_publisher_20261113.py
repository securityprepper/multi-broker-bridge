"""Tests never touch live clearance directory or submit orders."""
import json,os,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from recommendation_paper_bridge.news_eligibility import CATEGORIES,CLEAR,yesterday_today_start
from recommendation_paper_bridge.news_clearance import require_clear
from recommendation_paper_bridge.news_clearance_publisher import process,eligible_bundle,EvidenceBlocked
NOW=datetime(2026,11,13,15,40,tzinfo=timezone.utc)
SYM="AMD";CIK="0000002488";DIG="a"*64
def ts(offset=0):return (NOW+timedelta(seconds=offset)).isoformat()
def build():
    coverage=[]
    for src in ("sec_edgar","issuer_ir","licensed_news"):
        coverage.append({"symbol":SYM,"issuer_cik":CIK,"source":src,
          "verified_complete":True,"first_observed_at":ts(-4),
          "coverage_since":yesterday_today_start(NOW).isoformat(),
          "coverage_through":ts(-1),
          "source_reference":"source:"+src,"content_hash":DIG,
          "categories":list(CATEGORIES)})
    receipts={k:{"verified_original_snapshot":True,
          "provider_reference":"source:"+k,"original_receipt_sha256":DIG,
          "received_at_utc":ts(-4),
          "coverage_since_utc":yesterday_today_start(NOW).isoformat(),
          "coverage_through_utc":ts(-1),
          "full_pagination_or_feed_coverage_proven":True}
          for k in ("sec_edgar","issuer_ir","licensed_news")}
    return {"schema_version":1,"source_scope":"COMPLETE_INDEPENDENT_YESTERDAY_TODAY_ISSUER_SEC_LICENSED_NEWS",
      "window_timezone":"America/Chicago",
      "screening_start_utc":yesterday_today_start(NOW).isoformat(),
      "symbol":SYM,"issuer_cik":CIK,"exchange":"NASDAQ",
      "fresh_collector_observed_at_utc":ts(-4),
      "identity":{"verified":True,"symbol":SYM,"issuer_cik":CIK,
                  "exchange":"NASDAQ","first_observed_at":ts(-100)},
      "coverage":coverage,"evidence":[],
      "independent_source_receipts":receipts}
def holiday():
    return {"timezone":"America/Chicago","calendar_revision":2,"paused":False,
      "calendar_coverage_ok":True,"calendar_coverage_through":"2036-10-25",
      "next_check_at":ts(300)}
class Publisher(unittest.TestCase):
    def setup_dir(self,source_data=None,paused=False):
        ctx=tempfile.TemporaryDirectory()
        base=Path(ctx.name);src=base/"source";out=base/"clear"
        src.mkdir(mode=0o700);out.mkdir(mode=0o700)
        status=base/"status.json";gate=base/"gate.json"
        conf=holiday();conf["paused"]=paused
        gate.write_text(json.dumps(conf))
        if source_data is not None:
            (src/(SYM+".json")).write_text(json.dumps(source_data))
        return ctx,src,out,gate,status
    def test_no_source_does_not_create_clear_file(self):
        ctx,src,out,gate,status=self.setup_dir()
        with ctx:
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["files_published"],0)
            self.assertTrue(status.exists())
            self.assertEqual(list(out.iterdir()),[])
    def test_synthetic_fully_verified_bundle_produces_valid_clear(self):
        ctx,src,out,gate,status=self.setup_dir(build())
        with ctx:
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["files_published"],1)
            raw=(out/"AMD.json").read_bytes();doc=json.loads(raw)
            from hashlib import sha256
            proof=require_clear("AMD",NOW,loader=lambda s:(doc,sha256(raw).hexdigest()))
            self.assertEqual(proof["status"],CLEAR)
            self.assertEqual(doc["producer"],"trusted_issuer_sec_news_attestor_v1")
    def test_no_clear_if_missing_independent_issuer(self):
        a=build();del a["independent_source_receipts"]["issuer_ir"]
        ctx,src,out,gate,status=self.setup_dir(a)
        with ctx:
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["files_published"],0)
            self.assertEqual(list(out.iterdir()),[])
    def test_adverse_news_never_produces_clearance(self):
        a=build();a["evidence"]=[{"symbol":SYM,"issuer_cik":CIK,
          "source":"licensed_news","published_at":ts(-30),
          "first_observed_at":ts(-29),"source_reference":"source:negative",
          "content_hash":DIG,"category":"guidance","status":"material_adverse_verified"}]
        ctx,src,out,gate,status=self.setup_dir(a)
        with ctx:
            self.assertEqual(process(now=NOW,source=src,output=out,gate=gate,status=status)["files_published"],0)
    def test_issuer_identity_mismatch_blocks(self):
        a=build();a["identity"]["issuer_cik"]="0000000001"
        with self.assertRaisesRegex(EvidenceBlocked,"NOT_NEWS_CLEAR"):
            eligible_bundle(SYM,a,NOW)
    def test_missing_original_receipt_blocks(self):
        a=build();a["independent_source_receipts"]["sec_edgar"]["full_pagination_or_feed_coverage_proven"]=False
        with self.assertRaisesRegex(EvidenceBlocked,"SOURCE_ORIGINAL"):
            eligible_bundle(SYM,a,NOW)
    def test_stale_source_capture_blocks(self):
        a=build();a["fresh_collector_observed_at_utc"]=ts(-150)
        with self.assertRaisesRegex(EvidenceBlocked,"SOURCE_COLLECTION_NOT_FRESH"):
            eligible_bundle(SYM,a,NOW)
    def test_no_write_while_paused(self):
        ctx,src,out,gate,status=self.setup_dir(build(),paused=True)
        with ctx:
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["status"],"HOLIDAY_FAIL_CLOSED_NO_PUBLISH")
            self.assertEqual(list(out.iterdir()),[])
    def test_symlink_source_never_accepted(self):
        ctx,src,out,gate,status=self.setup_dir(build())
        with ctx:
            target=src/(SYM+".json")
            real=src/"real.txt"
            real.write_text(target.read_text());target.unlink();target.symlink_to(real)
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["files_published"],0)
    def test_untrusted_source_mode_blocks(self):
        ctx,src,out,gate,status=self.setup_dir(build())
        with ctx:
            f=src/(SYM+".json");f.chmod(0o666)
            r=process(now=NOW,source=src,output=out,gate=gate,status=status)
            self.assertEqual(r["files_published"],0)
    def test_reject_old_30day_scope_legacy(self):
        a=build()
        a["source_scope"]="COMPLETE_INDEPENDENT_30D_ISSUER_SEC_LICENSED_NEWS"
        with self.assertRaisesRegex(EvidenceBlocked,"YESTERDAY_TODAY_SOURCE_SCOPE"):
            eligible_bundle(SYM,a,NOW)
    def test_window_start_must_match_chicago_yesterday(self):
        a=build()
        a["screening_start_utc"]=ts(-24*3600)
        with self.assertRaisesRegex(EvidenceBlocked,"SCREENING_WINDOW_NOT_YESTERDAY_TODAY"):
            eligible_bundle(SYM,a,NOW)
    def test_issuer_IR_coverage_missing_first_hour_of_yesterday_rejected(self):
        a=build()
        a["independent_source_receipts"]["issuer_ir"]["coverage_since_utc"]=ts(-24*3600)
        with self.assertRaisesRegex(EvidenceBlocked,"SOURCE_ORIGINAL_RECEIPT_INCOMPLETE"):
            eligible_bundle(SYM,a,NOW)
    def test_cannot_place_broker_orders(self):
        from recommendation_paper_bridge.news_clearance_publisher import __file__ as source
        text=Path(source).read_text()
        for bad in ("paper_api(", "requests.post(", "urlopen(", "/v2/orders", "GenUI", "LIVE_ORDERS"):
            self.assertNotIn(bad,text)
if __name__=="__main__": unittest.main()
