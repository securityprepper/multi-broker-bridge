"""Research-only idempotent PAPER FILL readback events. No broker, Pushover or DB writes."""
import unittest,json
from unittest.mock import patch
from recommendation_paper_bridge import reconcile
from recommendation_paper_bridge.bridge import Unsafe

class FakeCursor:
    def __init__(self, prior=None):
        self.prior=prior; self.executed=[]
    def execute(self,query,params):
        self.executed.append((query,params))
    def fetchone(self):
        return {'evidence_json':self.prior} if self.prior is not None else None

class ReadbackTest(unittest.TestCase):
    def test_identical_broker_evidence_not_reinserted(self):
        obj={'state':'CLOSED_NEEDS_FEE_RECON','fill_activity_ids':['1','2','3','4'],
             'fill_activity_count':4,'gross_pnl':'-16.04','fees_verified':False,'net_pnl':None}
        cur=FakeCursor(json.dumps(obj))
        with patch.object(reconcile,'event') as ev:
            self.assertFalse(reconcile.record_readback_if_changed(cur,'rec',dict(obj)))
            ev.assert_not_called()
        self.assertEqual(len(cur.executed),1)
        self.assertIn("ORDER BY id DESC LIMIT 1",cur.executed[0][0])
    def test_new_first_broker_readback_is_inserted(self):
        obj={'state':'UNFILLED_TERMINAL','fills':0}
        cur=FakeCursor()
        with patch.object(reconcile,'event') as ev:
            self.assertTrue(reconcile.record_readback_if_changed(cur,'rec',obj))
            ev.assert_called_once_with(cur,'rec','BROKER_FILL_READBACK',obj)
    def test_new_fill_uuid_not_suppressed(self):
        earlier={'state':'OPEN_WITH_BRACKET','fill_activity_ids':['abc'],'fill_activity_count':1}
        latest={'state':'OPEN_WITH_BRACKET','fill_activity_ids':['abc','def'],'fill_activity_count':2}
        cur=FakeCursor(json.dumps(earlier))
        with patch.object(reconcile,'event') as ev:
            self.assertTrue(reconcile.record_readback_if_changed(cur,'rec',latest))
            ev.assert_called_once()
    def test_changed_broker_protection_status_preserved(self):
        earlier={'state':'OPEN_WITH_BRACKET','buy_qty':'2','sell_qty':'0'}
        latest={'state':'PARTIAL_UNPROTECTED','buy_qty':'2','sell_qty':'0'}
        cur=FakeCursor(json.dumps(earlier))
        with patch.object(reconcile,'event') as ev:
            self.assertTrue(reconcile.record_readback_if_changed(cur,'rec',latest))
            ev.assert_called_once()
    def test_same_json_semantics_different_key_order_suppressed(self):
        cur=FakeCursor('{"b":2,"a":1}')
        with patch.object(reconcile,'event') as ev:
            self.assertFalse(reconcile.record_readback_if_changed(cur,'rec',{'a':1,'b':2}))
            ev.assert_not_called()
    def test_bad_prior_evidence_fails_closed(self):
        for prior in ('{INVALID','[]','null','"string"'):
            with self.subTest(prior=prior):
                cur=FakeCursor(prior)
                with patch.object(reconcile,'event') as ev:
                    with self.assertRaises(Unsafe):
                        reconcile.record_readback_if_changed(cur,'rec',{'state':'CLOSED_NEEDS_FEE_RECON'})
                    ev.assert_not_called()
    def test_price_numeric_identity_unchanged(self):
        from decimal import Decimal
        self.assertTrue(reconcile.same_positive_price('66.13',Decimal('66.130000')))
        self.assertFalse(reconcile.same_positive_price('66.130001',Decimal('66.130000')))
        self.assertFalse(reconcile.same_positive_price(None,Decimal('66.130000')))
    def test_no_broker_order_post_in_reconciler(self):
        import inspect
        code=inspect.getsource(reconcile)
        self.assertNotIn('httpfn("POST"',code)
        self.assertNotIn('httpfn("DELETE"',code)
        self.assertNotIn('httpfn("PATCH"',code)
if __name__=="__main__":unittest.main()
