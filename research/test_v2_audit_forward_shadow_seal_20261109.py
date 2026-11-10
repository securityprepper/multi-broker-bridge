"""Offline, read-only provenance regression tests for V2 forward snapshots."""
import json,os,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta,timezone
try:
 from research import v2_audit_forward_shadow_seal_20261109 as audit
except ModuleNotFoundError:
 import v2_audit_forward_shadow_seal_20261109 as audit
UTC=timezone.utc

def sample():
 obs=datetime.fromisoformat("2026-11-10T09:35:25-05:00")
 doc={"schema_version":1,"time_of_observation_utc":obs.astimezone(UTC).isoformat(),
      "time_of_observation_ET":obs.isoformat(),"forecast_slot_ET":"09:35",
      "earliest_later_entry_at_ET":(obs+timedelta(minutes=5)).isoformat(),
      "source":"Alpaca SIP 5Min completed bars, GET-only",
      "research_only":True,"no_current_or_future_outcomes_in_document":True,
      "orders_submitted":0,"PAPER_orders_allowed":False,"LIVE_orders_allowed":False,"sectors":{}}
 for sector,names in audit.EXPECTED.items():
  features={name:{"observed_price":100.0,
                  "observed_bar_end_ET":"2026-11-10T09:35:00-05:00",
                  "from_0930_open_pct":-0.30,"last_5m_pct":-0.10} for name in names}
  doc["sectors"][sector]={"status":"ASOF_FEATURES","features":features,
                          "shadow_classification":None}
 return doc,obs

class TestSeal(unittest.TestCase):
 def run_audit(self,doc,obs,delay=12):
  return audit.audit_snapshot(doc,obs+timedelta(seconds=delay))
 def test_normal(self):
  doc,t=sample()
  r=self.run_audit(doc,t)
  self.assertEqual(r["status"],"METADATA_WINDOW_AND_FEATURES_PASSED")
  self.assertEqual(r["sector_features"],7)
  self.assertFalse(r["cryptographically_immutable"])
 def test_future_creation(self):
  doc,t=sample()
  self.assertIn("FILE_NOT_SEALED_BEFORE_EARLIEST_ENTRY",self.run_audit(doc,t,301)["defects"])
 def test_beyond_completed_candle(self):
  doc,t=sample()
  doc["sectors"]["energy"]["features"]["XLE"]["observed_bar_end_ET"]="2026-11-10T09:40:00-05:00"
  self.assertIn("BAR_NOT_KNOWN_AT_OBSERVATION:XLE",self.run_audit(doc,t)["defects"])
 def test_stale(self):
  doc,t=sample()
  doc["sectors"]["software"]["features"]["IGV"]["observed_bar_end_ET"]="2026-11-10T09:25:00-05:00"
  self.assertIn("STALE_BAR:IGV",self.run_audit(doc,t)["defects"])
 def test_no_orders(self):
  doc,t=sample()
  doc["PAPER_orders_allowed"]=True
  self.assertIn("NONZERO_ORDER_PERMISSION",self.run_audit(doc,t)["defects"])
 def test_bearish_label_supported(self):
  doc,t=sample()
  f=doc["sectors"]["semiconductors"]["features"]
  f["SOXX"]["from_0930_open_pct"]=-.9
  doc["sectors"]["semiconductors"]["shadow_classification"]="EXPLORATORY_BEARISH_SEMI_WATCH_ONLY"
  self.assertEqual(self.run_audit(doc,t)["status"],"METADATA_WINDOW_AND_FEATURES_PASSED")
 def test_bearish_label_incorrect(self):
  doc,t=sample()
  doc["sectors"]["semiconductors"]["shadow_classification"]="EXPLORATORY_BEARISH_SEMI_WATCH_ONLY"
  self.assertIn("LABEL_NOT_SUPPORTED_BY_ASOF_FEATURES",self.run_audit(doc,t)["defects"])
 def test_missing_peer(self):
  doc,t=sample()
  del doc["sectors"]["financials"]["features"]["JPM"]
  self.assertIn("INCOMPLETE_ASOF_SECTOR:financials",self.run_audit(doc,t)["defects"])
 def test_abstention_not_data(self):
  doc,t=sample()
  doc["sectors"]["gold_miners"]={"status":"ABSTAIN_MISSING_ASOF_DATA","features":{},"shadow_classification":None}
  r=self.run_audit(doc,t)
  self.assertEqual((r["sector_features"],r["sector_abstentions"]),(6,1))
 def test_path_date(self):
  doc,t=sample()
  r=audit.audit_snapshot(doc,t+timedelta(seconds=12),Path("/tmp/2026-11-09/0935.json"))
  self.assertIn("PATH_DATE_OR_SLOT_MISMATCH",r["defects"])
 def test_early_mtime(self):
  doc,t=sample()
  self.assertIn("FILE_PRECEDES_REPORTED_OBSERVATION",self.run_audit(doc,t,-10)["defects"])
 def test_read_only_file(self):
  doc,t=sample()
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/"2026-11-10"/"0935.json"
   p.parent.mkdir();p.write_text(json.dumps(doc))
   tm=(t+timedelta(seconds=12)).timestamp()
   os.utime(p,(tm,tm))
   before=p.stat().st_mtime_ns
   r=audit.audit_file(p)
   self.assertEqual(r["status"],"METADATA_WINDOW_AND_FEATURES_PASSED")
   self.assertEqual(p.stat().st_mtime_ns,before)
   self.assertEqual(len(r["snapshot_sha256_for_reconciliation"]),64)
 def test_symlink_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   p=Path(root)/"real.json";p.write_text("{}")
   l=Path(root)/"link.json";l.symlink_to(p)
   self.assertEqual(audit.audit_file(l)["status"],"REJECTED_FAIL_CLOSED")

if __name__=="__main__":unittest.main()
