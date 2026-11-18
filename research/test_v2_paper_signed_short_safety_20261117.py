"""Isolated owner-authorized V2 PAPER safety release regression tests.

Mock broker only: no API credentials, real orders, LIVE, timers or Pushover.
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
import direction_paper as p

CHICAGO=p.CT
def ct(day,hour,minute=0):
    return dt.datetime(2026,11,day,hour,minute,tzinfo=CHICAGO).astimezone(p.UTC)
ENTRY=ct(17,9,10)

def quote(sym,now, bid='101.1',ask='101.2'):
    b=Decimal(bid);a=Decimal(ask)
    return {'bid':b,'ask':a,'time':now,'spread':(a-b)/a,'feed':'sip'}

class Broker:
    def __init__(self,sym='AMD',shares=4,side='short',available=None):
        self.positions=[{'symbol':sym,'side':side,
            'qty':str(-shares if side=='short' else shares),
            'qty_available':str((-shares if side=='short' else shares) if available is None else available)}]
        self.orders=[]
        self.posts=[]
        self.account_id='PAPER_TEST_ACCOUNT'
    def __call__(self,method,path,body=None):
        if method=='GET' and path=='/v2/account':
            return {'id':self.account_id,'status':'ACTIVE','trading_blocked':False}
        if method=='GET' and path=='/v2/positions':return self.positions
        if method=='GET' and path.startswith('/v2/orders?status=open'):return self.orders
        if method=='GET' and path.startswith('/v2/assets/'):
            return {'symbol':path.removeprefix('/v2/assets/'),'tradable':True,
                    'overnight_tradable':True,'shortable':True,'easy_to_borrow':True}
        if method=='POST' and path=='/v2/orders':
            self.posts.append(body)
            return {'id':'OFFLINE-MOCK-'+str(len(self.posts)),'status':'accepted'}
        if method=='GET' and path.startswith('/v2/orders:by_client_order_id?'):
            from urllib.parse import parse_qs,urlsplit
            key=parse_qs(urlsplit(path).query)['client_order_id'][0]
            for i,b in enumerate(self.posts,1):
                if b['client_order_id']==key:
                    return {'id':'OFFLINE-MOCK-'+str(i),'client_order_id':key,'status':'accepted'}
        raise AssertionError('UNEXPECTED_REAL_BROKER_PATH '+method+' '+path)

def seeded(db,sym='AMD',shares=4,side='sell',price=100,when=ENTRY):
    sig=p.make_signal('V2','SIGNED-TEST|'+sym+'|'+when.isoformat(),sym,
                       'DOWN' if side=='sell' else 'UP',
                       'STOCK_URGENT_OBSERVED',when,price)
    assert p.save_signal(db,sig,when)
    client='SPD-MOCK-ENTRY-'+sym
    db.execute('INSERT INTO paper_attempts('
      'id,signal_id,symbol,action,role,side,qty,limit_price,client_order_id,'
      'before_order_utc,broker_post_attempted,outcome,filled_qty,fill_price,filled_at_utc)'
      ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
      (client,sig['id'],sym,sig['direction'],'OPEN_CONFIRMED',side,str(shares),str(price),
       client,when.isoformat(),1,'BROKER_FILL_VERIFIED',
       float(shares),float(price),(when+dt.timedelta(seconds=15)).isoformat()))
    db.commit()
    return sig

class Safety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=p.connect(Path(self.tmp.name)/'ledger.sqlite3')
        p.migrate_audit(self.db)
        self.addCleanup(self.db.close)
        self.acct=patch.object(p,'expected_account',return_value='PAPER_TEST_ACCOUNT')
        self.acct.start();self.addCleanup(self.acct.stop)
    def test_real_signed_short_matches_only_exact_side_and_availability(self):
        good={'side':'short','qty':'-4','qty_available':'-4'}
        self.assertEqual(p.owned_whole_position_qty(good,'sell',4),4)
        for bad in (
           {'side':'short','qty':'4','qty_available':'4'},
           {'side':'long','qty':'-4','qty_available':'-4'},
           {'side':'short','qty':'-5','qty_available':'-5'},
           {'side':'short','qty':'-4','qty_available':'-3'},
           {'side':'short','qty':'-4','qty_available':'4'},
           {'side':'short','qty':'-4'},
           {'side':'short','qty':'-4','qty_available':'-5'},
           {'side':'short','qty':'-4','qty_available':'NaN'},
        ):
            self.assertIsNone(p.owned_whole_position_qty(bad,'sell',4),bad)
        self.assertEqual(p.owned_whole_position_qty(
            {'side':'long','qty':'4','qty_available':'4'},'buy',4),4)
        self.assertIsNone(p.owned_whole_position_qty(good,'sell',4.5))
    def test_signed_short_stop_before_flat_posts_buy_cover_once(self):
        seeded(self.db)
        broker=Broker()
        now=ct(17,10,0)
        exits=p.software_risk_exits(self.db,now,broker=broker,quotes=quote)
        self.assertEqual(len(exits),1)
        self.assertEqual(exits[0]['role'],'RISK_EXIT_STOP_LOSS')
        self.assertEqual(broker.posts[0]['side'],'buy')
        self.assertEqual(broker.posts[0]['qty'],'4')
        self.assertEqual(broker.posts[0]['type'],'limit')
        self.assertEqual(len(p.software_risk_exits(self.db,now,broker=broker,quotes=quote)),0)
        self.assertEqual(len(broker.posts),1)
    def test_1340_flat_sticky_priority_until_next_trading_window(self):
        seeded(self.db)
        broker=Broker()
        self.assertFalse(p.session_flat_due(ENTRY,ct(17,13,39)))
        for t in (ct(17,13,40),ct(17,13,59),ct(17,14),ct(17,20,59),ct(18,3),ct(20,9)):
            self.assertTrue(p.session_flat_due(ENTRY,t),t)
        self.assertFalse(p.paper_exit_window(ct(17,20,59)))
        self.assertTrue(p.paper_exit_window(ct(18,3,0)))
        # Closed overnight: no quotes and no broker POST.
        exits=p.software_risk_exits(self.db,ct(17,20,59),broker=broker,
                 quotes=lambda *args: (_ for _ in ()).throw(AssertionError('CLOSED_WINDOW_MUST_NOT_QUOTE')))
        self.assertEqual(exits,[])
        self.assertEqual(broker.posts,[])
        # Next premarket: the same prior-session fill is still overdue.
        now=ct(18,3,1)
        exits=p.software_risk_exits(self.db,now,broker=broker,
                 quotes=lambda sym,when:quote(sym,when,bid='98.9',ask='99.0'))
        self.assertEqual(len(exits),1)
        self.assertEqual(exits[0]['role'],'RISK_EXIT_SESSION_FLAT_1340_CT')
        self.assertEqual(broker.posts[0]['side'],'buy')
        self.assertTrue(broker.posts[0]['extended_hours'])
    def test_1339_does_not_flat_profitable_and_1340_does(self):
        seeded(self.db)
        broker=Broker()
        below=lambda sym,now:quote(sym,now,bid='99.6',ask='99.7')
        self.assertEqual(p.software_risk_exits(self.db,ct(17,13,39),broker,below),[])
        self.assertEqual(broker.posts,[])
        exits=p.software_risk_exits(self.db,ct(17,13,40),broker,below)
        self.assertEqual(len(exits),1)
        self.assertEqual(exits[0]['role'],'RISK_EXIT_SESSION_FLAT_1340_CT')
    def test_stop_profit_when_pre_flat_includes_no_overnight_retry(self):
        seeded(self.db)
        b=Broker()
        q=lambda sym,now:quote(sym,now,bid='98.2',ask='98.3')
        exits=p.software_risk_exits(self.db,ct(17,10),b,q)
        self.assertEqual(len(exits),1)
        self.assertEqual(exits[0]['role'],'RISK_EXIT_PROFIT_TARGET')
    def test_wrong_account_and_mismatched_qty_never_posts(self):
        seeded(self.db)
        b=Broker(shares=6)
        self.assertEqual(p.software_risk_exits(self.db,ct(17,13,41),b,quote),[])
        self.assertEqual(b.posts,[])
        b.positions[0]['qty']='-4'
        b.positions[0]['qty_available']='-2'
        self.assertEqual(p.software_risk_exits(self.db,ct(17,13,41),b,quote),[])
        self.assertEqual(b.posts,[])
        b.positions[0]['qty_available']='-4';b.account_id='WRONG_ACCOUNT'
        with self.assertRaises(ValueError):
            p.software_risk_exits(self.db,ct(17,13,41),b,quote)
        self.assertEqual(b.posts,[])
    def test_open_order_blocks_duplicate_close_even_if_flat_due(self):
        seeded(self.db)
        b=Broker()
        b.orders=[{'symbol':'AMD','status':'accepted','side':'buy'}]
        self.assertEqual(p.software_risk_exits(self.db,ct(17,13,42),b,quote),[])
        self.assertEqual(b.posts,[])
    def test_early_rebound_closes_exact_short_without_new_long(self):
        seeded(self.db)
        b=Broker()
        signal=p.make_signal('V2','RISK-FIX-EARLY', 'AMD','UP','EARLY_REBOUND',ct(17,10),price=100)
        self.assertTrue(p.save_signal(self.db,signal,ct(17,10)))
        actions,status=p.decide_and_attempt(self.db,signal,ct(17,10),b,quote)
        self.assertEqual(status,'WAIT_CLOSE_FILL_BEFORE_REVERSE')
        self.assertEqual(len(actions),1)
        self.assertEqual(actions[0]['role'],'CLOSE_OPPOSING')
        self.assertEqual(b.posts[0]['side'],'buy')
        self.assertEqual(len(b.posts),1)
    def test_v2_entry_cutoff_and_unresolved_lock(self):
        self.assertTrue(p.v2_entry_window(ct(17,3,0)))
        self.assertTrue(p.v2_entry_window(ct(17,13,14)))
        self.assertFalse(p.v2_entry_window(ct(17,13,15)))
        self.assertFalse(p.v2_entry_window(ct(17,20,0)))
        self.assertFalse(p.v2_entry_window(ct(15,20)))
        b=Broker();b.positions=[]
        sig=p.make_signal('V2','TEST-NEW-MU','MU','DOWN','STOCK_URGENT_OBSERVED',ct(17,13,15),price=90)
        acts,status=p.decide_and_attempt(self.db,sig,ct(17,13,15),b,quote)
        self.assertEqual(acts,[])
        self.assertEqual(status,'V2_ENTRY_OUTSIDE_0400_ET_TO_1315_CT')
        self.assertEqual(b.posts,[])
        seeded(self.db)
        fresh=p.make_signal('V2','TEST-NEW-MU-WED','MU','DOWN','STOCK_URGENT_OBSERVED',ct(18,3),price=90)
        acts,status=p.decide_and_attempt(self.db,fresh,ct(18,3),b,quote)
        self.assertEqual(acts,[])
        self.assertEqual(status,'V2_UNCLOSED_POSITION_NO_NEW_ENTRY')
        self.assertEqual(b.posts,[])
    def test_duplicate_signal_return_contract_and_no_broker_access(self):
        sig=p.make_signal('V2','DUP-NO-POST','AMD','UP','EARLY_REBOUND',ct(17,10),price=100)
        self.assertTrue(p.save_signal(self.db,sig,ct(17,10)))
        check=p.apply_signal(self.db,sig,ct(17,10),execute=True,
             broker=lambda *a: (_ for _ in ()).throw(AssertionError('NO_BROKER_CALL')),
             quotes=lambda *a: (_ for _ in ()).throw(AssertionError('NO_QUOTE')))
        self.assertEqual(check['notification'],'NO_POST_NO_TRADING_ALERT')
        self.assertEqual(check['order_attempts'],0)
        self.assertEqual(check['status'],'ALREADY_HANDLED')
        self.assertEqual(check['symbol'],'AMD')
    def test_daily_flat_not_a_order_if_session_closed(self):
        seeded(self.db)
        b=Broker()
        for t in (ct(17,23),ct(21,9),ct(22,11)):
            self.assertEqual(p.software_risk_exits(self.db,t,b,
              lambda *a: (_ for _ in ()).throw(AssertionError('CLOSED'))),[])
        self.assertEqual(b.posts,[])

if __name__=="__main__":unittest.main(verbosity=2)
