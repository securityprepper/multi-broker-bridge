import copy
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from research.v2_score_sealed_sector_shadow_20261109 import score_snapshot

ET=ZoneInfo('America/New_York')
SNAP={
 'time_of_observation_utc':'2026-11-10T14:35:25+00:00',
 'earliest_later_entry_at_ET':'2026-11-10T09:40:25-05:00',
 'forecast_slot_ET':'09:35',
 'sectors':{
  'semiconductors':{
   'status':'ASOF_FEATURES','shadow_classification':'EXPLORATORY_BEARISH_SEMI_WATCH_ONLY',
   'features':{'SOXX':{'observed_price':100,'observed_bar_end_ET':'2026-11-10T09:35:00-05:00'}}},
  'gold_miners':{'status':'ABSTAIN_MISSING_ASOF_DATA','features':{}}
 }
}
def bars():
 # 09:40 open is TOO EARLY for saved earliest entry 09:40:25.
 result=[]
 for n in range(9*60+35,14*60+40,5):
  hh,mm=divmod(n,60)
  x=100 if n<9*60+45 else 99
  if n>=10*60+35:x=98
  if n>=14*60+35:x=97
  result.append({'t':datetime(2026,11,10,hh,mm,tzinfo=ET).isoformat(),
   'o':x,'h':x,'l':x,'c':x})
 return result
class TestSealedScoring(unittest.TestCase):
 def test_cannot_score_before_observation(self):
  with self.assertRaises(ValueError):score_snapshot(SNAP,{'SOXX':bars()},'2026-11-10T14:35:00Z')
 def test_premature_outcomes_are_not_hits(self):
  r=score_snapshot(SNAP,{'SOXX':bars()},'2026-11-10T14:40:00Z')
  self.assertEqual(r['sectors']['semiconductors']['forward']['forward_15m']['status'],'NOT_YET_OBSERVABLE')
  self.assertIsNone(r['sectors']['semiconductors']['trade_mark_proxy'])
 def test_post_signal_score_cannot_use_earlier_0930_prior_move(self):
  r=score_snapshot(SNAP,{'SOXX':bars()},'2026-11-10T20:00:00Z')
  s=r['sectors']['semiconductors']
  self.assertTrue(s['forward']['forward_60m']['direction_hit'])
  self.assertAlmostEqual(s['forward']['forward_60m']['signed_after_signal_pct'],2)
  self.assertIn('14:45:00',s['trade_mark_proxy']['entry_bar_start_utc'])
  self.assertTrue(s['trade_mark_proxy']['after_cost_win'])
  self.assertFalse(s['trade_mark_proxy']['real_fill'])
  self.assertTrue(s['trade_mark_proxy']['forward_60m_after_cost_win'])
  self.assertLessEqual(s['trade_mark_proxy']['worst_intratrade_excursion_pct'],0)
 def test_sorted_json_feature_order_does_not_score_amd_instead_of_soxx(self):
  p=copy.deepcopy(SNAP)
  p['sectors']['semiconductors']['features']={'AMD':{'observed_price':480,'observed_bar_end_ET':'2026-11-10T09:35:00-05:00'},**p['sectors']['semiconductors']['features']}
  r=score_snapshot(p,{'SOXX':bars(),'AMD':bars()},'2026-11-10T20:00:00Z')
  self.assertEqual(r['sectors']['semiconductors']['signal_baseline_price'],100)
 def test_does_not_invent_missing_bar(self):
  b=[x for x in bars() if x['t']!='2026-11-10T10:35:00-05:00']
  r=score_snapshot(SNAP,{'SOXX':b},'2026-11-10T20:00:00Z')
  self.assertEqual(r['sectors']['semiconductors']['forward']['forward_60m']['status'],'MISSING_BAR')
 def test_stale_asof_abstains(self):
  p=copy.deepcopy(SNAP)
  p['sectors']['semiconductors']['features']['SOXX']['observed_bar_end_ET']='2026-11-10T09:15:00-05:00'
  self.assertEqual(score_snapshot(p,{'SOXX':bars()},'2026-11-10T20:00:00Z')['sectors']['semiconductors']['status'],'ABSTAIN_STALE_OR_FUTURE_SIGNAL_BAR')
 def test_missing_sector_abstains(self):
  self.assertEqual(score_snapshot(SNAP,{'SOXX':bars()},'2026-11-10T20:00:00Z')['sectors']['gold_miners']['status'],'ABSTAIN_ASOF')
 def test_conflicting_bar_fails_closed(self):
  b=bars();evil=dict(b[0],c=55,l=55,h=100);b.append(evil)
  with self.assertRaises(ValueError):score_snapshot(SNAP,{'SOXX':b},'2026-11-10T20:00:00Z')
 def test_nonfinite_fails_closed(self):
  b=bars();b[0]=dict(b[0],c=float('nan'))
  with self.assertRaises(ValueError):score_snapshot(SNAP,{'SOXX':b},'2026-11-10T20:00:00Z')
 def test_full_output_no_orders(self):
  r=score_snapshot(SNAP,{'SOXX':bars()},'2026-11-10T20:00:00Z')
  self.assertEqual(r['orders_submitted'],0)
  self.assertFalse(r['historical_execution_quotes_verified'])
  self.assertFalse(r['short_borrow_verified'])
if __name__=='__main__':unittest.main()
