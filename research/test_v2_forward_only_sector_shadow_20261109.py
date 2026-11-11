import json, tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch
from research import v2_forward_only_sector_shadow_20261109 as f
ET=ZoneInfo("America/New_York")
NOW=datetime(2026,11,10,9,35,25,tzinfo=ET)
PAST=("2026-11-03","2026-11-04","2026-11-05","2026-11-06","2026-11-09")
def daily():
 return {s:[{"t":d+"T05:00:00Z","c":100} for d in PAST] for s in f.symbols()}
def live():
 result={}
 for s in f.symbols():
  price=99 if s=="SOXX" else (99.5 if s in ("AMD","MU","NVDA") else 100)
  result[s]=[
   {"t":"2026-11-10T14:25:00Z","o":100,"h":100,"l":100,"c":99.8 if s=="SOXX" else 100},
   {"t":"2026-11-10T14:30:00Z","o":100,"h":100,"l":price,"c":price},
   {"t":"2026-11-10T14:35:00Z","o":100,"h":110,"l":90,"c":110}
  ]
 return result
class TestForwardShadow(unittest.TestCase):
 def test_slot_exact_end_and_weekend(self):
  self.assertEqual(f.slot(NOW),"09:35")
  self.assertIsNone(f.slot(NOW-timedelta(minutes=5)))
  self.assertIsNone(f.slot(datetime(2026,11,8,9,35,25,tzinfo=ET)))
 def test_prior_five_are_not_today(self):
  v=f.validate_daily_prior5(daily(),NOW)
  self.assertTrue(all(len(x["five_previous_dates"])==5 for x in v.values()))
  self.assertNotIn("2026-11-10",v["SOXX"]["five_previous_dates"])
 def test_duplicate_daily_bar_does_not_count_as_extra_day(self):
  z=daily()
  z["SOXX"]=[z["SOXX"][0],z["SOXX"][0]]+z["SOXX"][1:4]
  self.assertIsNone(f.validate_daily_prior5(z,NOW)["SOXX"])
 def test_conflicting_daily_close_fails_closed(self):
  z=daily()
  z["SOXX"].append({"t":z["SOXX"][0]["t"],"c":500})
  with self.assertRaises(ValueError):
   f.validate_daily_prior5(z,NOW)
 def test_future_daily_rejected(self):
  z=daily();z["SOXX"]=[{"t":"2026-11-10T05:00:00Z","c":1000}]
  self.assertIsNone(f.validate_daily_prior5(z,NOW)["SOXX"])
 def test_unfinished_live_bar_excluded(self):
  v=f.validate_live_bars(live(),NOW)
  self.assertIn("2026-11-10 09:30",v["SOXX"])
  self.assertNotIn("2026-11-10 09:35",v["SOXX"])
 def test_shadow_uses_only_prior_completed_bars(self):
  d=f.validate_daily_prior5(daily(),NOW)
  b=f.validate_live_bars(live(),NOW)
  s=f.asof_signals(NOW,"09:35",d,b)
  self.assertEqual(s["semiconductors"]["shadow_classification"],"ABSTAIN")
  self.assertEqual(s["semiconductors"]["legacy_semiconductor_watch"],"EXPLORATORY_BEARISH_SEMI_WATCH_ONLY")
  self.assertFalse(s["semiconductors"]["broker_order_permissions"])
 def test_missing_critical_peer_abstains(self):
  d=f.validate_daily_prior5(daily(),NOW)
  b=f.validate_live_bars(live(),NOW)
  b["AMD"]={}
  s=f.asof_signals(NOW,"09:35",d,b)
  self.assertEqual(s["semiconductors"]["status"],"ABSTAIN_MISSING_ASOF_DATA")
 def test_once_seal_cannot_be_replaced(self):
  with tempfile.TemporaryDirectory() as td:
   p=f.save_once(Path(td),NOW,"09:35",{"no_orders":True})
   with self.assertRaises(FileExistsError):
    f.save_once(Path(td),NOW,"09:35",{"no_orders":False})
   self.assertTrue(json.loads(p.read_text())["no_orders"])
 def test_holiday_pause_cannot_fetch(self):
  with patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":"/tmp/not-used"}):
   x=f.run(NOW,holiday_check=lambda t:False,fetch=lambda *a,**k: (_ for _ in ()).throw(AssertionError("fetched")))
  self.assertEqual(x["market_data_requests"],0)
  self.assertEqual(x["status"],"HOLIDAY_PAUSED_NO_POLL")
 def test_success_get_only_with_no_orders(self):
  calls=[]
  def fetch(n,frame,creds):
   calls.append(frame)
   return daily() if frame=="1Day" else live()
  with tempfile.TemporaryDirectory() as td,patch.dict("os.environ",{"V2_SHADOW_STATE_ROOT":td}):
   x=f.run(NOW,holiday_check=lambda t:True,fetch=fetch)
   self.assertEqual(calls,["1Day","5Min"])
   self.assertEqual(x["status"],"RESEARCH_SHADOW_SEALED")
   self.assertEqual(x["orders_submitted"],0)
   p=Path(td)/"2026-11-10"/"0935.json"
   self.assertTrue(json.loads(p.read_text())["no_current_or_future_outcomes_in_document"])
   y=f.run(NOW,holiday_check=lambda t:True,fetch=lambda *a: (_ for _ in ()).throw(AssertionError("fetch twice")))
   self.assertEqual(y["status"],"ALREADY_SEALED")
 def test_market_fetch_get_only(self):
  requests=[]
  class Resp:
   status=200
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def read(self,n):return b'{"bars":{},"next_page_token":null}'
  def open_req(req,timeout):
   requests.append((req.get_method(),req.full_url))
   return Resp()
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)
   (p/"alpaca_data_key_id").write_text("TEST_KEY")
   (p/"alpaca_data_secret").write_text("TEST_SECRET")
   f.fetch_bars(NOW,"5Min",p,opener=open_req)
   self.assertEqual(requests[0][0],"GET")
   self.assertNotIn("TEST_SECRET",requests[0][1])
 def test_no_order_interface(self):
  self.assertFalse(hasattr(f,"place_order"))
  self.assertFalse(hasattr(f,"submit_order"))
  self.assertFalse(hasattr(f,"pushover"))
if __name__=="__main__":unittest.main()
