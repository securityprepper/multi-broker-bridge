"""Offline causality, boundary and flip-direction tests; no broker or V1 imports."""
import unittest
from datetime import date, datetime, time, timedelta
from research.v2_stock_risk_dayphase import ET
from research.v2_opening_sector_flip_stress import (
    ETF,PEERS,ANCHOR,first_open_flip,completed_returns,
    preopen_direction,same_day_proxy,CUTOFFS)

DAY=date(2026,11,2); PRE=date(2026,10,30)
SYMS=(*PEERS,ETF)
def stub(pre_value=101.0,post_value=99.8,at=time(9,30),missing=None):
    bars={s:{} for s in SYMS}
    closes={s:{PRE:100.0} for s in SYMS}
    for s in SYMS:
        if s != missing:
            bars[s][datetime.combine(DAY,ANCHOR,ET)] = [pre_value]*4+[100]
        bars[s][datetime.combine(DAY,at,ET)] = [post_value]*4+[100]
    return bars,closes

class OpenFlipTests(unittest.TestCase):
    def test_direction_requires_soxx_plus_four_peers(self):
        ret={s:1 for s in SYMS}
        self.assertEqual(preopen_direction(ret),1)
        self.assertEqual(preopen_direction({s:-1 for s in SYMS}),-1)
        ret[ETF]=0
        self.assertEqual(preopen_direction(ret),0)
        ret={s:0 for s in SYMS};ret[ETF]=1
        for s in PEERS[:3]:ret[s]=1
        self.assertEqual(preopen_direction(ret),0)

    def test_0930_bar_only_alert_at_0935(self):
        bars,closes=stub()
        e=first_open_flip(bars,closes,'AMD',PRE,DAY)
        self.assertEqual(e['asof'],'2026-11-02T09:35:00-05:00')
        self.assertEqual(e['side'],'down')
        self.assertEqual(e['preopen_direction'],'up')
        self.assertIsNone(e['next_bar_open'])

    def test_reverse_direction(self):
        bars,closes=stub(pre_value=99.0,post_value=100.2)
        e=first_open_flip(bars,closes,'SOXX',PRE,DAY)
        self.assertEqual(e['side'],'up')

    def test_missing_symbol_data_fails_closed(self):
        bars,closes=stub(missing='NVDA')
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))
        bars,closes=stub()
        bars['NVDA'].pop(datetime.combine(DAY,time(9,30),ET))
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))

    def test_requires_own_move_and_peer_breadth(self):
        bars,closes=stub()
        bars['AMD'][datetime.combine(DAY,time(9,30),ET)][3]=100.8
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))
        bars,closes=stub()
        for s in PEERS[1:]:
            bars[s][datetime.combine(DAY,time(9,30),ET)][3]=100.9
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))

    def test_soxx_is_independently_required(self):
        bars,closes=stub()
        bars['SOXX'][datetime.combine(DAY,time(9,30),ET)][3]=100.9
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))

    def test_no_use_of_future_bar(self):
        bars,closes=stub()
        a=first_open_flip(bars,closes,'AMD',PRE,DAY)
        # Change future next-bar open and far-future close; decision unchanged.
        bars['AMD'][datetime.combine(DAY,time(9,35),ET)]=[12.3]*4+[10]
        bars['AMD'][datetime.combine(DAY,time(15,55),ET)]=[1.0]*4+[10]
        b=first_open_flip(bars,closes,'AMD',PRE,DAY)
        self.assertEqual(a['asof'],b['asof'])
        self.assertEqual(a['price'],b['price'])
        self.assertNotEqual(a['next_bar_open'],b['next_bar_open'])

    def test_later_confirmation_not_first_only(self):
        bars,closes=stub(post_value=100.6)
        at=datetime.combine(DAY,time(9,35),ET)
        for s in SYMS:bars[s][at]=[99.5]*4+[10]
        event=first_open_flip(bars,closes,'AMD',PRE,DAY)
        self.assertEqual(event['asof'],'2026-11-02T09:40:00-05:00')

    def test_no_premarket_false_bar_consumption(self):
        bars,closes=stub(at=time(9,25))
        self.assertIsNone(first_open_flip(bars,closes,'AMD',PRE,DAY))

    def test_bounded_limit_nonfill_zero(self):
        event={'side':'down','price':100.0,'next_bar_open':95.0}
        a=same_day_proxy(event,90.0,100.0)
        self.assertFalse(a['price_eligible'])
        self.assertEqual(a['bounded_advantage_14_pp'],0.0)
        event={'side':'up','price':100.0,'next_bar_open':105.0}
        b=same_day_proxy(event,110.0,100.0)
        self.assertFalse(b['price_eligible'])
        self.assertEqual(b['bounded_advantage_14_pp'],0.0)

if __name__=="__main__":
    unittest.main()
