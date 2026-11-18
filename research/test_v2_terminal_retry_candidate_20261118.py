"""Research-only simulation for terminal-zero-fill retry and partial exit accounting.

No network, credentials, broker POST, production scripts or actual broker orders.
All tests run with an in-memory mock broker and a temporary SQLite journal.
"""
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from unittest.mock import patch
from decimal import Decimal
import direction_paper as p
from test_v2_paper_signed_short_safety import Broker,seeded,quote,ct

class TerminalBroker(Broker):
    def __init__(self):
        super().__init__(shares=4)
        self.records={}
        self.fail_get=False
        self.return_order_id_override=None
        self.return_symbol_override=None
        self.return_side_override=None
    def __call__(self,method,path,body=None):
        if method=='POST' and path=='/v2/orders':
            self.posts.append(body)
            idx=len(self.posts)
            self.records[body['client_order_id']]={
               'id':'MOCK-ORDER-'+str(idx),
               'client_order_id':body['client_order_id'],
               'symbol':body['symbol'],'side':body['side'],
               'status':'accepted','qty':body['qty'],'filled_qty':'0'}
            return {'id':'MOCK-ORDER-'+str(idx),'status':'accepted'}
        if method=='GET' and path.startswith('/v2/orders:by_client_order_id?'):
            if self.fail_get:raise p.UnknownSubmission('MOCK_CONNECTION_UNCERTAIN')
            key=parse_qs(urlsplit(path).query)['client_order_id'][0]
            rec=dict(self.records[key])
            if self.return_order_id_override:rec['id']=self.return_order_id_override
            if self.return_symbol_override:rec['symbol']=self.return_symbol_override
            if self.return_side_override:rec['side']=self.return_side_override
            return rec
        return super().__call__(method,path,body)
    def terminal(self,index=0,status='expired',filled='0',price=None):
        rec=self.records[self.posts[index]['client_order_id']]
        rec.update(status=status,filled_qty=str(filled))
        if price is not None:rec['filled_avg_price']=str(price)
        return rec

class Replay(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup)
        self.db=p.connect(Path(self.dir.name)/'research.sqlite3')
        p.migrate_audit(self.db);self.addCleanup(self.db.close)
        self.signal=seeded(self.db,shares=4,side='sell',price=100)
        self.mock=TerminalBroker()
        a=patch.object(p,'expected_account',return_value='PAPER_TEST_ACCOUNT')
        a.start();self.addCleanup(a.stop)
    def first(self):
        a=p.software_risk_exits(self.db,ct(17,13,40),broker=self.mock,quotes=quote)
        self.assertEqual(len(a),1)
        self.assertEqual(len(self.mock.posts),1)
        self.assertEqual(self.mock.posts[0]['side'],'buy')
        return a
    def reconcile(self,at=ct(18,3,3)):
        return p.reconcile_orders(self.db,at,broker=self.mock)
    def retry(self,at=ct(18,3,5)):
        return p.software_risk_exits(self.db,at,broker=self.mock,quotes=quote)
    def attempt_record(self):
        return self.db.execute("SELECT outcome,broker_status,filled_qty,fill_price,broker_order_id FROM paper_attempts WHERE role='RISK_EXIT_SESSION_FLAT_1340_CT' ORDER BY before_order_utc").fetchall()

    def test_terminal_zero_expired_retries_once_with_distinct_client_id(self):
        self.first()
        self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.assertEqual(self.attempt_record()[0][:3],('BROKER_ORDER_TERMINAL_UNFILLED','expired',0.0))
        a=self.retry()
        self.assertEqual(len(a),1)
        self.assertEqual(len(self.mock.posts),2)
        self.assertNotEqual(self.mock.posts[0]['client_order_id'],self.mock.posts[1]['client_order_id'])
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),2)

    def test_terminal_zero_cancelled_retries(self):
        self.first()
        self.mock.terminal(status='canceled',filled='0')
        self.reconcile()
        self.assertEqual(len(self.retry()),1)

    def test_terminal_zero_done_for_day_retries(self):
        self.first()
        self.mock.terminal(status='done_for_day',filled='0')
        self.reconcile()
        self.assertEqual(len(self.retry()),1)

    def test_terminal_zero_rejected_only_if_broker_proves_zero_fill(self):
        self.first()
        self.mock.terminal(status='rejected',filled='0')
        self.reconcile()
        self.assertEqual(len(self.retry()),1)

    def test_missing_filled_qty_never_assumed_zero(self):
        self.first()
        rec=self.mock.terminal(status='expired')
        rec.pop('filled_qty')
        x=self.reconcile()
        self.assertEqual(x['broker_readback_unknown_count'],1)
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_partial_2_of_4_expired_is_not_unfilled_and_blocks_retry(self):
        self.first()
        self.mock.terminal(status='expired',filled='2',price='101.20')
        self.reconcile()
        x=self.attempt_record()[0]
        self.assertEqual(x[0],'BROKER_TERMINAL_PARTIAL_UNRESOLVED')
        self.assertEqual(x[2],2.0)
        self.assertEqual(x[3],101.20)
        self.mock.positions[0]['qty']='-2'
        self.mock.positions[0]['qty_available']='-2'
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_fully_executed_terminal_canceled_status_blocks_retry(self):
        self.first()
        self.mock.terminal(status='canceled',filled='4',price='101.20')
        self.reconcile()
        self.assertEqual(self.attempt_record()[0][0],'BROKER_TERMINAL_PARTIAL_UNRESOLVED')
        self.assertEqual(self.retry(),[])

    def test_unknown_broker_status_blocks(self):
        self.first()
        self.mock.terminal(status='accepted',filled='0')
        self.reconcile()
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_reverification_order_id_mismatch_blocks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.return_order_id_override='IMPOSTOR'
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_reverification_wrong_symbol_blocks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.return_symbol_override='TSM'
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_reverification_wrong_side_blocks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.return_side_override='sell'
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_get_failure_blocks_no_new_retry(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.fail_get=True
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_open_broker_order_for_same_symbol_blocks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.orders=[{'symbol':'AMD','status':'accepted','side':'buy','id':'OTHER'}]
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_other_account_blocks_retry(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.account_id='WRONG'
        with self.assertRaises(ValueError):self.retry()
        self.assertEqual(len(self.mock.posts),1)

    def test_mismatched_short_quantity_blocks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        self.mock.positions[0]['qty']='-3'
        self.mock.positions[0]['qty_available']='-3'
        self.assertEqual(self.retry(),[])
        self.assertEqual(len(self.mock.posts),1)

    def test_bounded_retries_no_unlimited_orders(self):
        self.first()
        for i in range(3):
            self.mock.terminal(i,status='expired',filled='0')
            self.reconcile(ct(18,3,5+i))
            if i<3:
                actions=self.retry(ct(18,3,5+i))
                self.assertEqual(len(actions),1)
        self.assertEqual(len(self.mock.posts),4)
        self.mock.terminal(3,status='expired',filled='0')
        self.reconcile(ct(18,3,10))
        self.assertEqual(self.retry(ct(18,3,11)),[])
        self.assertEqual(len(self.mock.posts),4)

    def test_broker_terminal_status_does_not_bypass_quote_and_spread_checks(self):
        self.first();self.mock.terminal(status='expired',filled='0')
        self.reconcile()
        def stale(*args):raise ValueError('STALE_QUOTE')
        self.assertEqual(p.software_risk_exits(self.db,ct(18,3,5),broker=self.mock,quotes=stale),[])
        self.assertEqual(len(self.mock.posts),1)

if __name__=='__main__':
    unittest.main(verbosity=2)
