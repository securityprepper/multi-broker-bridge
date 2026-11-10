import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from v2_news_event_evidence_archive import (
 EvidenceError, holiday_gate, capture, canonical_article, write_once)
NOW=datetime.fromisoformat("2026-11-10T22:38:50+00:00")
GATE={"timezone":"America/Chicago","paused":False,"calendar_coverage_ok":True,
      "calendar_revision":"2","next_check_at":"2026-11-13T16:13:00-06:00",
      "calendar_coverage_through":"2036-10-25"}
A={"news_id":"12345","published_at_utc":"2026-11-10T22:38:15+00:00",
   "observed_at_utc":"2026-11-10T22:38:24+00:00","headline":"Company Q3 earnings",
   "symbols":["ABC"],"category":"EARNINGS_RELEASE_CANDIDATE_UNVERIFIED",
   "source":"benzinga","realtime_fresh":True,"latency_seconds":9}
def fixture(root, now=NOW, news=A):
 p=Path(root);f={"asof_utc":(now-timedelta(seconds=25)).isoformat(),
    "source":"Alpaca GET news, possibly delayed","broker_read_only":True,
    "orders_submitted":0,"recent":[news]}
 (p/"feed.json").write_text(json.dumps(f));(p/"gate.json").write_text(json.dumps(GATE))
 return p/"feed.json",p/"gate.json",p/"evidence"
class Tests(unittest.TestCase):
 def test_gate(self): self.assertTrue(holiday_gate(GATE,NOW))
 def test_pause_blocks(self):
  self.assertFalse(holiday_gate(dict(GATE,paused=True),NOW))
 def test_expired_boundary(self):
  self.assertFalse(holiday_gate(GATE,datetime.fromisoformat("2026-11-13T22:13:00+00:00")))
 def test_wrong_timezone(self):
  self.assertFalse(holiday_gate(dict(GATE,timezone="UTC"),NOW))
 def test_bad_coverage(self):
  self.assertFalse(holiday_gate(dict(GATE,calendar_coverage_through="2026-11-09"),NOW))
 def test_baseline_not_prospective(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d);r=capture(feed,gate,out,NOW)
   self.assertEqual(r["prospective_new"],0)
   self.assertEqual(r["created"],1)
 def test_new_prospective(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   capture(feed,gate,out,NOW)
   later=NOW+timedelta(minutes=1)
   news=dict(A,news_id="12346",
     published_at_utc=(later-timedelta(seconds=35)).isoformat(),
     observed_at_utc=(later-timedelta(seconds=26)).isoformat())
   fixture(d,later,news)
   r=capture(feed,gate,out,later)
   self.assertEqual(r["prospective_new"],1)
 def test_duplicate_id_with_changed_observation_keeps_earliest(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   later=dict(A,observed_at_utc="2026-11-10T22:38:26+00:00",
     latency_seconds=11,realtime_fresh=False)
   raw=json.loads(feed.read_text())
   raw["recent"]=[later,dict(A)]
   feed.write_text(json.dumps(raw))
   result=capture(feed,gate,out,NOW)
   self.assertEqual(result["created"],1)
   self.assertEqual(result["revision_created"],1)
   main=[p for p in out.glob("20*/*.json") if ".rev." not in p.name][0]
   self.assertEqual(json.loads(main.read_text())["article"]["observed_at_utc"],
                    "2026-11-10T22:38:24+00:00")
 def test_replay_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   capture(feed,gate,out,NOW)
   r=capture(feed,gate,out,NOW)
   self.assertEqual((r["created"],r["existing"]),(0,1))
 def test_conflicting_id_seals_revision_without_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d);capture(feed,gate,out,NOW)
   first=list(out.glob("20*/*.json"))[0]
   original=first.read_bytes()
   fixture(d,NOW,dict(A,headline="CONFLICT"))
   result=capture(feed,gate,out,NOW)
   self.assertEqual(result["revision_created"],1)
   self.assertEqual(first.read_bytes(),original)
   revision=list(out.glob("20*/*.rev.*.json"))[0]
   self.assertFalse(json.loads(revision.read_text())["prospective_archive"])
 def test_future_article_rejected(self):
  with self.assertRaises(EvidenceError):
   canonical_article(dict(A,observed_at_utc="2026-11-11T00:00:00Z"),NOW)
 def test_stale_feed_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   with self.assertRaises(EvidenceError): capture(feed,gate,out,NOW+timedelta(minutes=4))
 def test_no_broker_feed(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   x=json.loads(feed.read_text());x["orders_submitted"]=1;feed.write_text(json.dumps(x))
   with self.assertRaises(EvidenceError): capture(feed,gate,out,NOW)
 def test_no_trade_or_issuer_claim(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d);capture(feed,gate,out,NOW)
   events=list(out.glob("20*/*.json"));self.assertEqual(len(events),1)
   x=json.loads(events[0].read_text())
   self.assertFalse(x["trade_authorized"]);self.assertFalse(x["issuer_verified"])
   self.assertEqual(x["orders_submitted"],0)
 def test_paused_zero_writes(self):
  with tempfile.TemporaryDirectory() as d:
   feed,gate,out=fixture(d)
   (Path(d)/"gate.json").write_text(json.dumps(dict(GATE,paused=True)))
   r=capture(feed,gate,out,NOW)
   self.assertEqual(r["created"],0);self.assertFalse(out.exists())
if __name__=="__main__":
 unittest.main()
