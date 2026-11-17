import copy,sys,unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
sys.path.insert(0,"/opt/securityprepper/trading-dashboard")
import stop_watch
class Integration(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,17,5,tzinfo=timezone.utc);self.ts=self.now.isoformat();self.old={}
  self.run={"kind":"AGENTIC","account":"a","capture":"r","asof":self.ts,"pc":1,"oc":1}
  self.order=dict(account="a",capture="r",id="equity:1",symbol="AMD",side="sell",state="confirmed",qty=3,filled=1,stop=100,asof=self.ts,payload={"time_in_force":"gtc"})
  self.pos=[dict(account="RH:a",symbol="AMD",asset="EQUITY",qty=3,paper=False,broker="Robinhood",position_asof=self.ts)]
  self.quotes={"AMD":dict(price=99.9,asof=self.ts,stale=False)}
 def rows(self,table,*args):
  if table=="sp_robinhood_mcp_collection_runs":return [copy.deepcopy(self.run)]
  if table=="sp_robinhood_mcp_orders":return [copy.deepcopy(self.order)]
  return []
 def sql(self,q):
  return [{"payload":self.old}] if q.startswith("SELECT") else []
 def go(self):
  issues=[];result=stop_watch.watch(self.rows,self.sql,self.pos,self.quotes,self.now,issues);self.old=result;return result,issues
 @patch("stop_watch.push_report",return_value={"status":1,"request":"fake-receipt"})
 def test_delivery_persistence_dedup(self,push):
  a,_=self.go();self.assertEqual(a["entries"][0]["qty"],2);self.assertFalse(a["live_closing_enabled"])
  self.go();self.assertEqual(push.call_count,1);self.assertEqual(len(a["delivered"]),1)
 @patch("stop_watch.push_report",side_effect=[RuntimeError("network"),{"status":1,"request":"fake"}])
 def test_failed_send_retried(self,push):
  a,issues=self.go();self.assertEqual(a["delivered"],{});self.assertTrue(any("retry" in i for i in issues))
  b,_=self.go();self.assertEqual(push.call_count,2);self.assertEqual(len(b["delivered"]),1)
 @patch("stop_watch.push_report")
 def test_stale_order_capture_no_false_alert(self,push):
  self.run["asof"]=(self.now-timedelta(minutes=3)).isoformat()
  a,_=self.go();self.assertEqual(a["entries"],[]);push.assert_not_called()
 @patch("stop_watch.push_report")
 def test_other_account_no_alert(self,push):
  self.pos[0]["account"]="RH:regular";a,_=self.go();self.assertEqual(a["entries"],[]);push.assert_not_called()
 @patch("stop_watch.push_report")
 def test_no_orders_no_alert(self,push):
  self.order["state"]="filled";a,_=self.go();self.assertEqual(a["entries"],[]);push.assert_not_called()
 @patch("stop_watch.push_report")
 def test_incomplete_orders_not_all_clear(self,push):
  self.run["oc"]=0;a,_=self.go();self.assertIn("INCOMPLETE",a["coverage"][0]["status"]);push.assert_not_called()
 @patch("stop_watch.push_report",return_value={"status":1,"request":"fake"})
 def test_recovery_rearms_breach(self,push):
  self.go();self.quotes["AMD"]["price"]=100.1;self.go()
  self.quotes["AMD"]["price"]=99.9;self.go();self.assertEqual(push.call_count,2)
 @patch("stop_watch.push_report",return_value={"status":1,"request":"fake"})
 def test_changed_stop_new_alert(self,push):
  self.go();self.order["stop"]=101;self.go();self.assertEqual(push.call_count,2)
 @patch("stop_watch.push_report",return_value={"status":1,"request":"fake"})
 def test_regular_robinhood_live_breach(self,push):
  self.run["kind"]="REGULAR";a,_=self.go()
  self.assertEqual(a["entries"][0]["broker"],"Robinhood Live")
  self.assertFalse(a["live_closing_enabled"]);push.assert_called_once()
 @patch("stop_watch.push_report",return_value={"status":1,"request":"fake"})
 def test_agentic_breach_label(self,push):
  a,_=self.go();self.assertEqual(a["entries"][0]["broker"],"Robinhood Agentic")
 @patch("stop_watch.push_report")
 def test_missing_regular_coverage(self,push):
  self.order["state"]="filled";a,_=self.go()
  c=next(c for c in a["coverage"] if c["broker"]=="Robinhood Live")
  self.assertIn("UNAVAILABLE",c["status"])
if __name__=="__main__":unittest.main()