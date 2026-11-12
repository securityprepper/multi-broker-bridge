import unittest
from unittest.mock import patch
from datetime import datetime,timezone,timedelta
from decimal import Decimal
from recommendation_paper_bridge import bridge

NOW=datetime(2026,11,10,16,0,0,tzinfo=timezone.utc)
OID="11111111-2222-3333-4444-555555555555"
REC="FDR5-20261110-AMD-1234ABCD"
CLIENT=bridge.safe_client_id(REC)
ROW=dict(recommendation_id=REC,source_task=bridge.REBOUND_TASK,
         session_date="2026-11-10",symbol="AMD",action="BUY NOW",
         client_order_id=CLIENT,limit_price=Decimal("100.10"),
         profit_target=Decimal("105"),stop_loss=Decimal("98"),
         intended_qty=19,issued_at_utc=NOW.replace(tzinfo=None),
         expires_at_utc=(NOW+timedelta(minutes=2)).replace(tzinfo=None),
         created_at_utc=(NOW-timedelta(seconds=4)).replace(tzinfo=None),
         quote_last=Decimal("100.05"),quote_ask=Decimal("100.10"))

class FakeDB:
    def __init__(self,duplicate=False):
        self.events=[];self.in_tx=False;self.cursor_obj=FakeCursor(self)
        self.duplicate=duplicate
    def cursor(self,**kw):return self.cursor_obj
    def start_transaction(self):
        if self.in_tx:raise AssertionError("Transaction already in progress")
        self.in_tx=True;self.events.append("START_TRANSACTION")
    def commit(self):
        self.in_tx=False;self.events.append("COMMIT")
    def rollback(self):
        self.in_tx=False;self.events.append("ROLLBACK")
    def close(self):self.events.append("CLOSE")
class FakeCursor:
    def __init__(self,db):self.db=db;self.rowcount=1
    def execute(self,sql,args=()):
        if sql.startswith("SELECT * FROM"):
            self.db.in_tx=True;self.db.events.append("READ_PENDING")
        elif "INSERT INTO "+bridge.CLAIM_TABLE in sql:
            self.db.events.append("CLAIM")
            if self.db.duplicate:raise ValueError("duplicate claim")
        elif "UPDATE "+bridge.INTENT_TABLE in sql:self.db.events.append("UPDATE_INTENT");self.rowcount=1
        elif "INSERT INTO "+bridge.EVENT_TABLE in sql:self.db.events.append("EVENT")
        else:self.db.events.append("OTHER_SQL")
    def fetchall(self):return [ROW.copy()]
class BrokerFake:
    def __init__(self,ambiguous=False):self.events=[];self.ambiguous=ambiguous
    def __call__(self,method,path,body=None,data=False):
        if method=="POST":
            self.events.append("PAPER_POST")
            if self.ambiguous:raise bridge.SubmissionUnknown("transport ambiguous")
            self.body=body
            return dict(id=OID,client_order_id=CLIENT,order_class="bracket",
                        side="buy",symbol="AMD",type="limit",time_in_force="day",
                        extended_hours=False,limit_price="100.10",qty="19",status="accepted")
        if method=="GET":
            self.events.append("BROKER_READBACK")
            return dict(id=OID,client_order_id=CLIENT,order_class="bracket",
                        symbol="AMD",side="buy")
        raise AssertionError("unexpected network call")
class BrokerRouteTests(unittest.TestCase):
    def run_route(self,db,broker,rec=REC):
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(bridge,"require_clear",return_value={"status":"NEWS_CLEAR_ASOF","evidence_sha256":"mock-proof"}),patch.object(
            bridge,"preflight",return_value={"account_fingerprint":"verified-paper-abc",
                "quote_at":NOW-timedelta(seconds=2),
                "entry_tracking":{"price_gate":"NO_CHASE","already_up_at_order_ask_pct":"0.1"},
                "news_clearance":{"status":"NEWS_CLEAR_ASOF","evidence_sha256":"mock-proof"}}):
            return bridge.process_once(now=NOW,connect=lambda profile:db,
                            httpfn=broker,only_recommendation_id=rec,clockfn=lambda:NOW)
    def test_router_commit_before_claim_no_transaction_collision(self):
        db=FakeDB();broker=BrokerFake()
        r=self.run_route(db,broker)
        self.assertEqual(r["results"][0]["status"],"BROKER_ACCEPTED")
        self.assertLess(db.events.index("READ_PENDING"),db.events.index("START_TRANSACTION"))
        self.assertLess(db.events.index("COMMIT"),db.events.index("START_TRANSACTION"))
        self.assertEqual(broker.events,["PAPER_POST","BROKER_READBACK"])
        self.assertEqual(broker.body["order_class"],"bracket")
        self.assertEqual(broker.body["time_in_force"],"day")
        self.assertEqual(broker.body["stop_loss"]["stop_price"],"98")
    def test_duplicate_claim_prevents_broker_post(self):
        db=FakeDB(duplicate=True);broker=BrokerFake()
        result=self.run_route(db,broker)
        self.assertEqual(result["results"][0]["status"],"DUPLICATE_OR_RACED")
        self.assertEqual(broker.events,[])
    def test_ambiguous_broker_submission_never_retried(self):
        db=FakeDB();broker=BrokerFake(ambiguous=True)
        result=self.run_route(db,broker)
        self.assertEqual(result["results"][0]["status"],"UNKNOWN_NO_RETRY")
        self.assertEqual(broker.events,["PAPER_POST"])
    def test_default_router_does_not_pick_rebound_rows(self):
        db=FakeDB();broker=BrokerFake()
        with patch.object(bridge,"require_commissioned"),patch.object(bridge,"require_holiday"),patch.object(bridge,"require_clear",return_value={"status":"NEWS_CLEAR_ASOF","evidence_sha256":"mock-proof"}),patch.object(
            bridge,"preflight",return_value={"account_fingerprint":"verified-paper-abc",
                "quote_at":NOW-timedelta(seconds=2),
                "entry_tracking":{"price_gate":"NO_CHASE","already_up_at_order_ask_pct":"0.1"},
                "news_clearance":{"status":"NEWS_CLEAR_ASOF","evidence_sha256":"mock-proof"}}):
            bridge.process_once(now=NOW,connect=lambda profile:db,httpfn=broker,clockfn=lambda:NOW)
        self.assertNotIn("REBOUND_ORDER_READY"," ".join(db.events))

if __name__=="__main__":unittest.main()
