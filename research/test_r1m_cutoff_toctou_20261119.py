"""Read-only R1M entry cutoff time-of-check/time-of-use regression.
Mock-only PAPER order executor; no connected broker, actual POST or production writes.
"""
import datetime as dt
import tempfile, unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo
import one_minute_research as r
import direction_paper as dp
from test_direction_paper import PaperBroker, fake_newsclear, fake_shortclear

CT=ZoneInfo('America/Chicago')
def when(h,m,s=0):
    return dt.datetime(2026,11,19,h,m,s,tzinfo=CT).astimezone(dt.timezone.utc)
class SessionCutoffTOCTOU(unittest.TestCase):
    def test_policy_boundary(self):
        for start,post in ((when(13,14,58),when(13,15,3)),
                            (when(13,14,40),when(13,15,59)),
                            (when(13,14,59),when(13,40,1))):
            self.assertTrue(r.r1m_entry_allowed(start))
            self.assertFalse(r.r1m_entry_allowed(post))
    def test_preflight_crosses_cutoff_but_broker_mock_still_post_attempted(self):
        scan=when(13,14,58)
        actual_order_intent=when(13,15,8)
        with tempfile.TemporaryDirectory() as temp:
            db=dp.connect(Path(temp)/'s.db')
            r.setup(db)
            signal=dp.make_signal('R1M','cutoff-race-case','AMD','UP',
                 'R1M_FAST_UP',scan,price=100,close=0)
            signal['vs_close_pct']=0.0
            self.assertTrue(dp.save_signal(db,signal,scan))
            broker=PaperBroker()
            native=broker.__call__
            def fake_broker(method,path,body=None):
                if (method,path)==('GET','/v2/account'):
                    return {'id':'PAPER_TEST_ACCOUNT','status':'ACTIVE',
                            'trading_blocked':False,'cash':'10000','buying_power':'10000'}
                return native(method,path,body)
            def fake_quote(sym,asof):
                return {'bid':Decimal('99.99'),'ask':Decimal('100.00'),
                        'spread':Decimal('0.0001'),'time':actual_order_intent,'feed':'sip'}
            with patch.object(dp,'expected_account',return_value='PAPER_TEST_ACCOUNT'),\
                 patch.object(r,'utc_now',return_value=actual_order_intent):
                rows,why=r.research_open(db,signal,scan,broker=fake_broker,quotes=fake_quote,
                                        news_clear=fake_newsclear,short_news=fake_shortclear)
            # This is the current BUG: wall clock is past cutoff, but outdated
            # scan timestamp still permits a mock-only POST attempt.
            self.assertFalse(r.r1m_entry_allowed(actual_order_intent))
            self.assertEqual(len(broker.posts),1)
            self.assertEqual(len(rows),1)
            self.assertTrue(rows[0]['attempted'])
            self.assertIn('PAPER_POST_ATTEMPTED',why)
            db.close()
if __name__=='__main__':unittest.main(verbosity=2)
