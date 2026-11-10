import copy, unittest, datetime, json
from zoneinfo import ZoneInfo
from v2_mbb_final_flat_proof_20261110 import audit,parse_journal
CT=ZoneInfo("America/Chicago")
def t(h,m,s=0):return datetime.datetime(2026,11,10,h,m,s,tzinfo=CT)
def inv():
    return dict(broker_verified=True,paper_only=True,recent_orders_complete=True,
     asof_utc="2026-11-10T20:28:55Z",recent_orders_since_utc="2026-11-07T20:28:55Z",
     positions_count=0,positions=[],open_orders_count=0,open_orders=[],
     orders_submitted_by_exporter=0,
     recent_orders=[
      dict(client_order_id="MBB-20261110-a",symbol="COP",side="buy",status="filled",submitted_at="2026-11-10T11:00:00-06:00",filled_at="2026-11-10T11:00:01-06:00",filled_qty="14",filled_avg_price="134.92"),
      dict(client_order_id="MBB-20261110-b",symbol="COP",side="sell",status="filled",submitted_at="2026-11-10T13:40:30-06:00",filled_at="2026-11-10T13:40:31-06:00",filled_qty="14",filled_avg_price="135.54"),
      dict(client_order_id="MBB-20261110-c",symbol="NET",side="buy",status="filled",submitted_at="2026-11-10T13:10:40-06:00",filled_at="2026-11-10T13:10:42-06:00",filled_qty="6",filled_avg_price="301.695"),
      dict(client_order_id="MBB-20261110-d",symbol="NET",side="sell",status="filled",submitted_at="2026-11-10T13:40:30-06:00",filled_at="2026-11-10T13:40:34-06:00",filled_qty="6",filled_avg_price="302.43")])
def records():
 return [dict(when=t(13,40,30),kind="guard",flat_verified=False,status="FLATTEN_IN_PROGRESS",overdue=False),
 dict(when=t(13,40,40),kind="guard",flat_verified=True,status="FLAT_IN_BROKER_SNAPSHOT",overdue=False),
 dict(when=t(14,0,29),kind="guard",flat_verified=True,status="FLAT_IN_BROKER_SNAPSHOT",overdue=False),
 dict(when=t(14,3,56),kind="readback",broker_verified=True,positions_count=0,open_orders_count=0)]
class Tests(unittest.TestCase):
 def verify(self,s=None,r=None):return audit(inv() if s is None else s,records() if r is None else r,"2026-11-10")
 def fail(self,s=None,r=None):
  with self.assertRaises(ValueError):self.verify(s,r)
 def test_valid(self):
  a=self.verify()
  self.assertEqual(a["verification"],"PAPER_DAILY_FLAT_CONFIRMED")
  self.assertEqual((a["mbb_filled_buys"],a["mbb_filled_sells"]),(2,2))
  self.assertEqual(a["gross_realized_paper_usd"],"13.09")
  self.assertFalse(a["exclusive_strategy_ownership_proven"])
 def test_accepted_is_not_filled(self):self.fail(r=[records()[0],records()[2],records()[3]])
 def test_missing_1400_guard(self):self.fail(r=[records()[0],records()[1],records()[3]])
 def test_missing_independent_readback(self):self.fail(r=records()[:3])
 def test_stale_snapshot(self):
  s=inv();s["asof_utc"]="2026-11-10T19:59:00Z";self.fail(s)
 def test_unverified(self):
  s=inv();s["broker_verified"]=False;self.fail(s)
 def test_truncated_order_history(self):
  s=inv();s["recent_orders_since_utc"]="2026-11-10T14:00:00Z";self.fail(s)
 def test_open_position(self):
  s=inv();s["positions_count"]=1;s["positions"]=[dict(symbol="COP",qty=1)];self.fail(s)
 def test_open_order(self):
  s=inv();s["open_orders_count"]=1;s["open_orders"]=[dict(symbol="COP")];self.fail(s)
 def test_late_buy_submission(self):
  s=inv();s["recent_orders"][0]["submitted_at"]="2026-11-10T13:15:00-06:00";self.fail(s)
 def test_duplicate_order(self):
  s=inv();s["recent_orders"][1]["client_order_id"]="MBB-20261110-a";self.fail(s)
 def test_unmatched_sell(self):
  s=inv();s["recent_orders"][1]["filled_qty"]="15";self.fail(s)
 def test_incomplete_flatten(self):
  s=inv();s["recent_orders"].pop();self.fail(s)
 def test_wrong_exporter(self):
  s=inv();s["orders_submitted_by_exporter"]=1;self.fail(s)
 def test_wrong_readback(self):
  r=records();r[-1]["open_orders_count"]=1;self.fail(r=r)
 def test_parse_journal(self):
  def line(msg,dt):
   return json.dumps({"MESSAGE":json.dumps(msg),"__REALTIME_TIMESTAMP":str(int(dt.timestamp()*1000000))})
  parsed=parse_journal([line({"status":"PAPER_DAILY_EXIT_GUARD","exit_guard":{"flat_verified":True,"status":"FLAT_IN_BROKER_SNAPSHOT","overdue":False}},t(13,40,40)),line({"broker_verified":True,"positions_count":0,"open_orders_count":0},t(14,3,56))])
  self.assertEqual([x["kind"] for x in parsed],["guard","readback"])
if __name__=="__main__":unittest.main()
