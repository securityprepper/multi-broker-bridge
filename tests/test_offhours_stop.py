import unittest
from datetime import datetime,timedelta,timezone
from multi_broker_bridge.offhours_stop import detect,session,paper_exit_plan
class Stops(unittest.TestCase):
 def setUp(self):
  self.now=datetime(2026,11,17,5,0,tzinfo=timezone.utc); self.ts=self.now.isoformat()
  self.p=dict(account="RH:a",symbol="AMD",asset="EQUITY",qty=10,paper=False,broker="Robinhood",position_asof=self.ts)
  self.o=dict(account="RH:a",symbol="AMD",id="1",side="sell",state="confirmed",tif="gtc",stop=100,qty=10,filled=2,asof=self.ts)
  self.q={"AMD":dict(price=99.9,asof=self.ts,stale=False)}
 def found(self):return detect([self.p],[self.o],self.q,self.now)
 def test_breach_remaining(self): self.assertEqual(self.found()[0]["qty"],8)
 def test_small_noise(self):
  self.q["AMD"]["price"]=99.96;self.assertEqual(self.found(),[])
 def test_threshold_inclusive(self):
  self.q["AMD"]["price"]=99.95;self.assertEqual(len(self.found()),1)
 def test_terminal(self):
  for state in ("filled","cancelled","canceled","rejected","pending_cancel"):
   self.o["state"]=state;self.assertEqual(self.found(),[])
 def test_stale_evidence(self):
  for obj,key in ((self.p,"position_asof"),(self.o,"asof"),(self.q["AMD"],"asof")):
   old=obj[key];obj[key]=(self.now-timedelta(minutes=3)).isoformat();self.assertEqual(self.found(),[]);obj[key]=old
 def test_future_quote(self):
  self.q["AMD"]["asof"]=(self.now+timedelta(seconds=1)).isoformat();self.assertEqual(self.found(),[])
 def test_wrong_account(self):
  self.o["account"]="RH:b";self.assertEqual(self.found(),[])
 def test_options_short_paper_excluded(self):
  for key,val in (("asset","OPTION"),("qty",-10),("paper",True)):
   old=self.p[key];self.p[key]=val;self.assertEqual(self.found(),[]);self.p[key]=old
 def test_day_buy_missing_fill(self):
  for key,val in (("tif","day"),("side","buy"),("filled",None),("filled",10)):
   old=self.o[key];self.o[key]=val;self.assertEqual(self.found(),[]);self.o[key]=old
 def test_duplicate_order(self):
  self.assertEqual(len(detect([self.p],[self.o,self.o],self.q,self.now)),1)
 def test_sessions(self):
  self.assertEqual(session(self.now),"OVERNIGHT")
  self.assertEqual(session(self.now.replace(hour=16)),"REGULAR")
  self.assertEqual(session(self.now.replace(day=21,hour=16)),"CLOSED")
 def test_plan_live_and_cancel_guard(self):
  for account,terminal in (("U123",True),("DU123",False),("ALPACA_LIVE:abc",True)):
   with self.assertRaises(ValueError):paper_exit_plan(account,10,10,0,100,self.ts,self.now,terminal)
 def test_plan_remaining(self):
  p=paper_exit_plan("DU123",5,10,2,100,self.ts,self.now,True);self.assertEqual(p["qty"],5);self.assertFalse(p["live_enabled"])
if __name__=="__main__":unittest.main()