"""V2 separate historical study; does NOT touch installed monitors or PAPER orders.
Use pre-existing 9-stock trades, selectively delay only unprofitable 08:30 exits.
All results hypothetical with five-minute OHLC price proxies, no live fills.
"""
import sys,io,contextlib,datetime as dt,collections,statistics,math
from pathlib import Path
sys.path.insert(0,'/tmp')
with contextlib.redirect_stdout(io.StringIO()):import semis_year_day_context as u
from semis_year_intraday_chronological import calendar,daily_map,bydate,S,LEAD,E,D,T
from semis_peer_transfer_study import peers

ALL=u.trades
BASE={d:[] for d in calendar}
for x in ALL:BASE[x['day']].append(x)
def five_day_negative(d):
 i=calendar.index(d)
 if i<6:return False
 d0=calendar[i-6];prev=calendar[i-1]
 changes={s:daily_map[s][prev][4]/daily_map[s][d0][4]-1 for s in S}
 return sum(changes[s]<0 for s in LEAD)>=2 and changes['SOXX']<0
BLOCKED_CATALYST={'2026-02-05'} # historical retrospective news veto; V1 code handles in live, modeled V2 excludes.

def tape(s,d):
 if s in peers:return peers[s]
 day=dt.date.fromisoformat(d)
 z=dict(bydate[s].get(str(day-T(days=1)),{}));z.update(bydate[s].get(d,{}))
 return z

def parse_entry(t,d):
 clock=D.strptime(d[:4]+'-'+t['entry'],'%Y-%m-%d %H:%M').replace(tzinfo=E)
 if clock.date().isoformat()>d:clock=clock.replace(year=clock.year-1)
 return clock

def estimate_exit(t,d,clock,allowance=.0015):
 b=tape(t['symbol'],d).get(clock)
 if not b:return None
 return round(b[3]*(1-allowance),2)

def strategy(policy='baseline',stop_loss=None,trail=None,exit_at='14:55',use_catalyst=True,only_downtrend=False, profit_cut=0):
 records=[];missing=[]
 for trade in ALL:
  day=trade['day'];s=trade['symbol']
  if only_downtrend and not five_day_negative(day):continue
  if use_catalyst and day in BLOCKED_CATALYST:continue
  buy=trade.get('entry_limit',trade.get('price'));qty=trade['qty'];pnl=trade['pnl']
  entry=parse_entry(trade,day);start=D.combine(dt.date.fromisoformat(day),dt.time(9,30),E)
  if entry>=start:continue
  # Decision based ONLY on the completed 8:25 ET bar, available at 8:30.
  # Never infer buy/sell fill from the 8:30 OHLC high or a later quote.
  cutoff=D.combine(dt.date.fromisoformat(day),dt.time(8,25),E)
  cutoff_row=tape(s,day).get(cutoff)
  if not cutoff_row:
   missing.append((day,s,'MISSING_0825_CLOSE'));continue
  model_exit=round(cutoff_row[3]*.9985,2)
  simulated_premarket_pnl=round(qty*(model_exit-buy),2)
  if policy=='baseline' or simulated_premarket_pnl>profit_cut:
   result=simulated_premarket_pnl;reason='PREMARKET_AT_0825_MARK';out_time='08:30'
  else:
   # Explicitly determine losing at 08:30 without looking at future bars.
   tt=tape(s,day)
   terminal=D.combine(dt.date.fromisoformat(day),dt.time.fromisoformat(exit_at),E)
   # Optional 9:30 market-opening stop and 5min OHLC trailing, conservative.
   price=None;reason=None;out_time=None
   ceiling=None
   if stop_loss is not None or trail is not None:
    for tick in sorted(x for x in tt if start<=x<=terminal):
     bar=tt[tick]
     if ceiling is None:ceiling=bar[0]
     if stop_loss is not None:
      level=buy*(1-stop_loss)
      if bar[2]<=level:
       price=round(min(bar[0],level)*.9985,2)
       reason='STOPLOSS';out_time=tick.strftime('%H:%M');break
     if trail is not None:
      level=max(buy,ceiling)*(1-trail)
      if bar[2]<=level:
       price=round(min(bar[0],level)*.9985,2)
       reason='TRAIL';out_time=tick.strftime('%H:%M');break
      ceiling=max(ceiling,bar[1])
   if price is None:
    price=estimate_exit(trade,day,terminal)
    reason='DEFERRED_MARK_'+exit_at;out_time=exit_at
   if price is None:
    missing.append((day,s,exit_at));continue
   result=round(qty*(price-buy),2)
  records.append({'day':day,'symbol':s,'pnl':result,'reason':reason,'exit_time':out_time,'prev_pnl':simulated_premarket_pnl})
 return records,missing

def summarize(records):
 byday=collections.defaultdict(float)
 for x in records:byday[x['day']]+=x['pnl']
 early=[x for x in records if x['day']<='2026-08-31'];later=[x for x in records if x['day']>'2026-08-31']
 return {'days':len(byday),'trades':len(records),'wins':sum(p>0 for p in byday.values()),'losses':sum(p<0 for p in byday.values()),'total':round(sum(byday.values()),2),'train':round(sum(x['pnl'] for x in early),2),'later':round(sum(x['pnl'] for x in later),2),'later_ex_Nov6':round(sum(x['pnl'] for x in later if x['day']!='2026-11-06'),2),'byday':dict(byday),'held_count':sum(x['reason']!='PREMARKET_AT_0825_MARK' for x in records),'win_after_held':sum(x['pnl']>0 for x in records if x['reason']!='PREMARKET_AT_0825_MARK')}

if __name__=='__main__':
 for onlydown in (True,False):
  print('\nCOHORT',('PREVIOUS_FIVE_DOWN' if onlydown else 'ALL_BULLISH'),'FEB5_CATALYST_EXCLUDED',flush=True)
  for policy in ('baseline','conditional'):
   for exitat in (('08:30',) if policy=='baseline' else ('09:30','09:45','10:00','10:30','11:00','12:00','13:00','14:55')):
    r,missing=strategy(policy,exit_at=exitat,use_catalyst=True,only_downtrend=onlydown)
    summary=summarize(r)
    print('CONDITIONAL',policy,exitat,'DAYS',summary['days'],'WINS',summary['wins'],'P_L',summary['total'],'TRAIN',summary['train'],'LATER',summary['later'],'LATER_EX_NOV6',summary['later_ex_Nov6'],'HELD_STOCK_POSITIONS',summary['held_count'],'MISSING',missing[:3], 'EXAMPLES',{k:round(summary['byday'].get(k,0),2) for k in ('2026-03-04','2026-08-12','2026-11-06')},flush=True)
  for st in (.015,.025,.04):
   r,missing=strategy('conditional',stop_loss=st,exit_at='14:55',use_catalyst=True,only_downtrend=onlydown)
   q=summarize(r)
   print('LATE_STOP',st,'WINS',q['wins'],'TOTAL',q['total'],'TRAIN',q['train'],'LATER',q['later'],'HELD',q['held_count'],'MISSING',len(missing))
