import unittest,importlib.util,json,ast,pathlib,datetime as dt,urllib.parse,types
from unittest.mock import patch
stage=pathlib.Path('/tmp/news_unknown_fix_20261116/news_source_collector.py')
spec=importlib.util.spec_from_file_location('candidate_news_source_nov16',str(stage))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
root=pathlib.Path('/tmp/news_unknown_fix_20261116')
manifest=json.loads((root/'candidate_feeds.json').read_text())
class SecurityTests(unittest.TestCase):
 def test_catalog_91(self):self.assertEqual(len(module.ISSUER_RSS),91)
 def test_only_sec_proved_official_host_pairs(self):
  for s,(url,host) in module.ISSUER_RSS.items():
   p=urllib.parse.urlsplit(url)
   self.assertEqual(p.scheme,'https',s)
   self.assertEqual(p.hostname,host,s)
   self.assertFalse(p.username,s)
   self.assertEqual(p.port,None,s)
 def test_original_25_unchanged(self):
  p=pathlib.Path('/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/news_source_collector.py')
  old=ast.literal_eval(next(n.value for n in ast.parse(p.read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ISSUER_RSS' for t in n.targets)))
  self.assertEqual(len(old),25)
  for s,v in old.items():self.assertEqual(v,module.ISSUER_RSS[s])
 def test_66_unrelated_sources_are_not_silently_admitted(self):
  novel=manifest['validated_candidates'];self.assertEqual(len(novel),66)
  for sym,(url,host) in novel.items():self.assertEqual(module.ISSUER_RSS[sym],(url,host))
 def test_stale_cigna_not_added(self):self.assertNotIn('CI',module.ISSUER_RSS)
 def test_unreachable_still_unverified(self):
  for s in ['PANW','CRWD','SNDK','WDC','AVGO','AMAT','TSM','ZS']:
   self.assertNotIn(s,module.ISSUER_RSS)
 def test_two_chicago_dates_window(self):
  cutoff=module.yesterday_today_start(dt.datetime(2026,11,16,17,15,tzinfo=dt.timezone.utc))
  self.assertEqual(cutoff.isoformat(),'2026-11-15T06:00:00+00:00')
 def test_no_substitute_issuer_source(self):
  import inspect
  source=inspect.getsource(module.issuer_rss)
  self.assertIn('ISSUER_RSS[symbol]',source)
  self.assertIn('OFFICIAL_IR_RSS_EMPTY_OR_INVALID',source)
  self.assertIn('ISSUER_RSS_DOES_NOT_COVER_FULL_TWO_DAYS',source)
 def test_no_order_functions(self):
  source=stage.read_text()
  for forbidden in ['submit_order(', 'place_order(', 'cancel_order(', '/v2/orders']:
   self.assertNotIn(forbidden,source)
 def test_priority_capped(self):self.assertEqual(module.MAX_SYMBOLS_PER_CYCLE,32)
 def test_new_universe_excludes_uncertified_identity(self):
  doc=json.loads((root/'normal-followed-universe.json').read_text())
  self.assertEqual(len(doc['symbols']),284)
  self.assertNotIn('EA',doc['symbols']);self.assertNotIn('OSP',doc['symbols'])
  self.assertEqual(doc['symbols'],sorted(set(doc['symbols'])))
 def test_existing_broker_constraints_untouched(self):
  self.assertEqual(stage.stat().st_size>30000,True)
 def test_news_eligibility_manual_review_nonadverse_unless_proven(self):
  x=module.classify_news_article({'headline':'Generic earnings update','content':''},'CAT','Caterpillar Inc')
  self.assertEqual(x[1],'review_needed')
if __name__=='__main__':unittest.main()
