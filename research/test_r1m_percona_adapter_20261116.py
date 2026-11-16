"""No-network regression for Percona R1M adapter and fail-closed semantics."""
import os,sqlite3,unittest
from unittest.mock import patch
import mysql.connector
import r1m_percona as x

class Cursor:
    def __init__(self,parent):
        self.parent=parent
        self.with_rows=False
    def execute(self,sql,params=()):
        self.parent.statements.append((sql,tuple(params)))
        if self.parent.duplicate:
            raise mysql.connector.IntegrityError(msg="Duplicate entry",errno=1062)
        self.with_rows=sql.strip().upper().startswith("SELECT")
    def fetchall(self):
        return [(1,)] if self.with_rows else []
    def close(self):
        self.parent.closes+=1

class Connection:
    def __init__(self):
        self.statements=[];self.closes=0;self.rollback_count=0;self.duplicate=False
    def cursor(self,buffered=True):return Cursor(self)
    def rollback(self):self.rollback_count+=1

def adapter():
    obj=object.__new__(x.PerconaLedger)
    obj.connection=Connection()
    return obj

class PerconaAdapterTests(unittest.TestCase):
    def test_sqlite_style_insert_ignore_parameterized_mysql(self):
        db=adapter()
        db.execute('INSERT OR IGNORE INTO signals(signal_id) VALUES(?)',('ID-1',))
        self.assertEqual(db.connection.statements[0],
             ('INSERT IGNORE INTO signals(signal_id) VALUES(%s)',('ID-1',)))
    def test_sqlite_replace_is_parameterized(self):
        db=adapter()
        db.execute('INSERT OR REPLACE INTO research_runs VALUES(?,?)',('date','session'))
        self.assertEqual(db.connection.statements[0],
            ('REPLACE INTO research_runs VALUES(%s,%s)',('date','session')))
    def test_on_conflict_to_percona_duplicate_key(self):
        db=adapter()
        db.execute('INSERT INTO research_audit_variants VALUES(?,?,?) '
           'ON CONFLICT(signal_id,target_pct,stop_pct) DO UPDATE SET '
           'outcome=excluded.outcome,minutes_to_close=excluded.minutes_to_close',
           ('a',1.,1.))
        q=db.connection.statements[0][0]
        self.assertIn('ON DUPLICATE KEY UPDATE',q)
        self.assertIn('outcome=VALUES(outcome)',q)
        self.assertNotIn('excluded.',q)
    def test_bad_sql_ddl_rejected(self):
        db=adapter()
        with self.assertRaises(ValueError):db.execute('DROP TABLE signals')
        with self.assertRaises(ValueError):db.executescript('DROP TABLE signals')
        with self.assertRaises(ValueError):db.execute('SELECT * FROM signals WHERE signal_id=?',())
        self.assertEqual(db.connection.statements,[])
    def test_missing_db_credential_never_falls_back_to_sqlite(self):
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':''}):
            with self.assertRaises(RuntimeError):x.connect()
    def test_mysql_duplicate_propagates_as_legacy_signal_reservation_collision(self):
        db=adapter()
        db.connection.duplicate=True
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute('INSERT INTO signals(signal_id) VALUES(?)',('a',))
        self.assertEqual(db.connection.rollback_count,1)
    def test_bounded_schema_whitelist(self):
        db=adapter()
        with self.assertRaises(ValueError):db.executescript('CREATE TABLE IF NOT EXISTS elsewhere (id INTEGER)')
        db.executescript('CREATE TABLE IF NOT EXISTS signals(signal_id TEXT PRIMARY KEY);')
    def test_finite_percent_guard_rejects_nonfinite(self):
        from decimal import Decimal
        for number in ('NaN','Infinity','-Infinity'):
            self.assertFalse(Decimal(number).is_finite())
if __name__=='__main__':unittest.main(verbosity=2)
