"""Synthetic only, no broker/SEC network requests."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import unittest

modpath=str(Path(__file__).resolve().parents[1]/"research"/"v2_material_cyber_8k_source_gate_20261111.py")
spec=importlib.util.spec_from_file_location("v2cyber",modpath)
cyber=importlib.util.module_from_spec(spec);spec.loader.exec_module(cyber)
BASE={"form":"8-K","items":"1.05,9.01",
      "accession":"0001388658-26-000055","issuer_cik":"0001388658",
      "acceptance_at":"2026-06-15T20:30:17.000Z"}
def row(**extra):
    x=dict(BASE);x.update(extra);return x
ASOF="2026-06-16T13:30:00Z"
def original(**extra):
    content="First observed original SEC content"
    x=row(first_observed_at="2026-06-15T20:30:20Z",
          first_observed_content_sha256=sha256(content.encode()).hexdigest(),
          original_content=content)
    x.update(extra);return x

class TestAcceptedItem(unittest.TestCase):
    def test_valid_but_untradeable(self):
        s=cyber.source_status(original(),ASOF,"1388658")
        self.assertEqual(s["status"],"SOURCE_SNAPSHOT_VERIFIED_RESEARCH_ONLY")
        self.assertFalse(s["allowed_to_order"])
        self.assertFalse(s["allowed_to_notify"])
    def test_hist_sec_time_is_not_original_first_seen(self):
        self.assertEqual(cyber.source_status(row(),ASOF,"1388658")["status"],
                         "NO_ORIGINAL_FIRST_OBSERVED")
    def test_8ka_amendment_not_new(self):
        self.assertEqual(cyber.source_status(row(form="8-K/A"),ASOF,"1388658")["status"],
                         "AMENDMENT_NOT_NEW_ORIGINAL_EVENT")
    def test_8k_without_item_105(self):
        self.assertEqual(cyber.source_status(row(items="8.01,9.01"),ASOF,"1388658")["status"],
                         "NOT_ITEM_105")
    def test_11_05_not_confused(self):
        self.assertEqual(cyber.source_status(row(items="11.05"),ASOF,"1388658")["status"],
                         "NOT_ITEM_105")
    def test_issuer_mismatch(self):
        self.assertEqual(cyber.source_status(row(),ASOF,"1193125")["status"],"ISSUER_CIK_MISMATCH")
    def test_future_acceptance_not_known(self):
        self.assertEqual(cyber.source_status(row(), "2026-06-15T20:00:00Z", "1388658")["status"],
                         "FUTURE_ACCEPTANCE")
    def test_firstseen_before_sec_acceptance(self):
        self.assertEqual(cyber.source_status(original(first_observed_at="2026-06-15T20:20:20Z"),
                                             ASOF,"1388658")["status"],
                         "FIRST_OBSERVED_BEFORE_SEC_ACCEPTED")
    def test_first_seen_after_decision(self):
        self.assertEqual(cyber.source_status(original(first_observed_at="2026-06-17T10:00:00Z"),
                                             ASOF,"1388658")["status"],
                         "FUTURE_FIRST_OBSERVED")
    def test_firstseen_missing_hash(self):
        self.assertEqual(cyber.source_status(original(first_observed_content_sha256=None),
                                             ASOF,"1388658")["status"],
                         "NO_IMMUTABLE_ORIGINAL_CONTENT_DIGEST")
    def test_filing_rewritten_after_first_capture(self):
        self.assertEqual(cyber.source_status(original(original_content="later rewritten"),
                                             ASOF,"1388658")["status"],
                         "VERSION_HASH_MISMATCH")
    def test_naive_timestamps_rejected(self):
        self.assertEqual(cyber.source_status(original(first_observed_at="2026-06-15T20:30:20"),
                                             ASOF,"1388658")["status"],
                         "INVALID_OR_UNTRUSTED_SOURCE")
    def test_required_fields(self):
        a=row();a.pop("issuer_cik")
        self.assertEqual(cyber.source_status(a,ASOF,"1388658")["status"],
                         "INVALID_OR_UNTRUSTED_SOURCE")
    def test_sec_arrays_and_amendments(self):
        x={"form":["8-K","8-K/A","8-K","8-K"],
           "items":["1.05,9.01","1.05","8.01","11.05"],
           "accessionNumber":["0001388658-26-000055"]*4,
           "acceptanceDateTime":["2026-06-15T20:30:17.000Z"]*4}
        found=cyber.extract_recent(x,"1388658")
        self.assertEqual(len(found),2)
        self.assertEqual([v["form"] for v in found],["8-K","8-K/A"])
    def test_sec_array_partial_rejected(self):
        with self.assertRaises(ValueError):
            cyber.extract_recent({"form":["8-K"],"items":["1.05"],
                                  "accessionNumber":["abc"],"acceptanceDateTime":[]},"1388658")
    def test_sec_wrong_items_not_extracted(self):
        x={"form":["8-K"],"items":["1.050"],"accessionNumber":["0001388658-26-000055"],
           "acceptanceDateTime":["2026-06-15T20:30:17.000Z"]}
        self.assertEqual(cyber.extract_recent(x,"1388658"),[])

class TestSealed(unittest.TestCase):
    def report(self,slot,sect):
        return {"research_only":True,"orders_submitted":0,
                "no_current_or_future_outcomes_in_document":True,
                "forecast_slot_ET":slot,
                "sectors":sect}
    def test_features_not_forecasts(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"2026-11-10";p.mkdir()
            (p/"0935.json").write_text(json.dumps(self.report("09:35",{
                "semiconductors":{"status":"ASOF_FEATURES","shadow_classification":None},
                "gold_miners":{"status":"ABSTAIN_MISSING_ASOF_DATA","shadow_classification":None}})))
            s=cyber.sealed_progress(Path(d),("2026-11-10",))
            self.assertEqual(s["snapshots"],1)
            self.assertEqual(s["asof_feature_sector_slots"],1)
            self.assertEqual(s["actual_precommitted_forecast_sector_slots"],0)
            self.assertEqual(s["missing_slots"],2)
    def test_frozen_shadow_rule_is_only_real_forecast(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"2026-11-10";p.mkdir()
            (p/"0935.json").write_text(json.dumps(self.report("09:35",{
                "semiconductors":{"status":"ASOF_FEATURES",
                                  "shadow_classification":"EXPLORATORY_BEARISH_SEMI_WATCH_ONLY"}})))
            s=cyber.sealed_progress(Path(d),("2026-11-10",))
            self.assertEqual(s["actual_precommitted_forecast_sector_slots"],1)
    def test_future_outcome_in_shadow_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"2026-11-10";p.mkdir()
            x=self.report("09:35",{})
            x["no_current_or_future_outcomes_in_document"]=False
            (p/"0935.json").write_text(json.dumps(x))
            with self.assertRaises(ValueError):cyber.sealed_progress(Path(d),("2026-11-10",))
    def test_mismatched_slot_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"2026-11-10";p.mkdir()
            (p/"0935.json").write_text(json.dumps(self.report("09:45",{})))
            with self.assertRaises(ValueError):cyber.sealed_progress(Path(d),("2026-11-10",))
if __name__=="__main__":unittest.main()