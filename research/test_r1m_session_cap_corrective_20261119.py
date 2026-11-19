"""Research-only corrective R1M PAPER session-cap regression tests.

Isolated in-memory/temp SQLite only. No credential access, broker POST, or
production systemd service interaction. Do not deploy this research patch.
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

import direction_paper as dp
import one_minute_research as r

UTC=dt.timezone.utc
ET=ZoneInfo('America/New_York')
def at_et(year,month,day,hour,minute=0,second=0):
    return dt.datetime(year,month,day,hour,minute,second,tzinfo=ET).astimezone(UTC)

def create_attempt(db,n,symbol,when,posted=1,closed=True):
    signal=dp.make_signal('R1M','MOCK_DAY_BOUND_'+str(n),symbol,'UP','R1M_FAST_UP',
                          when,price=100,close=0.25)
    assert dp.save_signal(db,signal,when)
    db.execute(
      'INSERT INTO paper_attempts(id,signal_id,symbol,action,role,side,qty,limit_price,'
      'client_order_id,before_order_utc,broker_post_attempted,outcome,closed_at_utc)'
      ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
      ('MOCKSESSION'+str(n),signal['id'],symbol,'UP','OPEN_CONFIRMED','buy','1',100,
       'MOCKSESSION'+str(n),when.isoformat(),posted,
       'BROKER_FILL_VERIFIED' if posted else 'NOT_SUBMITTED',
       (when+dt.timedelta(minutes=4)).isoformat() if closed else None))
    db.commit()

class PaperSessionCapRegression(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=dp.connect(Path(self.temp.name)/'test.db')
        r.setup(self.db)
        self.addCleanup(self.db.close)
    def test_reset_exactly_at_next_0400_eastern(self):
        yesterday=at_et(2026,11,18,4,4)
        for n in range(20):
            create_attempt(self.db,n,'AMD' if n<2 else 'S'+str(n),
                           yesterday+dt.timedelta(minutes=n*9))
        prev=r.research_open_count(self.db,at_et(2026,11,19,3,59,59))
        self.assertEqual(prev[0],20)
        self.assertEqual(prev[1]['AMD'],2)
        self.assertEqual(prev[2],0)
        new=r.research_open_count(self.db,at_et(2026,11,19,4))
        self.assertEqual(new,(0,{},0))
        self.assertTrue(r.r1m_entry_allowed(at_et(2026,11,19,4)))
    def test_same_session_twenty_total_two_per_symbol(self):
        start=at_et(2026,11,19,4,1)
        for n in range(20):
            create_attempt(self.db,n,'AMD' if n<2 else 'X'+str(n),
                           start+dt.timedelta(seconds=n))
        c,by,active=r.research_open_count(self.db,start+dt.timedelta(minutes=2))
        self.assertEqual(c,r.MAX_ENTRIES_PER_SESSION)
        self.assertEqual(by['AMD'],r.MAX_PER_SYMBOL_PER_SESSION)
        self.assertEqual(active,0)
        self.assertEqual(r.research_open_count(self.db,at_et(2026,11,20,4)),(0,{},0))
    def test_unsubmitted_and_other_source_attempts_not_counted(self):
        start=at_et(2026,11,19,4,1)
        create_attempt(self.db,1,'AMD',start,posted=0)
        c,by,active=r.research_open_count(self.db,start+dt.timedelta(minutes=5))
        self.assertEqual((c,by,active),(0,{},0))
    def test_previous_day_open_exposure_remains_concurrent(self):
        create_attempt(self.db,1,'NVDA',at_et(2026,11,18,5),closed=False)
        c,by,active=r.research_open_count(self.db,at_et(2026,11,19,4))
        self.assertEqual(c,0)
        self.assertEqual(by,{})
        self.assertEqual(active,1)  # global risk cap survives reset
    def test_dst_spring_and_fall_boundaries(self):
        spring=r.r1m_entry_session_bounds(at_et(2026,3,7,4))
        spring_hours=(dt.datetime.fromisoformat(spring[1])-dt.datetime.fromisoformat(spring[0])).total_seconds()/3600
        self.assertEqual(spring_hours,23)
        fall=r.r1m_entry_session_bounds(at_et(2026,10,31,4))
        fall_hours=(dt.datetime.fromisoformat(fall[1])-dt.datetime.fromisoformat(fall[0])).total_seconds()/3600
        self.assertEqual(fall_hours,25)
        for start,end in (spring,fall):
            self.assertLess(dt.datetime.fromisoformat(start),dt.datetime.fromisoformat(end))
    def test_naive_clock_fails_closed_and_weekend_not_admitted(self):
        with self.assertRaises(ValueError):
            r.r1m_entry_session_bounds(dt.datetime(2026,11,19,4))
        self.assertFalse(r.r1m_entry_allowed(at_et(2026,11,21,4)))
        self.assertFalse(r.r1m_entry_allowed(at_et(2026,11,20,19)))

if __name__=='__main__':unittest.main(verbosity=2)
