"""Broker-disabled tests for R1M entry cutoff and sticky 13:40 CT flat.

Only temporary SQLite test ledgers and fake PAPER brokers. No POST to Alpaca.
"""
from __future__ import annotations
import datetime as dt
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import direction_paper as dp
import one_minute_research as r
from test_direction_paper import PaperBroker, fake_newsclear, fake_shortclear

CT=r.CT
def chicago(day,hour,minute=0,second=0,month=11):
    return dt.datetime(2026,month,day,hour,minute,second,tzinfo=CT).astimezone(dt.timezone.utc)

def offered(symbol,now,ask='100.10',bid='100.00'):
    a=Decimal(ask);b=Decimal(bid)
    return {'ask':a,'bid':b,'spread':(a-b)/a,'time':now,'feed':'sip'}

def synthetic_entry(db, when, sym='AMD', fill_when=None,side='buy'):
    filled=fill_when or when
    sig=dp.make_signal('R1M',sym+'|CLOCK_GUARD|'+when.isoformat(),sym,
                       'UP' if side=='buy' else 'DOWN','R1M_FAST_UP' if side=='buy' else 'R1M_FAST_DOWN',
                       when,price=100,close=0.5)
    assert dp.save_signal(db,sig,when)
    attempt_id='MOCK-'+sig['id']
    db.execute('INSERT INTO paper_attempts('
      'id,signal_id,symbol,action,role,side,qty,limit_price,client_order_id,'
      'before_order_utc,broker_post_attempted,outcome,filled_at_utc,filled_qty,fill_price)'
      ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (attempt_id,sig['id'],sym,sig['direction'],'OPEN_CONFIRMED',side,'2','100.00',
       attempt_id,filled.isoformat(),1,'BROKER_FILL_VERIFIED',filled.isoformat(),2.,100.))
    db.commit()
    return attempt_id

class ClockSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=dp.connect(Path(self.tmp.name)/'research.db')
        r.setup(self.db)
        self.addCleanup(self.db.close)
    def test_positive_window_12_boundary_cases(self):
        allowed=[
            chicago(18,3,0),
            chicago(18,3,1),
            chicago(18,9,0),
            chicago(18,13,14,59),
            chicago(16,12,30),
        ]
        prohibited=[
            chicago(18,2,59,59),chicago(18,0),
            chicago(18,13,15),chicago(18,13,16),chicago(18,18,59),
            chicago(18,19,0),chicago(18,21,0),chicago(19,1,0),
            chicago(21,9,0),chicago(22,19,0),
        ]
        for when in allowed:
            with self.subTest(when=when,allowed=True):self.assertTrue(r.r1m_entry_allowed(when))
        for when in prohibited:
            with self.subTest(when=when,allowed=False):self.assertFalse(r.r1m_entry_allowed(when))
    def test_dst_and_time_zone_untrusted(self):
        self.assertTrue(r.r1m_entry_allowed(chicago(12,3,0,month=3)))
        self.assertFalse(r.r1m_entry_allowed(chicago(12,13,15,month=3)))
        self.assertFalse(r.r1m_entry_allowed(dt.datetime(2026,11,18,9,0)))
    def test_cutoff_rejects_before_any_broker_access(self):
        times=(chicago(18,2),chicago(18,13,15),
               chicago(18,19),chicago(18,23),chicago(21,12))
        for i,now in enumerate(times):
            with self.subTest(now=now):
                s=dp.make_signal('R1M','blocked-entry-'+str(i),'AMD','UP','R1M_FAST_UP',
                                 now,price=100,close=0.5)
                def impossible(*args,**kwargs):
                    raise AssertionError('BROKER_OR_QUOTES_MUST_NOT_BE_TOUCHED')
                acts,reason=r.research_open(self.db,s,now,
                  broker=impossible,quotes=impossible,
                  news_clear=impossible,short_news=impossible)
                self.assertEqual(acts,[])
                self.assertEqual(reason,'RESEARCH_ENTRY_OUTSIDE_0400_ET_TO_1315_CT')
    def test_legitimate_premarket_paper_mock_still_possible(self):
        now=chicago(18,3,5)
        s=dp.make_signal('R1M','allowed-entry','AMD','UP','R1M_FAST_UP',
                         now,price=100,close=0.5)
        self.assertTrue(dp.save_signal(self.db,s,now))
        b=PaperBroker()
        real=b.__call__
        def paper(method,path,body=None):
            if (method,path)==('GET','/v2/account'):
                return {'id':'TEST_ACCOUNT','status':'ACTIVE','trading_blocked':False,
                        'cash':'10000','buying_power':'10000'}
            return real(method,path,body)
        with patch.object(dp,'expected_account',return_value='TEST_ACCOUNT'):
            acts,reason=r.research_open(self.db,s,now,broker=paper,quotes=offered,
                                        news_clear=fake_newsclear,short_news=fake_shortclear)
        self.assertEqual(len(acts),1)
        self.assertEqual(acts[0]['role'],'OPEN_CONFIRMED')
        self.assertEqual(len(b.posts),1)
        self.assertTrue(b.posts[0]['extended_hours'])
        self.assertLessEqual(int(b.posts[0]['qty'])*Decimal(b.posts[0]['limit_price']),r.RESEARCH_NOTIONAL)
    def test_flat_deadline_nine_cases_stays_due(self):
        entry=chicago(17,8,0)
        cases=[
           (chicago(17,13,39),False),
           (chicago(17,13,39,59),False),
           (chicago(17,13,40),True),
           (chicago(17,13,59),True),
           (chicago(17,14),True),
           (chicago(17,23,59),True),
           (chicago(18,0,0),True),
           (chicago(18,3,0),True),
           (chicago(20,9,0),True),
           (chicago(22,21,0),True),
        ]
        for moment,expected in cases:
            with self.subTest(now=moment):
                self.assertIs(r.r1m_flat_due(entry.isoformat(),moment),expected)
    def test_original_fill_anchor_not_current_clock_or_signal_date(self):
        started=chicago(17,10)
        next_fill=chicago(18,3,0)
        self.assertFalse(r.r1m_flat_due(next_fill.isoformat(),chicago(18,10)))
        self.assertTrue(r.r1m_flat_due(next_fill.isoformat(),chicago(18,13,40)))
        self.assertTrue(r.r1m_flat_due(started.isoformat(),chicago(18,3)))
        with self.assertRaises(ValueError):
            r.r1m_flat_due('not_an_ISO_time',chicago(18,3))
    def test_overdue_fill_gets_forced_close_after_midnight_mock_only(self):
        entry=chicago(17,10)
        synthetic_entry(self.db,entry)
        b=PaperBroker(positions=[{'symbol':'AMD','side':'long','qty':'2','qty_available':'2'}])
        now=chicago(18,3,5)
        q=lambda sym,at:offered(sym,at,'100.04','99.98')
        with patch.object(dp,'expected_account',return_value='PAPER_TEST_ACCOUNT'):
            acts,blocked=r.manage_research_exits(
                self.db,now,broker=b,quotes=q,trend_fn=lambda *a:None)
            repeat,_=r.manage_research_exits(
                self.db,now,broker=b,quotes=q,trend_fn=lambda *a:None)
        self.assertEqual(blocked,[])
        self.assertEqual(len(acts),1)
        self.assertEqual(acts[0]['role'],'R1M_RISK_EXIT_FLAT_BY_1340_CT')
        self.assertEqual(b.posts[0]['side'],'sell')
        self.assertEqual(b.posts[0]['qty'],'2')
        self.assertEqual(len(repeat),0)
        self.assertEqual(len(b.posts),1)
    def test_flat_priority_over_profitable_or_loss_stop(self):
        now=chicago(17,13,40)
        synthetic_entry(self.db,chicago(17,9,10))
        b=PaperBroker(positions=[{'symbol':'AMD','side':'long','qty':'2','qty_available':'2'}])
        q=lambda sym,at:offered(sym,at,'101.7','101.6')
        with patch.object(dp,'expected_account',return_value='PAPER_TEST_ACCOUNT'):
            acts,_=r.manage_research_exits(self.db,now,b,q,trend_fn=lambda *a:{'p1':-.1,'p3':-.2})
        self.assertEqual(len(acts),1)
        self.assertEqual(acts[0]['role'],'R1M_RISK_EXIT_FLAT_BY_1340_CT')
        self.assertEqual(len(b.posts),1)

if __name__=='__main__':unittest.main(verbosity=2)
