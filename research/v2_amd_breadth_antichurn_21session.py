"""Research-only: point-in-time AMD morning sector-breadth and exits.
Sources: historical Alpaca SIP 1m trade marks, not bid/ask or executable fills.
All model signals come from completed minutes; fill proxies at NEXT minute OPEN.
Never connects to broker or changes V1. Final proxy flat 14:40 ET = 13:40 CT.
"""
import json,statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
S=('SOXX','AMD','MU','SNDK')
PAST=Path('/tmp/sector_complete_20session_alpaca_mixed.json')
NOV9=Path('/tmp/v2-amd-nov9-2026-asof-sip-1m.json')
DAILY=Path('/tmp/semis_52weeks_alpaca_daily.json')
POLICIES=('hold','tight1m','target_stop1','hard2p5','trend5m','trend5m_reentry')
def n(t):
 a,b=map(int,t.split(':'));return a*60+b
def tm(i):return f'{i//60:02}:{i%60:02}'
def et(t):return datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(ET)
def load():
 out=defaultdict(dict)
 j=json.loads(PAST.read_text())
 for d,names in j.items():
  for s in S:
   for t,v in names[s].items():
    if v[5]=='sip':
     out[d,s][et(t).strftime('%H:%M')]=[float(q)/(3 if s=='SOXX' and d<'2026-11-05' else 1) if i<4 else float(q) for i,q in enumerate(v[:5])]
 z=json.loads(NOV9.read_text())
 for s,arr in z['bars'].items():
  if s not in S:continue
  for row in arr:
   t=et(row[0]);d=t.date().isoformat()
   out[d,s][t.strftime('%H:%M')]=[float(q) for q in row[1:6]]
 raw=json.loads(DAILY.read_text())['raw']
 rawmap={(s,x[0][:10]):float(x[4]) for s in S for x in raw[s]}
 dates=sorted(j)+['2026-11-09']
 prev={}
 for i,d in enumerate(dates):
  p=dates[i-1] if i else '2026-10-09'
  for s in S:
   x=rawmap.get((s,p))
   if x:prev[d,s]=x/(3 if s=='SOXX' and p<'2026-11-05' else 1)
 return out,prev,dates
def close(b,t):return b[t][3] if t in b else None
def momentum(b,t,back):
 a=close(b,t);c=close(b,tm(n(t)-back))
 return 100*(a/c-1) if a and c else None
def signal(day,bars,prev):
 p={};m={}
 for s in S:
  cp=prev.get((day,s));now=close(bars[day,s],'08:34')
  if not cp or not now:return 0,False,{},{}
  p[s]=100*(now/cp-1);m[s]=momentum(bars[day,s],'08:34',5)
 sign=1 if p['SOXX']>=.2 and p['AMD']>=.2 and sum(p[s]>=.2 for s in S[1:])>=2 else (-1 if p['SOXX']<=-.2 and p['AMD']<=-.2 and sum(p[s]<=-.2 for s in S[1:])>=2 else 0)
 strength=bool(sign and all(m.get(s)!=None and sign*m[s]>=.1 for s in ('SOXX','AMD')) and sum(m[s]!=None and sign*m[s]>=.1 for s in S[1:])>=2)
 return sign,strength,p,m
def close_reason(day,bars,prev,side,policy,at,entry):
 a=close(bars[day,'AMD'],at)
 if a is None:return None
 gain=side*100*(a/entry-1)
 p=prev[day,'AMD'];current=100*(a/p-1)
 last15=momentum(bars[day,'AMD'],at,15)
 emergency=bool(last15 is not None and (current<=-2.5 and last15<=-1 if side==1 else current>=2.5 and last15>=1))
 if policy=='hold':return None
 if gain<=-2.5:return 'hard2p5'
 if emergency:return 'owner_2p5_and_15m_emergency'
 if policy=='hard2p5':return None
 if policy=='target_stop1' and (gain>=1 or gain<=-1):return 'target_stop1'
 if policy=='tight1m':
  stock=momentum(bars[day,'AMD'],at,1);sector=momentum(bars[day,'SOXX'],at,1)
  return 'tight1m' if stock is not None and sector is not None and side*stock<=-.1 and side*sector<=-.05 else None
 if policy in ('trend5m','trend5m_reentry'):
  m={s:momentum(bars[day,s],at,5) for s in S}
  if m['SOXX'] is not None and m['AMD'] is not None and side*m['SOXX']<=-.15 and side*m['AMD']<=-.25 and sum(m[s] is not None and side*m[s]<=-.1 for s in S[1:])>=2:return 'trend5m_breadth'
 return None
def simulate(day,bars,prev,side,policy):
 b=bars[day,'AMD']
 if '08:35' not in b or '14:40' not in b:return []
 fills=[];entrytm='08:35'
 for attempt in range(2 if policy=='trend5m_reentry' else 1):
  entry=b[entrytm][0];ending='14:40';reason='time_flat';mae=0
  for k in range(n(entrytm),n('14:40')):
   at=tm(k);next_time=tm(k+1)
   if at not in b:continue
   # high/low only for AFTER-THE-FACT risk measurements, not signals.
   adverse=100*((b[at][2] if side==1 else b[at][1])/entry-1)*side
   mae=min(mae,adverse)
   if next_time not in b:continue
   why=close_reason(day,bars,prev,side,policy,at,entry)
   if why:ending=next_time;reason=why;break
  exitp=b[ending][0];gross=side*100*(exitp/entry-1)
  fills.append({'entry':entrytm,'exit':ending,'price_in':round(entry,4),'price_out':round(exitp,4),
                'reason':reason,'gross':round(gross,4),'net30':round(gross-.30,4),'net60':round(gross-.60,4),
                'intratrade_mae':round(mae,4)})
  if policy!='trend5m_reentry' or ending=='14:40':break
  # Cooldown >=15m and fresh signal using last COMPLETED 1m (no same-bar fill).
  reentry=None
  for k in range(n(ending)+15,n('14:00')):
   a=tm(k-1);filltm=tm(k)
   if filltm not in b:continue
   pm={};mm={}
   for s in S:
    cp=prev.get((day,s));v=close(bars[day,s],a)
    if not cp or not v:break
    pm[s]=side*100*(v/cp-1);mm[s]=momentum(bars[day,s],a,5)
   if len(pm)!=4 or pm['SOXX']<.2 or pm['AMD']<.2 or sum(pm[s]>=.2 for s in S[1:])<2:continue
   if mm['SOXX'] is None or mm['AMD'] is None or side*mm['SOXX']<.1 or side*mm['AMD']<.1:continue
   if sum(mm[s] is not None and side*mm[s]>=.1 for s in S[1:])<2:continue
   reentry=filltm;break
  if not reentry:break
  entrytm=reentry
 return fills
def stats(cases):
 if not cases:return {'days':0,'tickets':0}
 x=[sum(t['net30'] for t in row['fills']) for row in cases]
 y=[sum(t['net60'] for t in row['fills']) for row in cases]
 wealth=peak=worst_dd=0
 for gain in x:
  wealth+=gain;peak=max(peak,wealth);worst_dd=min(worst_dd,wealth-peak)
 return {'days':len(cases),'tickets':sum(len(q['fills']) for q in cases),
         'winning_days':sum(v>0 for v in x),'mean_net30':round(statistics.mean(x),4),
         'total_net30_pp':round(sum(x),3),'mean_net60':round(statistics.mean(y),4),
         'worst_day_net30':round(min(x),4),
         'worst_intratrade_mae':round(min(t['intratrade_mae'] for row in cases for t in row['fills']),4),
         'fixed_notional_max_drawdown_pp':round(worst_dd,3),
         'early_exits':sum(t['reason']!='time_flat' for row in cases for t in row['fills'])}
def run():
 bars,prev,dates=load();decisions=[];rows=defaultdict(list)
 for day in dates:
  s,improve,p,m=signal(day,bars,prev)
  decisions.append({'day':day,'signal':'UP' if s==1 else 'DOWN' if s==-1 else 'ABSTAIN',
                    'improving5m':improve,'asof_changes_pct':p,'last5m_pct':m})
  if s==0:continue
  for gate in ('breadth','breadth_plus_5m'):
   if gate=='breadth_plus_5m' and not improve:continue
   for policy in POLICIES:
    fills=simulate(day,bars,prev,s,policy)
    if fills:rows[gate+'__'+policy].append({'day':day,'sign':s,'fills':fills})
 summary={k:{'all':stats(v),'first10_dates':stats([x for x in v if x['day']<='2026-10-23']),
    'remaining_dates':stats([x for x in v if x['day']>'2026-10-23']),
    'UP':stats([x for x in v if x['sign']==1]),'DOWN':stats([x for x in v if x['sign']==-1])}
    for k,v in rows.items()}
 return {'days':len(dates),'first':dates[0],'last':dates[-1],
         'decisions':decisions,'summary':summary,'event_rows':dict(rows)}
if __name__=='__main__':
 x=run();out=Path('/tmp/v2-run24-amd-antichurn')
 (out/'amd_21session_full.json').write_text(json.dumps(x,indent=2))
 print(json.dumps({'days':x['days'],'decisions':x['decisions'],'summary':x['summary'],
       'nov9':{k:[z for z in v if z['day']=='2026-11-09'] for k,v in x['event_rows'].items()}},indent=2))
