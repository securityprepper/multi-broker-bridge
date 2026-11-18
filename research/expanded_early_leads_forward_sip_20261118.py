"""GET-only, as-of first observed, completed SIP minute bar research; no broker P/L claims."""
import json,sqlite3,datetime as dt,urllib.parse,collections,statistics,os
from pathlib import Path
from zoneinfo import ZoneInfo
from multi_broker_bridge.auto_paper import _fetch_json,market_headers
UTC=dt.timezone.utc
CT=ZoneInfo('America/Chicago')
def parse(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def iso(t):return t.astimezone(UTC).isoformat()
now=dt.datetime.now(UTC)
c=sqlite3.connect('file:/var/lib/securityprepper-quality-watch/state.sqlite3?mode=ro',uri=True)
start=parse('2026-11-18T14:30:00+00:00');end=parse('2026-11-18T15:30:00+00:00')
signals={}
preflight=set()
for asof,s in c.execute('SELECT asof,signal_summary FROM scans WHERE asof>=? AND asof<=? ORDER BY asof',(iso(start),iso(end))):
 t=parse(asof)
 if not start<=t<=end:continue
 data=json.loads(s)
 for sym in data.get('shortlist',[]):preflight.add(sym)
 for item in data.get('expanded_buy_preflight_candidates',[]):
  sym=item.get('symbol')
  if not sym or sym in signals:continue
  stamped=parse(item['asof_utc'])
  # Actual availability may be later than stamped bar, never earlier than scan time.
  available=max(t,stamped)
  if available>now-dt.timedelta(minutes=10):continue
  signals[sym]={'asof':iso(available),'first_source_bar':iso(stamped),'score':item.get('score'),
                 'weak_sector':item.get('weak_sector_exception'),'peer_count':len(item.get('peer_evidence',[]))}
sigs=sorted(signals.items(),key=lambda kv:parse(kv[1]['asof']))
# Freeze a small representative contemporaneous cohort, not outcome-picked:
# earliest 25 unique leads by observation time, with no post-price rank filter.
sigs=sigs[:25]
stock_data={}
fetch_failed={}
for sym,entry in sigs+[('SPY',{'asof':iso(start)})]:
 try:
  stamp=parse(entry['asof'])
  q=urllib.parse.urlencode({'feed':'sip','timeframe':'1Min','adjustment':'split',
         'start':iso(stamp-dt.timedelta(minutes=3)),'end':iso(min(now,stamp+dt.timedelta(minutes=70))),
         'limit':1000})
  url='https://data.alpaca.markets/v2/stocks/'+urllib.parse.quote(sym,safe='')+'/bars?'+q
  res=_fetch_json(url,headers=market_headers())
  if res.get('next_page_token'):raise ValueError('PAGINATED_INCOMPLETE')
  bars=[]
  for v in res.get('bars',[]):
   ts=parse(v['t']); close=float(v['c']); opening=float(v['o']);volume=float(v.get('v',0))
   if ts+dt.timedelta(minutes=1)<=now and close>0 and opening>0 and volume>0:bars.append((ts,opening,close))
  stock_data[sym]=sorted(bars)
 except Exception as e:fetch_failed[sym]=type(e).__name__
rows=[]
for sym,signal in sigs:
 t=parse(signal['asof']);bars=stock_data.get(sym,[])
 # first completed fully future bar; requires scan availability before bar start.
 entry=next(((ts,o) for ts,o,cl in bars if ts>=t),None)
 row={'symbol':sym,**signal,'source':'QW_EXPANDED_EARLY_PEER','entry_bar':iso(entry[0]) if entry else None}
 if entry:
  row['entry_price_NEXT_OPEN_PROXY']=entry[1]
  for horizon in (15,60):
   due=t+dt.timedelta(minutes=horizon)
   if due>now:row[f'future_{horizon}m']='NOT_YET_OBSERVED';continue
   vals=[(ts,cl) for ts,o,cl in bars if ts+dt.timedelta(minutes=1)>due and ts+dt.timedelta(minutes=1)<=due+dt.timedelta(minutes=3)]
   if not vals:row[f'future_{horizon}m']='QUOTE_BAR_GAP';continue
   close=vals[0][1]
   row[f'future_{horizon}m_net_proxy_pct']=round((close/entry[1]-1)*100-0.25,3)
   row[f'future_{horizon}m']='COMPLETE_BAR_PROXY_0.25PCT_ASSUMED_COST'
 rows.append(row)
summary={}
for k in (15,60):
 vals=[r[f'future_{k}m_net_proxy_pct'] for r in rows if f'future_{k}m_net_proxy_pct' in r]
 summary[f'{k}m']={'n_valid':len(vals),'wins':sum(x>0 for x in vals),
    'mean_assumed_cost_proxy_pct':round(statistics.mean(vals),3) if vals else None,
    'median_assumed_cost_proxy_pct':round(statistics.median(vals),3) if vals else None}
result={'research_only':True,'asof_utc':iso(now),'cohort_first_25_by_first_scan_not_by_return':len(sigs),
 'total_expanded_unique_in_window':len(signals),'source_time_window_utc':[iso(start),iso(end)],
 'outcome_after_true_scan_availability':True,'data_feed':'Alpaca SIP 1min completed OHLC, not executable quotes',
 'simulation_warning':'0.25pct assumed total roundtrip costs; no actual ask/bid, fees, native fills or stops; no trading edge proof',
 'horizon_summaries':summary,'failed_symbols':fetch_failed,'rows':rows}
out=Path('/tmp/v2_research_20261118_1030/expanded_first_seen_sip_20261118.json')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows',)},sort_keys=True))
print('EXAMPLE_ROWS',[(r['symbol'],r.get('future_15m_net_proxy_pct'),r.get('future_60m_net_proxy_pct')) for r in rows[:12]])
