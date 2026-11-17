"""Read-only R1M/V2 short-position safety regression; no broker traffic."""
import sys,datetime as dt
from unittest.mock import patch
sys.path.insert(0,'/opt/securityprepper/direction-paper-executor')
sys.path.insert(0,'/opt/securityprepper/multi-broker-bridge')
sys.path.insert(0,'/opt/securityprepper/recommendation-paper-bridge')
sys.path.insert(0,'/opt/securityprepper/sector-monitor')
import direction_paper as dp

class Cursor(list):
 def fetchall(self):return list(self)

class DB:
 def execute(self, sql, params=()):
  if sql.startswith('PRAGMA table_info(paper_attempts)'):
   return [(i,v) for i,v in enumerate(('fill_price','filled_qty','filled_at_utc','entry_signal_price','entry_vs_close_pct','entry_momentum_pct','exit_reason','audit_completed_at_utc'))]
  if sql.startswith('SELECT a.id,a.signal_id,a.symbol,a.side,a.filled_qty'):
   return Cursor([('TEST-ENTRY-ID','TEST-SIGNAL-ID','SNDK','sell',2.0,790.91,'V2','STOCK_EARLY_REVERSAL','DOWN',dt.datetime(2026,11,17,9,20,tzinfo=dt.timezone.utc).isoformat())])
  raise AssertionError('Unexpected DB call '+sql[:90])
 def commit(self):pass

def broker(method,path,*args):
 assert method=='GET',('NO_BROKER_WRITE_ALLOWED',method,path)
 if path=='/v2/account':return {'id':'TEST_ACCOUNT','status':'ACTIVE','trading_blocked':False}
 if path=='/v2/positions':return [{'symbol':'SNDK','qty':'-2','qty_available':'-2','side':'short'}]
 if path=='/v2/orders?status=open&limit=500':return []
 raise AssertionError('UNEXPECTED_BROKER_GET:'+path)

with patch.object(dp,'expected_account',return_value='TEST_ACCOUNT'):
 result=dp.software_risk_exits(DB(),dt.datetime(2026,11,17,12,36,tzinfo=dt.timezone.utc),broker=broker,
                            quotes=lambda *_: (_ for _ in ()).throw(AssertionError('QUOTE_NOT_EVEN_REACHED_FOR_SHORT')))
 print('V2_SHORT_SIGNED_QTY_REPLAY',result,'entry_qty',2,'broker_short_qty',-2)
 assert result==[]
 print('BUG_CONFIRMED_SHORT_POSITION_SKIPPED_BEFORE_QUOTE_AND_STOP')
