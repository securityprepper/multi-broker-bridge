"""Read-only, event-date-controlled descriptive pre-earnings study, never execution."""
import json,statistics,collections,random,datetime as dt
from pathlib import Path
P=Path('/var/lib/securityprepper-earnings-anticipation')
b=json.loads((P/'research-20261116-broad-market-pre-earnings-3809.json').read_text())
s=json.loads((P/'research-20261116-sector-98-last-earnings.json').read_text())
latest=json.loads((P/'latest.json').read_text())
pairs=b['pairs'];group_syms=set(s['events'])
assert len(pairs)==3809 and len(group_syms)==98
duplicates=collections.Counter((x['symbol'],x['earnings_date']) for x in pairs)
assert max(duplicates.values())==1
groups=collections.defaultdict(list)
for x in pairs:groups[x['earnings_date']].append(x)
summary={'metadata':{'source_rows':len(pairs),'event_dates':len(groups),'sector_tickers':len(group_syms),
'sector_events':sum(x['symbol'] in group_syms for x in pairs),'duplicate_symbol_date':0,
'limitations':['historical adjusted close not executable ask-bid or after-fee return',
'calendar release dates were retrospectively queried and not issuer verified',
'sector membership frozen at present as proxy, not point-in-time membership',
'event-date peer-earnings cross-section is not SPY or true market benchmark',
'news and analyst point-in-time estimates unavailable','correlated symbols and dates; no holdout forward trades']}}
for h in (5,10,15):
 ret='return'+str(h)+'_pct'
 controls={date:statistics.mean(x[ret] for x in rows if x['symbol'] not in group_syms)
           for date,rows in groups.items() if sum(x['symbol'] not in group_syms for x in rows)>=3}
 matching=[(x['earnings_date'],x['symbol'],float(x[ret]),float(x[ret])-controls[x['earnings_date']])
           for x in pairs if x['symbol'] in group_syms and x['earnings_date'] in controls]
 assert matching
 def stats(rows):
  if not rows:return None
  raw=[r[2] for r in rows];diff=[r[3] for r in rows]
  return {'n':len(rows),'dates':len(set(r[0] for r in rows)),'unique_symbols':len(set(r[1] for r in rows)),
   'positive_pct':round(100*sum(z>0 for z in raw)/len(raw),3),'mean_return_pct':round(statistics.mean(raw),3),
   'mean_vs_same_earnings_date_peer_pctpoints':round(statistics.mean(diff),3),
   'median_vs_peer_pctpoints':round(statistics.median(diff),3),
   'positive_vs_peer_pct':round(100*sum(z>0 for z in diff)/len(diff),3)}
 bydate=collections.defaultdict(list)
 for item in matching:bydate[item[0]].append(item)
 dates=list(bydate)
 rng=random.Random(20261116+int(h))
 bootstrap=[]
 for _ in range(2500):
  resampled=[r for date in (rng.choice(dates) for i in dates) for r in bydate[date]]
  bootstrap.append(statistics.mean(r[3] for r in resampled))
 bootstrap.sort()
 k=len(bootstrap)
 agg=stats(matching)
 agg['event_date_cluster_bootstrap_mean_vs_peer_95pct_interval_pp']=[
  round(bootstrap[int(.025*k)],3),round(bootstrap[int(.975*k)-1],3)]
 agg['calendar_split_descriptive_only']={
   'Aug_Sep':stats([x for x in matching if x[0]<'2026-10']),
   'Oct_Nov':stats([x for x in matching if x[0]>='2026-10'])}
 summary['horizon_'+str(h)+'_prior_closes']=agg
 symbol_hist=collections.defaultdict(list)
 for x in pairs:symbol_hist[x['symbol']].append(x)
 def eligible(c,years):
  f=c.get('fundamentals',{})
  rev=f.get('annual_revenue_yoy_pct_recent_then_prior') or []
  eps=f.get('annual_eps_yoy_pct_recent_then_prior') or []
  return len(rev)>=years and len(eps)>=years and all(z>=15 for z in rev[:years]+eps[:years])
 strict={x['symbol'] for x in latest['candidates'] if eligible(x,2)}
 relaxed={x['symbol'] for x in latest['candidates'] if eligible(x,1)}
 # Current 2026 Nov snapshot must NOT be used as a historical execution feature.
 if h==5:
  for name,syms in [('two_fiscal_intervals_15pct_current',strict),('last_fiscal_interval_15pct_current',relaxed)]:
   rs=[(x['symbol'],x['earnings_date'],x[ret]) for x in pairs if x['symbol'] in syms]
   summary[name]={'prospective_candidates':len(syms),'historical_earnings_events':len(rs),
    'historical_positive_pct':round(100*sum(x[2]>0 for x in rs)/len(rs),3) if rs else None,
    'historical_mean_pct':round(statistics.mean(x[2] for x in rs),3) if rs else None,
    'forward_eligibility_conclusion':'UNAVAILABLE_NO_POINT_IN_TIME_FINANCIALS'}
print(json.dumps(summary,indent=2))
f=Path('/tmp/v2-preearnings-eventdate-controls-20261116T2030CT.json')
f.write_text(json.dumps(summary,sort_keys=True,indent=2))
print('ISOLATED_ANALYSIS_ARTIFACT',f)
