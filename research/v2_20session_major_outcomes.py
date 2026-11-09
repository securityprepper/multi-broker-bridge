"""Daily major upside/downside audit of the 20-session SIP anti-churn cohort.

Post-close labels are outcomes ONLY and never consulted in 09:35 forecasts.
Research-only: no Alpaca orders or active V1 paths.
"""
import json,csv
from pathlib import Path
from collections import Counter
try:
 from . import v2_20session_anti_churn_replay as base
except ImportError:
 import v2_20session_anti_churn_replay as base
SIP5=Path('/tmp/semis_52wk_5min_sip_adjusted.json')
SIP20=Path('/tmp/sector_complete_20session_alpaca_mixed.json')
def audit():
 hist=base.prior_5_history()
 data=json.loads(SIP20.read_text())
 out=[]
 for day in sorted(data):
  bars=base.daily_1min(data,day)
  if not bars:continue
  prior={s:base.previous_five(hist[s],day) for s in base.ALL}
  if not all(prior.values()):continue
  prev={s:prior[s][-1] for s in base.ALL}
  base.reconcile_sector_price_basis(bars,prev["SOXX"])
  sig=base.sign_at_window(bars,prev)
  qualified=set(base.eligible_stocks(bars,prev,sig)) if sig else set()
  for sym in base.ALL:
   ends=[p for d,p in hist[sym] if d==day]
   if len(ends)!=1:continue
   close=ends[0];openx=bars[sym]['09:30'][0]
   pct=100*(close/prev[sym]-1)
   rth=100*(close/openx-1)
   side='UP' if max(pct,rth)>=5 else 'DOWN' if min(pct,rth)<=-5 else 'NONE'
   hit=(sig==1 and side=='UP' or sig==-1 and side=='DOWN')
   # stock-specific actionable warning also requires stock itself to meet as-of entry rule.
   stock_action=(sym=='SOXX' and sig!=0 or sym in qualified)
   out.append({'day':day,'symbol':sym,'previous_close_pct':round(pct,4),'rth_open_close_pct':round(rth,4),
               'major_5pct_side':side,'sector_0935_forecast':'UP' if sig==1 else 'DOWN' if sig==-1 else 'ABSTAIN',
               'early_sector_correct_direction':hit,'stock_0935_entry_eligible':bool(stock_action),
               'early_0935_bigmove_hit':bool(hit and stock_action)})
 return out
if __name__=='__main__':
 rows=audit()
 out=Path('/tmp/v2-run20-broker-churn/v2_20session_major_outcomes.csv')
 with out.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 for scope in ('SOXX','STOCKS'):
  z=[r for r in rows if (r['symbol']=='SOXX')==(scope=='SOXX')]
  majors=[r for r in z if r['major_5pct_side']!='NONE']
  print(scope,'all_stocks_days',len(z),'major_up',sum(r['major_5pct_side']=='UP' for r in majors),
      'major_down',sum(r['major_5pct_side']=='DOWN' for r in majors),
      'correct_sector_0935_direction',sum(r['early_sector_correct_direction'] for r in majors),
      'stock_eligible_0935',sum(r['early_0935_bigmove_hit'] for r in majors),
      'major_misses',[(r['day'],r['symbol'],r['major_5pct_side']) for r in majors if not r['early_0935_bigmove_hit']])
 print('Audit rows',len(rows))
