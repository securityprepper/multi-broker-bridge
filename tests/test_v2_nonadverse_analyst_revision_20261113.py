import unittest
from datetime import datetime,timezone,timedelta
from recommendation_paper_bridge.news_eligibility import evaluate_news_asof,CATEGORIES
NOW=datetime(2026,11,13,21,0,tzinfo=timezone.utc)
SYMBOL='FTV';CIK='0001659166'
def bundle(status):
 start='2026-11-12T06:00:00+00:00'
 return dict(symbol=SYMBOL,exchange='NYSE',issuer_cik=CIK,asof_utc=NOW.isoformat(),
     identity={'verified':True,'symbol':SYMBOL,'exchange':'NYSE','issuer_cik':CIK,'first_observed_at':(NOW-timedelta(seconds=20)).isoformat()},
     coverage=[{'symbol':SYMBOL,'issuer_cik':CIK,'source':src,'verified_complete':True,
       'first_observed_at':(NOW-timedelta(seconds=5)).isoformat(),
       'coverage_since':start,'coverage_through':(NOW-timedelta(seconds=2)).isoformat(),
       'source_reference':'OFFICIAL:'+src,'content_hash':'a'*64,
       'categories':list(CATEGORIES)} for src in ('sec_edgar','issuer_ir','licensed_news')],
     evidence=[{'symbol':SYMBOL,'issuer_cik':CIK,'source':'licensed_news',
       'published_at':(NOW-timedelta(hours=20)).isoformat(),
       'first_observed_at':(NOW-timedelta(seconds=8)).isoformat(),
       'source_reference':'ALPACA_NEWS:record','content_hash':'b'*64,
       'category':'analyst_upgrade','status':status}])
class LiveReducerCompatibility(unittest.TestCase):
 def test_verified_nonadverse_numeric_analyst_raise_allowed(self):
  self.assertEqual(evaluate_news_asof(**bundle('verified_nonadverse'))['status'],'NEWS_CLEAR_ASOF')
 def test_unknown_contradiction_not_allowed(self):
  self.assertEqual(evaluate_news_asof(**bundle('review_needed'))['status'],'NEWS_REVIEW_WATCH_ONLY')
 def test_positive_but_unknown_is_not_auto_cleared(self):
  self.assertEqual(evaluate_news_asof(**bundle('unverified_positive'))['status'],'NEWS_REVIEW_WATCH_ONLY')
 def test_in_window_adverse_never_cleared(self):
  self.assertEqual(evaluate_news_asof(**bundle('material_adverse_verified'))['status'],'NEWS_MATERIAL_ADVERSE')
if __name__=='__main__':unittest.main()
