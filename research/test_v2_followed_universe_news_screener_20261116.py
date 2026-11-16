import datetime as dt,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import universe_screener as s
UTC=dt.timezone.utc
NOW=dt.datetime(2026,11,16,16,12,tzinfo=UTC)
class Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='sp-news-286-test-',dir='/tmp');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.output=self.root/'proofs';self.output.mkdir(mode=0o700)
  self.status=self.root/'status'/'current.json';self.status.parent.mkdir(mode=0o700)
  self.ledger=self.root/'ledger'/'coverage.json';self.ledger.parent.mkdir(mode=0o700)
  self.universe=self.root/'universe.json';self.tracked=['A'+str(i).zfill(3) for i in range(54)]+['FROG']
  self.tracked.sort();self.doc={'schema_version':1,'universe_name':'SECURITYPREPPER_NORMAL_FOLLOWED_STOCKS','symbols':self.tracked,'not_company_news_eligible_etf_references':['SOXX','XLE'],'retired_symbol_successors':{'CYBR':'PANW'}}
  self.universe.write_text(json.dumps(self.doc));self.universe.chmod(0o640)
 def test_real_sec_reference_owner_and_data(self):
  ids=s.load_sec_ticker_directory();self.assertGreater(len(ids),9000);self.assertIn('AMD',ids)
 def test_universe_valid_and_sorted(self):self.assertEqual(s.universe_read(self.universe),self.tracked)
 def test_universe_etf_rejected(self):
  self.doc['symbols'].append('SOXX');self.doc['symbols'].sort();self.universe.write_text(json.dumps(self.doc))
  with self.assertRaises(s.ScreeningBlocked):s.universe_read(self.universe)
 def test_universe_retired_rejected(self):
  self.doc['symbols'].append('CYBR');self.doc['symbols'].sort();self.universe.write_text(json.dumps(self.doc))
  with self.assertRaises(s.ScreeningBlocked):s.universe_read(self.universe)
 def test_universe_untrusted_file(self):
  self.universe.chmod(0o666)
  with self.assertRaises(s.ScreeningBlocked):s.universe_read(self.universe)
 def test_priority_mbb_unverified_included_for_review(self):
  with patch.object(s,'recent_mbb',return_value=['PANW','NVDA','SNDK']),patch.object(s,'recent_quality',return_value=['FTV']):
   selected=s.candidates(NOW,self.tracked,{'PANW':1,'NVDA':2,'SNDK':3,'FTV':4})
  self.assertIn('PANW',selected);self.assertIn('SNDK',selected);self.assertIn('NVDA',selected);self.assertIn('FTV',selected)
  self.assertEqual(len(selected),len(set(selected)))
 def test_coverage_rotation(self):
  core=set(self.tracked)
  all_seen=set()
  for step in range(40):
   at=NOW+dt.timedelta(minutes=step)
   with patch.object(s,'recent_mbb',return_value=[]),patch.object(s,'recent_quality',return_value=[]):
    selected=s.candidates(at,self.tracked,{})
   self.assertLessEqual(len(selected),s.MAX_BATCH)
   all_seen.update(selected)
  self.assertTrue(core.issubset(all_seen))
 def test_no_sector_or_invalid_symbols(self):
  selected=s.candidates(NOW,self.tracked,{'AMD':2488},mbb=['SECTOR:Semiconductors','BAD/ONE','ABC','AMD','AMD'],quality=['NXT P'])
  self.assertNotIn('BAD/ONE',selected);self.assertNotIn('SECTOR:Semiconductors',selected)
  self.assertEqual(selected.count('AMD'),1)
 def test_stale_quality_scan(self):
  db=self.root/'quality.sqlite3'
  import sqlite3
  with sqlite3.connect(db) as c:
   c.execute('CREATE TABLE scans(id INTEGER PRIMARY KEY,asof TEXT,signal_summary TEXT)')
   c.execute('INSERT INTO scans(asof,signal_summary) VALUES (?,?)',((NOW-dt.timedelta(minutes=5)).isoformat(),json.dumps({'shortlist':['PANW']})))
  self.assertEqual(s.recent_quality(NOW,db),[])
 def test_mbb_journal_does_not_trust_future(self):
  stamp=int((NOW+dt.timedelta(minutes=1)).timestamp()*1e6)
  out=json.dumps({'__REALTIME_TIMESTAMP':str(stamp),'MESSAGE':json.dumps({'status':'SCAN_COMPLETE','buy_watch_symbols':['AMD']})})+'\n'
  from types import SimpleNamespace
  self.assertEqual(s.recent_mbb(NOW,runner=lambda *a,**k:SimpleNamespace(returncode=0,stdout=out)),[])
 def test_partial_never_eligible(self):
  with patch.object(s,'sec_snapshot',return_value={'name':'Issuer','exchange':'NASDAQ','events':[]}),patch.object(s,'news_pages',return_value={'events':[]}):
   row=s.partial_screen('PANW',1327567,NOW,lambda:NOW)
  self.assertFalse(row['buy_clearance_eligible']);self.assertEqual(row['status'],'NEWS_UNKNOWN_OFFICIAL_ISSUER_RSS_UNVERIFIED')
 def test_partial_news_review_still_no_buy(self):
  with patch.object(s,'sec_snapshot',return_value={'name':'Issuer','exchange':'NASDAQ','events':[]}),patch.object(s,'news_pages',return_value={'events':[{'status':'review_needed'}]}):
   row=s.partial_screen('PANW',1327567,NOW,lambda:NOW)
  self.assertFalse(row['buy_clearance_eligible']);self.assertIn('REVIEW',row['status'])
 def test_holiday_paused_returns_silent_no_scan(self):
  with patch.object(s,'holiday_allows',return_value=False):
   result=s.run(now=NOW,source=self.output,status=self.status,ledger=self.ledger,universe=self.universe)
  self.assertEqual(result['status'],'HOLIDAY_FAIL_CLOSED');self.assertEqual(list(self.output.iterdir()),[])
 def test_unknown_sec_identity_not_eligible(self):
  with patch.object(s,'holiday_allows',return_value=True),patch.object(s,'universe_read',return_value=self.tracked),patch.object(s,'load_sec_ticker_directory',return_value={}),patch.object(s,'partial_screen',side_effect=AssertionError('bad')):
   res=s.run(now=NOW,source=self.output,status=self.status,ledger=self.ledger,universe=self.universe,forced=['A001'],do_mbb=False,do_quality=False)
  self.assertEqual(res['checked_status_by_symbol']['A001'],'NEWS_UNKNOWN_SEC_IDENTITY_UNAVAILABLE');self.assertEqual(list(self.output.glob('*.json')),[])
 def test_no_official_rss_writes_no_clearance(self):
  with patch.object(s,'holiday_allows',return_value=True),patch.object(s,'universe_read',return_value=self.tracked),patch.object(s,'load_sec_ticker_directory',return_value={'A001':123}),patch.object(s,'partial_screen',return_value={'status':'REVIEW_WATCH_ONLY_MISSING_ISSUER_SOURCE','buy_clearance_eligible':False}):
   res=s.run(now=NOW,source=self.output,status=self.status,ledger=self.ledger,universe=self.universe,forced=['A001'],do_mbb=False,do_quality=False)
  self.assertEqual(res['three_source_bundles_published'],0);self.assertEqual(res['paper_broker_orders'],0)
  self.assertFalse((self.output/'A001.json').exists());self.assertEqual(len(json.loads(self.ledger.read_text())['symbols']),len(self.tracked))
 def test_full_requires_existing_real_issuer_feed(self):
  with patch.object(s,'holiday_allows',return_value=True),patch.object(s,'universe_read',return_value=self.tracked),patch.object(s,'load_sec_ticker_directory',return_value={'FROG':1800667}),patch.object(s,'source_manifest',return_value={'evidence':[],'symbol':'FROG'}):
   res=s.run(now=NOW,source=self.output,status=self.status,ledger=self.ledger,universe=self.universe,forced=['FROG'],do_mbb=False,do_quality=False)
  self.assertEqual(res['three_source_bundles_published'],1)
  self.assertTrue((self.output/'FROG.json').is_file())
  self.assertEqual(res['buy_clearances_published_by_screener'],0)
 def test_no_broker_order_interfaces(self):
  import inspect
  code=inspect.getsource(s)
  for disallowed in ('submit_order(', 'place_order(', 'cancel_order(', 'modify_order(', '/v2/orders', '/v2/positions'):
   self.assertNotIn(disallowed,code)
if __name__=='__main__':unittest.main()
