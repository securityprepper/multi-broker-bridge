"""R1M session cap is silently carried across days by rolling 24-hour SQL.

Research-only reproduction. Uses isolated SQLite fixtures and *no* broker
credentials, network, production state mutations, services or broker orders.
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import direction_paper as dp
import one_minute_research as r

UTC=dt.timezone.utc
PREVIOUS_DAY=dt.datetime(2026,11,18,9,4,tzinfo=UTC)
NEW_SESSION=dt.datetime(2026,11,19,9,0,tzinfo=UTC)  # Thu 03:00 CT / 04:00 ET


def submit_fake_prior(db,i,symbol):
    instant=PREVIOUS_DAY+dt.timedelta(minutes=i*9)
    signal=dp.make_signal('R1M','CAP_PRIOR_'+str(i),symbol,'UP',
                          'R1M_FAST_UP',instant,price=100,close=0.25)
    assert dp.save_signal(db,signal,instant)
    db.execute(
      'INSERT INTO paper_attempts(id,signal_id,symbol,action,role,side,qty,limit_price,'
      'client_order_id,before_order_utc,broker_post_attempted,outcome,closed_at_utc)'
      'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
      ('MOCKCAP'+str(i),signal['id'],symbol,'UP','OPEN_CONFIRMED','buy','1',
       100,'MOCKCAP'+str(i),instant.isoformat(),1,'BROKER_FILL_VERIFIED',
       (instant+dt.timedelta(minutes=2)).isoformat()))
    db.commit()


class SessionCapLeakRepro(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db=dp.connect(Path(self.temp.name)/'test.db')
        r.setup(self.db)
        self.addCleanup(self.db.close)

    def test_20_previous_trading_session_posts_block_new_session(self):
        for i in range(20):
            submit_fake_prior(self.db,i,'AMD' if i<2 else 'MU' if i<4 else 'T'+str(i))
        self.assertEqual(r.session_key(PREVIOUS_DAY),'2026-11-18')
        self.assertEqual(r.session_key(NEW_SESSION),'2026-11-19')
        count,bysymbol,active=r.research_open_count(self.db,NEW_SESSION)
        # Production currently treats previous-day POSTs as today's POSTs.
        self.assertEqual(count,20)
        self.assertEqual(active,0)
        self.assertEqual(count,r.MAX_ENTRIES_PER_SESSION)
        self.assertEqual(bysymbol['AMD'],r.MAX_PER_SYMBOL_PER_SESSION)
        # A true 04:00 ET-start new-session count is zero: independent days.
        bounded=self.db.execute(
          'SELECT COUNT(*) FROM paper_attempts a JOIN signals s ON '
          'a.signal_id=s.signal_id WHERE s.source=? AND a.role=? '
          'AND a.broker_post_attempted=1 AND s.signal_at_utc>=?',
          ('R1M','OPEN_CONFIRMED',NEW_SESSION.isoformat())).fetchone()[0]
        self.assertEqual(bounded,0)
        self.assertTrue(r.r1m_entry_allowed(NEW_SESSION))
        # This documents a CODE-LEVEL BLOCKER; no prospective order occurred.

    def test_prior_session_per_symbol_limit_is_also_inherited(self):
        for i in range(2):
            submit_fake_prior(self.db,i,'AMD')
        count,bysymbol,active=r.research_open_count(self.db,NEW_SESSION)
        self.assertEqual(count,2)
        self.assertEqual(bysymbol['AMD'],2)
        self.assertEqual(active,0)
        # With a session-start bound, AMD is not symbol-cap-blocked.
        self.assertEqual(self.db.execute(
          "SELECT COUNT(*) FROM paper_attempts a JOIN signals s ON "
          "a.signal_id=s.signal_id WHERE a.symbol='AMD' "
          "AND s.signal_at_utc>=?",(NEW_SESSION.isoformat(),)
        ).fetchone()[0],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
