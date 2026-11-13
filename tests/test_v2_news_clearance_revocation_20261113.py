"""Publisher must revoke stale, adverse, or absent source attestations immediately."""
import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from recommendation_paper_bridge.news_clearance_publisher import process
from test_v2_nonadverse_analyst_revision_20261113 import bundle
NOW=datetime(2026,11,13,21,0,tzinfo=timezone.utc)
def gate():
 return {"timezone":"America/Chicago","paused":False,
   "calendar_coverage_ok":True,"calendar_revision":2,
   "next_check_at":(NOW+timedelta(minutes=20)).isoformat(),
   "calendar_coverage_through":"2026-11-15"}
class Revoke(unittest.TestCase):
 def setup_sources(self):
  ctx=tempfile.TemporaryDirectory();base=Path(ctx.name)
  src=base/"source";out=base/"clear";src.mkdir();out.mkdir()
  g=base/"gate.json";g.write_text(json.dumps(gate()))
  source=bundle("verified_nonadverse")
  # synthetic source requires exactly verifiable original receipt metadata
  x={"schema_version":1,"source_scope":"COMPLETE_INDEPENDENT_YESTERDAY_TODAY_ISSUER_SEC_LICENSED_NEWS",
     "window_timezone":"America/Chicago","screening_start_utc":"2026-11-12T06:00:00+00:00",
     "symbol":"FTV","exchange":"NYSE","issuer_cik":"0001659166",
     "identity":source["identity"],"coverage":source["coverage"],
     "evidence":source["evidence"],
     "fresh_collector_observed_at_utc":(NOW-timedelta(seconds=5)).isoformat(),
     "independent_source_receipts":{k:{"verified_original_snapshot":True,
       "provider_reference":"SYNTHETIC:"+k,"original_receipt_sha256":"a"*64,
       "received_at_utc":(NOW-timedelta(seconds=4)).isoformat(),
       "coverage_since_utc":"2026-11-12T06:00:00+00:00",
       "coverage_through_utc":(NOW-timedelta(seconds=2)).isoformat(),
       "full_pagination_or_feed_coverage_proven":True}
      for k in ("issuer_ir","sec_edgar","licensed_news")}}
  (src/"FTV.json").write_text(json.dumps(x))
  return ctx,src,out,g
 def test_stale_issuer_collection_revokes_earlier_clearance(self):
  ctx,src,out,g=self.setup_sources()
  with ctx:
   first=process(now=NOW,source=src,output=out,gate=g,status=None)
   self.assertEqual(first["files_published"],1)
   self.assertTrue((out/"FTV.json").exists())
   stale=process(now=NOW+timedelta(seconds=110),source=src,output=out,gate=g,status=None)
   self.assertEqual(stale["files_published"],0)
   self.assertEqual(stale["revoked_symbols"],["FTV"])
   self.assertFalse((out/"FTV.json").exists())
 def test_missing_source_revokes_earlier_clearance(self):
  ctx,src,out,g=self.setup_sources()
  with ctx:
   self.assertEqual(process(now=NOW,source=src,output=out,gate=g,status=None)["files_published"],1)
   (src/"FTV.json").unlink()
   outcom=process(now=NOW+timedelta(seconds=5),source=src,output=out,gate=g,status=None)
   self.assertEqual(outcom["revoked_symbols"],["FTV"])
   self.assertFalse((out/"FTV.json").exists())
 def test_adverse_source_revokes_earlier_clearance(self):
  ctx,src,out,g=self.setup_sources()
  with ctx:
   self.assertEqual(process(now=NOW,source=src,output=out,gate=g,status=None)["files_published"],1)
   path=src/"FTV.json";x=json.loads(path.read_text())
   x["evidence"][0]["status"]="material_adverse_verified"
   path.write_text(json.dumps(x))
   outcom=process(now=NOW+timedelta(seconds=6),source=src,output=out,gate=g,status=None)
   self.assertEqual(outcom["revoked_symbols"],["FTV"])
   self.assertFalse((out/"FTV.json").exists())
if __name__=="__main__":unittest.main()
