"""SRM hourly-report integrity: broker-free, source-read-only November 19, 2026."""
import copy, datetime as dt, importlib.util, json, pathlib, sys, tempfile, unittest
from unittest.mock import patch
UTC=dt.timezone.utc
src="/opt/securityprepper/sustained-riser-monitor/monitor.py"
spec=importlib.util.spec_from_file_location("srm_research_20261119",src)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def scan(now,active=True):
  return {
    "id":654321, "asof":now.isoformat(),"feed":"sip",
    "signals":{"qualified":[],"sustained_riser_research_leads":([{
       "symbol":"AMD","signal":"SUSTAINED_RISER_RESEARCH_V1",
       "sustained_60m_verified":True,"trend_window_minutes":60,
       "complete_positive_volume_1m_bars":61,"rising_5m_intervals":10,
       "positive_15m_segments":4,
       "latest_price":150.0,"latest_price_asof_utc":now.isoformat(),
       "observed_at_utc":now.isoformat(),"feed_kind":"sip",
       "p5":.2,"p10":.5,"p30":.9,"p60":1.7
    }] if active else [])}
  }

class SRMSourceIntegrity(unittest.TestCase):
  def setUp(self):
    self.now=dt.datetime(2026,11,19,17,30,tzinfo=UTC)
  def test_expired_gate_accepted_proven(self):
    with tempfile.TemporaryDirectory() as tmp:
      gate=pathlib.Path(tmp)/"gate.json"
      gate.write_text(json.dumps({
         "schema_version":1,"status_valid":True,"timezone":"America/Chicago",
         "calendar_coverage_ok":True,"calendar_coverage_through":"2036-10-25",
         "calendar_revision":"3300","paused":False,
         "next_check_at":"2026-11-20T22:07:00+00:00",
         "published_at":"2026-11-19T11:00:00-06:00",
         "valid_until":"2026-11-19T11:02:30-06:00"
      }))
      with patch.object(m,"GATE",gate):
        ok,why=m.authorized_gate(self.now)
      self.assertTrue(ok)   # security regression currently present
      self.assertEqual(why,"GATE_VALID")
  def test_blocked_handoff_not_durable_but_reserved(self):
    sys.path.insert(0,"/opt/securityprepper/watcher-paper")
    import watcher_event
    with tempfile.TemporaryDirectory() as tmp:
      root=pathlib.Path(tmp);pub=root/"public"/"latest.json";pub.parent.mkdir()
      now=self.now; s=[scan(now)]
      with patch.object(m,"ROOT",root),patch.object(m,"PUBLIC",pub),\
           patch.object(m,"authorized_gate",return_value=(True,"GATE_VALID")),\
           patch.object(m,"latest_scan",side_effect=lambda:s[0]),\
           patch.object(m,"read_financials",return_value={}),\
           patch.object(watcher_event,"emit",return_value={"status":"NOT_COMMISSIONED"}):
        out0=m.run(now,notify=True)
        later=now+dt.timedelta(minutes=1);s[0]=scan(later)
        out1=m.run(later,notify=True)
      self.assertEqual(out0["alerts"],0)
      self.assertEqual(out1["alerts"],1)
      self.assertEqual(out1["order_handoffs"][0]["status"],"NOT_COMMISSIONED")
      self.assertEqual(len(list(root.glob("sustained-alerts-*.jsonl"))),0)
      self.assertEqual(json.loads((root/"state.json").read_text())["episodes"]["AMD"]["last_alerted_hour"],1)
      self.assertEqual(len(json.loads((root/"latest.json").read_text())["alerts"]),1)
  def test_single_missing_scan_still_continues_old_episode(self):
    s={}
    for minute in range(60):
       at=self.now+dt.timedelta(minutes=minute)
       picks,status=m.decide(scan(at),at,s)
       for item in picks:s["episodes"]["AMD"]["last_alerted_hour"]=item["consecutive_hours"]
    # Scan 60 has no verified sustained lead; this must break continuity per owner's rules.
    missing=self.now+dt.timedelta(minutes=60)
    m.decide(scan(missing,False),missing,s)
    resumed=self.now+dt.timedelta(minutes=61)
    picks,_=m.decide(scan(resumed),resumed,s)
    self.assertEqual(s["episodes"]["AMD"]["hours_verified"],2) # bug: counts across missing scan
    self.assertEqual(picks[0]["consecutive_hours"],2)
    self.assertEqual(s["episodes"]["AMD"]["misses"],0)

if __name__=='__main__':unittest.main(verbosity=2)
