import json,os,unittest
from datetime import datetime,timezone,timedelta,date
from unittest.mock import patch
from recommendation_paper_bridge.bridge import (
    ingest,process_once,validate_recommendation,Unsafe,safe_client_id
)
NOW=datetime(2026,11,10,16,0,tzinfo=timezone.utc)
BASE={"recommendation_id":"TO-20261110-AMD-T1-RUN42",
"issued_at_utc":"2026-11-10T15:59:50Z","quote_at_utc":"2026-11-10T15:59:35Z",
"symbol":"AMD","action":"BUY NOW","quote_last":"100.00","quote_bid":"99.98",
"quote_ask":"100.05","limit":"100.10","profit_target":"101.60",
"stop_loss":"98.50","rationale":"Official earnings and non-extended qualified pullback",
"source_task":"Task - Trading Opportunities One","source_run_id":"run.42"}
class Cursor:
 def __init__(self,parent):self.p=parent;self.rowcount=1
 def execute(self,sql,args=None):
    self.p.sql.append((sql,args))
    self.rowcount=1
 def fetchone(self):return (1,)
 def fetchall(self):
    return [dict(self.p.row)] if self.p.row else []
class Conn:
 def __init__(self,row=None):self.row=row;self.sql=[];self.commits=0;self.rollbacks=0
 def cursor(self,**k):return Cursor(self)
 def start_transaction(self):return None
 def commit(self):self.commits+=1
 def rollback(self):self.rollbacks+=1
 def close(self):return None
class TestDatabaseAndBrokerIntegration(unittest.TestCase):
 def test_atomic_legacy_and_new_db_inserts(self):
    db=Conn()
    r=ingest(dict(BASE),now=NOW,connect=lambda *_:db)
    self.assertEqual(r["status"],"PENDING")
    self.assertEqual(db.commits,1)
    self.assertEqual(db.rollbacks,0)
    statements=" ".join(x[0] for x in db.sql)
    for name in ("sp_paper_rec_intents","sp_paper_rec_events",
                 "sp_live_recommendation_ledger","sp_notes_recommendations"):
        self.assertIn(name,statements)
 def test_intake_verified_rollback_leaves_no_commit(self):
    db=Conn()
    r=ingest(dict(BASE),now=NOW,connect=lambda *_:db,test_rollback=True)
    self.assertEqual(r["status"],"ROLLBACK_VERIFIED")
    self.assertEqual(db.commits,0)
    self.assertEqual(db.rollbacks,1)
 def typed(self):
    s=validate_recommendation(dict(BASE),NOW)
    return {"recommendation_id":s["id"],"issued_at_utc":s["issued"].replace(tzinfo=None),
            "expires_at_utc":s["expiry"].replace(tzinfo=None),"session_date":s["session"],
            "symbol":s["symbol"],"action":s["action"],"limit_price":s["limit"],
            "profit_target":s["target"],"stop_loss":s["stop"],
            "intended_qty":s["qty"],"client_order_id":s["client_id"]}
 def response(self,row,cls="bracket"):
    return {"id":"broker-uuid","client_order_id":row["client_order_id"],
            "order_class":cls,"side":"buy","symbol":"AMD","type":"limit",
            "time_in_force":"day","extended_hours":False,
            "limit_price":"100.10","qty":"19","status":"new"}
 def test_full_mock_paper_bracket_and_readback(self):
    row=self.typed();db=Conn(row);calls=[]
    def remote(method,path,body=None,data=False):
        calls.append((method,path,body,data))
        if path=="/v2/account":return {"id":"PAPER_ID","status":"ACTIVE","trading_blocked":False,"cash":"5000"}
        if path=="/v2/positions" or path.startswith("/v2/orders?"):return []
        if data:return {"quote":{"bp":99.98,"ap":100.05,"t":"2026-11-10T15:59:45Z"}}
        if method=="POST":return self.response(row)
        if path.startswith("/v2/orders/broker-uuid"):return self.response(row)
        raise AssertionError(path)
    env={"PAPER_BRIDGE_COMMISSIONED":"1","PAPER_BRIDGE_SHARED_LOCK_ATTESTED":"1",
         "PAPER_BRIDGE_EXIT_GUARD_ATTESTED":"1","PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"PAPER_ID"}
    with patch.dict(os.environ,env),patch(
        "recommendation_paper_bridge.bridge.require_holiday",return_value=True):
        result=process_once(NOW,connect=lambda *_:db,httpfn=remote)
    self.assertEqual(result["results"][0]["status"],"BROKER_ACCEPTED")
    posted=[a for a in calls if a[0]=="POST"]
    self.assertEqual(len(posted),1)
    self.assertEqual(posted[0][2]["order_class"],"bracket")
    self.assertEqual(posted[0][2]["take_profit"]["limit_price"],"101.60")
    self.assertEqual(posted[0][2]["stop_loss"]["stop_price"],"98.50")
 def test_wrong_broker_class_never_retries(self):
    row=self.typed();db=Conn(row);posted=[]
    def remote(method,path,body=None,data=False):
        if path=="/v2/account":return {"id":"PAPER_ID","status":"ACTIVE","trading_blocked":False,"cash":"5000"}
        if path=="/v2/positions" or path.startswith("/v2/orders?"):return []
        if data:return {"quote":{"bp":"99.98","ap":"100.05","t":"2026-11-10T15:59:45Z"}}
        if method=="POST":
            posted.append(body)
            return self.response(row,cls="simple")
        raise AssertionError(path)
    env={"PAPER_BRIDGE_COMMISSIONED":"1","PAPER_BRIDGE_SHARED_LOCK_ATTESTED":"1",
         "PAPER_BRIDGE_EXIT_GUARD_ATTESTED":"1","PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"PAPER_ID"}
    with patch.dict(os.environ,env),patch(
        "recommendation_paper_bridge.bridge.require_holiday",return_value=True):
        result=process_once(NOW,connect=lambda *_:db,httpfn=remote)
    self.assertEqual(result["results"][0]["status"],"UNKNOWN_NO_RETRY")
    self.assertEqual(len(posted),1)
 def test_existing_strategy_position_blocks_post(self):
    row=self.typed();db=Conn(row);posts=[]
    def remote(method,path,body=None,data=False):
        if path=="/v2/account":return {"id":"PAPER_ID","status":"ACTIVE","trading_blocked":False,"cash":"5000"}
        if path=="/v2/positions":return [{"symbol":"AMD","qty":"2","side":"long"}]
        if path.startswith("/v2/orders?"):return []
        if method=="POST":posts.append(path)
        raise AssertionError("Unexpected endpoint "+path)
    env={"PAPER_BRIDGE_COMMISSIONED":"1","PAPER_BRIDGE_SHARED_LOCK_ATTESTED":"1",
         "PAPER_BRIDGE_EXIT_GUARD_ATTESTED":"1","PAPER_BRIDGE_EXPECTED_PAPER_ACCOUNT":"PAPER_ID"}
    with patch.dict(os.environ,env),patch(
        "recommendation_paper_bridge.bridge.require_holiday",return_value=True):
        result=process_once(NOW,connect=lambda *_:db,httpfn=remote)
    self.assertEqual(result["results"][0]["status"],"NO_ORDER")
    self.assertEqual(posts,[])
if __name__=="__main__":unittest.main()
