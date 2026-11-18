"""Read-only market-data SPY control aligned to original scan availability."""
import json,datetime as dt,urllib.parse,statistics
from pathlib import Path
from multi_broker_bridge.auto_paper import _fetch_json,market_headers
UTC=dt.timezone.utc
def parse(s):return dt.datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def iso(t):return t.isoformat()
p=Path('/tmp/v2_research_20261118_1030/expanded_first_seen_sip_20261118.json')
d=json.loads(p.read_text())
now=parse(d['asof_utc'])
url='https://data.alpaca.markets/v2/stocks/SPY/bars?'+urllib.parse.urlencode({'feed':'sip','timeframe':'1Min','adjustment':'split','start':'2026-11-18T14:25:00+00:00','end':iso(now),'limit':1000})
v=_fetch_json(url,headers=market_headers())
assert not v.get('next_page_token')
bars=sorted([(parse(x['t']),float(x['o']),float(x['c'])) for x in v.get('bars',[]) if parse(x['t'])+dt.timedelta(minutes=1)<=now and float(x['o'])>0 and float(x['c'])>0])
for row in d['rows']:
 t=parse(row['asof_utc' if 'asof_utc' in row else 'asof'])
 entry=next(((ts,o) for ts,o,c in bars if ts>=t),None)
 if not entry:continue
 for k in (15,60):
  stock=row.get(f'future_{k}m_net_proxy_pct')
  if not isinstance(stock,(int,float)):continue
  due=t+dt.timedelta(minutes=k)
  outs=[(ts,c) for ts,o,c in bars if ts+dt.timedelta(minutes=1)>due and ts+dt.timedelta(minutes=1)<=due+dt.timedelta(minutes=3)]
  if not outs:continue
  spy=100*(outs[0][1]/entry[1]-1)
  row[f'SPY_{k}m_gross_pct']=round(spy,3)
  row[f'vs_SPY_{k}m_minus_assumed_cost_pct']=round(stock-spy,3)
bench={}
for k in (15,60):
 values=[r[f'vs_SPY_{k}m_minus_assumed_cost_pct'] for r in d['rows'] if f'vs_SPY_{k}m_minus_assumed_cost_pct' in r]
 bench[f'{k}m']={'n':len(values),'positive_excess':sum(x>0 for x in values),
     'mean_excess_after_assumed_cost_pct':round(statistics.mean(values),3) if values else None,
     'median_excess_after_assumed_cost_pct':round(statistics.median(values),3) if values else None}
d['spy_matched_completed_minute_benchmark']=bench
d['benchmark_caveat']='SPY matched next-minute OHLC, not bid/ask. 0.25 percentage-point assumed friction applies only to stock, SPY treated as passive benchmark; no after-fee verified edge.'
p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
print('UPDATED_SAMPLE',d['cohort_first_25_by_first_scan_not_by_return'])
print('SPY_MATCHED',json.dumps(bench,sort_keys=True))
