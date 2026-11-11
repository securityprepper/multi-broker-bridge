"""Synthetic deterministic contract tests; no network, broker or production file writes."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from hashlib import sha256
import json
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from research import v2_forward_shadow_integrity_verify_20261111 as v

ET=ZoneInfo("America/New_York")
DAY="2026-11-12"
POLICY_SHA=v.POLICY_SHA256

def local(hm,seconds=25):
    h,m=map(int,hm.split(":"))
    return datetime(2026,11,12,h,m,seconds,tzinfo=ET)

def create_day(root):
    events=[]
    source={}
    for slot in v.SLOTS:
        dt=local(slot)
        sectors={}
        for sec in v.SECTORS:
            side="ABSTAIN" if sec=="healthcare" else "UP"
            mark=None if side=="ABSTAIN" else 100.0
            f={"sector":sec,"etf":"ETF","policy_id":v.POLICY,
               "policy_sha256":POLICY_SHA,
               "signal_recorded_at_ET":dt.isoformat(),
               "signal_source_bar_end_ET":dt.replace(second=0).isoformat() if mark else None,
               "benchmark_side":side,"peer_confirmed_side":side,
               "signal_mark":mark,"orders_authorized":False,
               "alerts_authorized":False}
            sectors[sec]={"forward_forecast":f,"shadow_classification":side,
                          "peer_confirmed_classification":side}
        d={"schema_version":2,"time_of_observation_ET":dt.isoformat(),
           "forecast_actual_issued_at_ET":dt.isoformat(),
           "forecast_slot_ET":slot,"forecast_policy_id":v.POLICY,
           "forecast_policy_sha256":POLICY_SHA,
           "research_only":True,"no_current_or_future_outcomes_in_document":True,
           "PAPER_orders_allowed":False,"LIVE_orders_allowed":False,
           "orders_submitted":0,"sectors":sectors}
        filename=root/DAY/(slot.replace(":","")+".json")
        filename.parent.mkdir(exist_ok=True)
        raw=(json.dumps(d,sort_keys=True)+"\n").encode()
        filename.write_bytes(raw)
        digest=sha256(raw).hexdigest()
        source[slot]=(d,digest)
        event={"status":"RESEARCH_SHADOW_SEALED","day":DAY,"slot":slot,
               "sealed_file_sha256":digest,"orders_submitted":0}
        ts=dt+timedelta(seconds=2)
        events.append({"MESSAGE":json.dumps(event),
                       "__REALTIME_TIMESTAMP":str(int(ts.timestamp()*1_000_000))})
    rows=[]
    for slot in v.SLOTS:
        d,digest=source[slot]
        for sec in v.SECTORS:
            f=d["sectors"][sec]["forward_forecast"]
            for arm in v.ARMS:
                for horizon in v.HORIZONS:
                    end=v.first_completed_bar_at_or_after(local(slot)+timedelta(hours=1)) if horizon=="60m" else local("14:40",seconds=0)
                    if sec=="healthcare":
                        signed=None; net30=None;net60=None;label="ABSTAIN";future=101.
                    else:
                        signed=1.; net30=.7;net60=.4;label="HIT";future=101.
                    rows.append({"slot_ET":slot,"sector":sec,"etf":"ETF","arm":arm,
                                "horizon":horizon,"forecast":f[arm],
                                "policy_id":v.POLICY,"policy_sha256":POLICY_SHA,
                                "signal_issued_at_ET":f["signal_recorded_at_ET"],
                                "signal_bar_end_ET":f["signal_source_bar_end_ET"],
                                "source_document_sha256":digest,
                                "signal_mark":f["signal_mark"],
                                "future_at_ET":end.isoformat(),
                                "future_mark":future,
                                "direction":label,"signed_return_pct":signed,
                                "modeled_after_30bp_pct":net30,
                                "modeled_after_60bp_pct":net60})
    outcome={"schema_version":1,"research_only":True,"orders_submitted":0,
             "PAPER_orders_allowed":False,"LIVE_orders_allowed":False,
             "capture_complete":True,"forecast_policy_id":v.POLICY,
             "forecast_policy_sha256":POLICY_SHA,"sealed_slots":sorted(v.SLOTS),
             "scored_at_ET":local("14:51").isoformat(),
             "scores":rows}
    output=root/"scores"/DAY/"1340CT.json"
    output.parent.mkdir(parents=True)
    output.write_text(json.dumps(outcome,sort_keys=True)+"\n")
    return events,output

class Tests(unittest.TestCase):
    def setUp(self):
        self.context=tempfile.TemporaryDirectory()
        self.root=Path(self.context.name)
        self.events,self.scored=create_day(self.root)
    def tearDown(self):
        self.context.cleanup()
    def test_valid_complete_forecasts_and_future_scores(self):
        d=v.verify(self.root,DAY,self.events)
        self.assertEqual(d["status"],"PASS_SOURCE_AND_SCORE_AGREE")
        self.assertEqual(d["forecast_outcome_rows_verified"],84)
        self.assertEqual(d["broker_orders"],0)
    def test_source_only_before_outcomes_is_not_claimed_profit(self):
        d=v.verify(self.root,DAY,self.events,require_score=False)
        self.assertEqual(d["status"],"PASS_ISSUANCE_ONLY_OUTCOMES_PENDING")
    def test_original_old_schema_not_rewritten(self):
        with self.assertRaises(v.AuditError):
            v.verify(self.root,"2026-11-11",self.events,require_score=False)
    def test_missing_initial_receipt_fails_closed(self):
        with self.assertRaisesRegex(v.AuditError,"missing or duplicate"):
            v.verify(self.root,DAY,self.events[:2])
    def test_duplicate_initial_receipt_fails_closed(self):
        with self.assertRaisesRegex(v.AuditError,"missing or duplicate"):
            v.verify(self.root,DAY,self.events+self.events[:1])
    def test_root_symlink_rejected(self):
        link=self.root/"alias"
        link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(v.AuditError):
            v.verify(link,DAY,self.events)
    def test_tampered_original_file_detected_by_journal_hash(self):
        p=self.root/DAY/"0935.json"
        d=json.loads(p.read_text())
        d["sectors"]["energy"]["forward_forecast"]["signal_mark"]=199.
        p.write_text(json.dumps(d,sort_keys=True)+"\n")
        with self.assertRaisesRegex(v.AuditError,"hash differs"):
            v.verify(self.root,DAY,self.events)
    def test_bad_journal_timestamp_after_outcome(self):
        self.events[0]["__REALTIME_TIMESTAMP"]=str(int(local("11:00").timestamp()*1e6))
        with self.assertRaisesRegex(v.AuditError,"journal seal"):
            v.verify(self.root,DAY,self.events)
    def test_bad_journal_hash_fails(self):
        msg=json.loads(self.events[0]["MESSAGE"])
        msg["sealed_file_sha256"]="0"*64
        self.events[0]["MESSAGE"]=json.dumps(msg)
        with self.assertRaisesRegex(v.AuditError,"hash differs"):
            v.verify(self.root,DAY,self.events)
    def test_broker_orders_are_not_accepted_in_journal(self):
        msg=json.loads(self.events[0]["MESSAGE"])
        msg["orders_submitted"]=1
        self.events[0]["MESSAGE"]=json.dumps(msg)
        with self.assertRaisesRegex(v.AuditError,"broker orders"):
            v.verify(self.root,DAY,self.events)
    def test_score_future_only_not_priorclose(self):
        obj=json.loads(self.scored.read_text())
        obj["scores"][0]["signed_return_pct"]=4.0
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"prior price movement"):
            v.verify(self.root,DAY,self.events)
    def test_tiny_not_a_hit(self):
        obj=json.loads(self.scored.read_text())
        r=obj["scores"][0]
        r["future_mark"]=100.01
        r["signed_return_pct"]=.01
        r["modeled_after_30bp_pct"]=-.29
        r["modeled_after_60bp_pct"]=-.59
        r["direction"]="HIT"
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"tiny"):
            v.verify(self.root,DAY,self.events)
    def test_score_broker_permission_not_allowed(self):
        obj=json.loads(self.scored.read_text())
        obj["PAPER_orders_allowed"]=True
        self.scored.write_text(json.dumps(obj))
        with self.assertRaises(v.AuditError):
            v.verify(self.root,DAY,self.events)
    def test_score_unavailable_does_not_claim_pass(self):
        self.scored.unlink()
        with self.assertRaisesRegex(v.AuditError,"missing sealed"):
            v.verify(self.root,DAY,self.events)
    def test_score_duplicate_row_rejected(self):
        obj=json.loads(self.scored.read_text())
        obj["scores"][0]=obj["scores"][1].copy()
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"duplicate"):
            v.verify(self.root,DAY,self.events)
    def test_score_prior_to_future_fails(self):
        obj=json.loads(self.scored.read_text())
        obj["scored_at_ET"]=local("10:00").isoformat()
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"too early"):
            v.verify(self.root,DAY,self.events)
    def test_abstain_wrongly_credited_fails(self):
        obj=json.loads(self.scored.read_text())
        r=next(x for x in obj["scores"] if x["sector"]=="healthcare")
        r["direction"]="HIT"
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"abstention"):
            v.verify(self.root,DAY,self.events)
    def test_horizon_follows_actual_issue_not_schedule_start(self):
        target=v.first_completed_bar_at_or_after(local("09:35")+timedelta(minutes=60))
        self.assertEqual(target,local("10:40",seconds=0))
    def test_improper_slot_plus_60_minute_scoring_is_rejected(self):
        obj=json.loads(self.scored.read_text())
        row=next(r for r in obj["scores"] if r["slot_ET"]=="09:35" and r["horizon"]=="60m")
        row["future_at_ET"]=local("10:35",seconds=0).isoformat()
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"horizon"):
            v.verify(self.root,DAY,self.events)
    def test_wrong_horizon_fails(self):
        obj=json.loads(self.scored.read_text())
        obj["scores"][0]["future_at_ET"]=local("11:41").isoformat()
        self.scored.write_text(json.dumps(obj))
        with self.assertRaisesRegex(v.AuditError,"horizon"):
            v.verify(self.root,DAY,self.events)

if __name__=="__main__":
    unittest.main()
