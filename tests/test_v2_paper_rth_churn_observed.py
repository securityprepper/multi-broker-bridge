import unittest
from v2_paper_rth_churn_observed import audit, AuditError

DAY = '2026-11-10'

def order(cid, sym, side, qty, price, at, status='filled', filled_qty=None):
    return {'client_order_id':cid, 'symbol':sym, 'side':side,
            'status':status, 'qty':str(qty),
            'filled_qty':str(qty) if filled_qty is None else str(filled_qty),
            'filled_avg_price':str(price) if status=='filled' else None,
            'created_at':'2026-11-10T'+at+':00Z',
            'filled_at':'2026-11-10T'+at+':10Z' if status=='filled' else None}

def sample():
    return {'paper_only': True, 'broker_verified':True, 'recent_orders_complete':True,
            'recent_orders_since_utc':'2026-11-07T00:00:00Z',
            'asof_utc':'2026-11-10T16:33:44Z', 'orders_submitted_by_exporter':0,
            'positions_count':1,'positions':[{'symbol':'COP','qty':'4','side':'long'}],
            'open_orders_count':0,'open_orders':[],
            'recent_orders':[order('MBB-a','ZS','buy',10,200,'14:00'),
                             order('MBB-b','ZS','sell',10,199,'14:05'),
                             order('MBB-c','COP','buy',4,135,'14:12')]}

class AuditTests(unittest.TestCase):
    def test_fifo_loss_and_remaining(self):
        r=audit(sample(),DAY);self.assertEqual(r['gross_realized_usd_before_fees'],-10)
        self.assertEqual(r['owner_filled_buys'],2);self.assertEqual(r['owner_closed_losers'],1)
        self.assertEqual(r['open_positions_by_symbol'],{'COP':4})
    def test_no_forecast_or_order_claim(self):
        r=audit(sample(),DAY);self.assertFalse(r['after_fees_pnl_verified'])
        self.assertFalse(r['fill_uuid_origin_chain_verified']);self.assertEqual(r['orders_sent_by_research'],0)
    def test_broker_verification_required(self):
        x=sample();x['broker_verified']=False
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_complete_order_range_required(self):
        x=sample();x['recent_orders_since_utc']='2026-11-10T14:00:00Z'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_duplicate_client_id_rejected(self):
        x=sample();x['recent_orders'][1]['client_order_id']='MBB-a'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_other_strategy_not_matched(self):
        x=sample();x['recent_orders'][0]['client_order_id']='FDR-a'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_position_quantity_mismatch(self):
        x=sample();x['positions'][0]['qty']='5'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_missing_fill_timestamp_rejected(self):
        x=sample();x['recent_orders'][1]['filled_at']=None
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_after_snapshot_fill_rejected(self):
        x=sample();x['recent_orders'][1]['filled_at']='2026-11-10T18:00:00Z'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_partial_fill_fail_closed(self):
        x=sample();x['recent_orders'][1]['filled_qty']='5'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_historical_orders_excluded(self):
        x=sample();x['recent_orders'].append(order('MBB-old','MU','buy',5,100,'14:00'))
        x['recent_orders'][-1]['created_at']='2026-11-09T14:00:00Z'
        self.assertEqual(audit(x,DAY)['owner_filled_buys'],2)
    def test_buys_involving_other_writer_rejected_if_position_mismatch(self):
        x=sample();x['recent_orders'].append(order('FDR-new','COP','buy',3,133,'14:14'))
        x['positions'][0]['qty']='7'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_invalid_timezone_rejected(self):
        x=sample();x['asof_utc']='2026-11-10T16:33:44'
        with self.assertRaises(AuditError):audit(x,DAY)
    def test_unfilled_order_does_not_count(self):
        x=sample();x['recent_orders'].append(order('MBB-unfilled','AMD','buy',4,470,'14:10',status='canceled',filled_qty='0'))
        self.assertEqual(audit(x,DAY)['owner_filled_buys'],2)

if __name__ == '__main__':unittest.main()
