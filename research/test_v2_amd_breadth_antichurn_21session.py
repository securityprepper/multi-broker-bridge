"""Research-only offline integrity tests; no network or broker calls."""
import unittest,copy
from . import v2_amd_breadth_antichurn_21session as m
class TestAmdResearch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.bars,cls.prev,cls.days=m.load()
 def test_21_days(self):
  self.assertEqual(len(self.days),21)
  self.assertEqual(self.days[-1],'2026-11-09')
 def test_split_metadata_normalization(self):
  self.assertAlmostEqual(m.load()[0]['2026-11-04','SOXX']['08:34'][3]*3,460.88,delta=1)
 def test_nov9_0835_only_known_data(self):
  sign,improve,p,mm=m.signal('2026-11-09',self.bars,self.prev)
  self.assertEqual(sign,1)
  self.assertTrue(improve)
  self.assertGreater(p['AMD'],3)
 def test_future_prices_not_used_for_entry_signal(self):
  future=copy.deepcopy(self.bars)
  for s in m.S:
   if '14:39' in future['2026-11-09',s]:
    future['2026-11-09',s]['14:39'][3]*=.5
  self.assertEqual(m.signal('2026-11-09',future,self.prev),
                   m.signal('2026-11-09',self.bars,self.prev))
 def test_owner_2p5_contains_one_15m(self):
  # loss from previous close = -2.5, most recent 15m=-1.015,
  # but gain since entry; no additive -3.5 threshold permitted.
  bars=copy.deepcopy(self.bars)
  key=('2026-11-09','AMD')
  bars[key]['09:15'][3]=98.5
  bars[key]['09:30'][3]=97.5
  prev=dict(self.prev);prev[key]=100
  why=m.close_reason('2026-11-09',bars,prev,1,'trend5m','09:30',96)
  self.assertEqual(why,'owner_2p5_and_15m_emergency')
 def test_tight_stop_actual_nov9_simulated(self):
  ev=m.simulate('2026-11-09',self.bars,self.prev,1,'tight1m')
  self.assertEqual(ev[0]['exit'],'08:37')
  self.assertEqual(ev[0]['reason'],'tight1m')
 def test_policy_never_after_1340_ct(self):
  out=m.run()
  for case in out['event_rows'].values():
   for row in case:
    for event in row['fills']:
     self.assertLessEqual(m.n(event['exit']),m.n('14:40'))
                     # 14:40 ET == 13:40 Chicago
 def test_no_nov9_reentry_before_cooldown(self):
  ev=m.simulate('2026-11-09',self.bars,self.prev,1,'trend5m_reentry')
  self.assertLessEqual(len(ev),2)
  if len(ev)==2:
   self.assertGreaterEqual(m.n(ev[1]['entry'])-m.n(ev[0]['exit']),15)
 def test_nov9_hold_forward_gain(self):
  ev=m.simulate('2026-11-09',self.bars,self.prev,1,'hold')
  self.assertGreater(ev[0]['gross'],8.5)
  self.assertEqual(ev[0]['exit'],'14:40')
if __name__=='__main__':unittest.main()
