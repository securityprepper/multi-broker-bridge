"""Pre-earnings as-of pre5 momentum alignment vs subsequent pre5 close return.

READ-ONLY retrospective estimator, not executable trading authorization.
Inputs: frozen retrospectively discovered event pairs and independently pulled
historical SPY split-adjusted SIP daily bar closes.
"""
from __future__ import annotations
import collections,datetime as dt,hashlib,json,math,os,random,stat,statistics,sys
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0,'/opt/securityprepper/owned-overnight-direction')
from owned_direction import batched_bars,market_json

NOW=dt.datetime.now(dt.timezone.utc)
ROOT=Path('/var/lib/securityprepper-earnings-anticipation')
EVENTS=ROOT/'research-20261116-broad-market-pre-earnings-3809.json'
SECTORS=ROOT/'research-20261116-sector-98-last-earnings.json'
DST=Path('/tmp/v2-trading-strategy-research/research/v2_20261117_preearnings_pre5_priortrend_alignment.json')
GATE=Path('/var/cache/securityprepper-holiday/task-gate.json')
CACHE=Path('/etc/securityprepper/alpaca-feed/private')
def check_gate():
 s=GATE.lstat();g=json.loads(GATE.read_text())
 t=lambda k:dt.datetime.fromisoformat(g[k]).astimezone(dt.timezone.utc)
 assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and not(s.st_mode&0o022) and not GATE.is_symlink()
 assert g.get('schema_version')==1 and g.get('status_valid') is True
 assert g.get('timezone')=='America/Chicago' and g.get('calendar_coverage_ok') is True
 assert str(g.get('calendar_revision'))=='2' and g.get('paused') is False
 assert (dt.date.fromisoformat(g['calendar_coverage_through'])>=NOW.date())
 assert dt.timedelta(0)<=NOW-t('published_at')<=dt.timedelta(seconds=150)
 assert NOW<t('valid_until') and NOW<t('next_check_at')
def signal_known_at_minus5(r5,r10,r15):
 """Earlier returns, computed *at* -5 close, no P0 necessary operationally."""
 assert min(1+r5/100,1+r10/100,1+r15/100)>0
 pre5=100*((1+r10/100)/(1+r5/100)-1)
 pre10=100*((1+r15/100)/(1+r5/100)-1)
 return (pre5,pre10)
def pct(a,b):
 assert a>0 and b>0
 return 100*(b/a-1)
def week(d):
 x=dt.date.fromisoformat(d).isocalendar()
 return f'{x.year}-W{x.week:02d}'
def summarise(rows):
 n=len(rows)
 if not n:return {'n':0}
 vals=[r['forward_pct'] for r in rows]
 excess=[r['excess_spy_pct_points'] for r in rows]
 return {'n':n,'up':sum(x>0 for x in vals),'up_fraction':round(sum(x>0 for x in vals)/n,4),
         'mean_forward_close_pct':round(statistics.mean(vals),4),
         'median_forward_close_pct':round(statistics.median(vals),4),
         'mean_excess_spy_close_pp':round(statistics.mean(excess),4),
         'outperform_spy':sum(v>0 for v in excess),
         'outperform_spy_fraction':round(sum(v>0 for v in excess)/n,4),
         'mean_minus_20bps_cost_pct':round(statistics.mean(vals)-0.2,4),
         'mean_excess_minus_20bps_cost_pp':round(statistics.mean(excess)-0.2,4)}
def ci_week(rows,field,seed=202611170030,boot=1300):
 groups=collections.defaultdict(list)
 for x in rows:groups[x['week']].append(x)
 if len(groups)<3:return None
 rng=random.Random(seed)
 cells=list(groups.values())
 vals=[]
 for i in range(boot):
  sampled=[x[field] for sample in rng.choices(cells,k=len(cells)) for x in sample]
  vals.append(statistics.mean(sampled))
 vals.sort()
 return [round(vals[int(.025*(boot-1))],4),round(vals[int(.975*(boot-1))],4)]
def run():
 check_gate()
 E=json.loads(EVENTS.read_text())['pairs']
 S=set(json.loads(SECTORS.read_text())['events'])
 assert len(E)==3809
 assert len({(x['symbol'],x['earnings_date']) for x in E})==3809
 key={name:(CACHE/name).read_text().strip() for name in ('alpaca_data_key_id','alpaca_data_secret')}
 assert all(key.values())
 days,failed=batched_bars(['SPY'],'1Day',dt.datetime(2026,7,1,tzinfo=dt.timezone.utc),
                          dt.datetime(2026,11,17,tzinfo=dt.timezone.utc),'sip',key,market_json)
 assert not failed and 'SPY' in days
 spy={}
 for b in days['SPY']:
  d=dt.datetime.fromisoformat(b['t'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
  v=float(b['c'])
  if v>0 and math.isfinite(v) and int(b.get('v',0))>0:spy[d]=v
 assert len(spy)>=85
 rows=[]
 for p in E:
  dates=(p['prior16_day'],p['prior11_day'],p['prior6_day'],p['last_pre_earnings_close_date'])
  if any(k not in spy for k in dates):continue
  r5,r10,r15=(float(p[f'return{h}_pct']) for h in (5,10,15))
  if not all(math.isfinite(v) for v in (r5,r10,r15)):continue
  stock_pre5,stock_pre10=signal_known_at_minus5(r5,r10,r15)
  spy_pre5=pct(spy[dates[1]],spy[dates[2]])
  spy_pre10=pct(spy[dates[0]],spy[dates[2]])
  spy_forward=pct(spy[dates[2]],spy[dates[3]])
  # Signal is evaluated at -5 trading-day close: only information prior or at that point.
  trend5=stock_pre5>0 and stock_pre5>spy_pre5
  trend10=stock_pre10>0 and stock_pre10>spy_pre10
  label=('BOTH_PRIOR_STRENGTHS' if trend5 and trend10 else
         'NO_PRIOR_STRENGTH' if not trend5 and not trend10 else
         'ONLY_PRIOR_5' if trend5 else 'ONLY_PRIOR_10')
  rows.append({'symbol':p['symbol'],'date':p['earnings_date'],
               'week':week(p['earnings_date']),'marketcap':p.get('market_cap_estimate'),
               'sector98':p['symbol'] in S,'period':('EARLY_AUG_SEP' if p['earnings_date']<'2026-10-01' else 'LATER_OCT_NOV'),
               'pre5_pct':round(stock_pre5,4),'pre10_pct':round(stock_pre10,4),
               'spy_pre5_pct':round(spy_pre5,4),'spy_pre10_pct':round(spy_pre10,4),
               'label':label,'forward_pct':r5,
               'spy_forward_pct':round(spy_forward,4),
               'excess_spy_pct_points':round(r5-spy_forward,4)})
 # Remove repeated symbol/year at analysis level; earliest listed observation was fixed
 # before label calculations; not selected on return or classification.
 primary=[];seen=set()
 for r in sorted(rows,key=lambda x:(x['date'],x['symbol'])):
  k=(r['symbol'],r['date'][:4])
  if k in seen:continue
  seen.add(k);primary.append(r)
 out={}
 for period in ('EARLY_AUG_SEP','LATER_OCT_NOV','ALL'):
  rset=[r for r in primary if period=='ALL' or r['period']==period]
  out[period]={'all':summarise(rset),'week_clusters':len({r['week'] for r in rset}),
               'labels':{label:summarise([r for r in rset if r['label']==label])
                for label in ('BOTH_PRIOR_STRENGTHS','ONLY_PRIOR_5','ONLY_PRIOR_10','NO_PRIOR_STRENGTH')},
               'sector98_aligned':summarise([r for r in rset if r['sector98'] and r['label']=='BOTH_PRIOR_STRENGTHS']),
               'nonsector_aligned':summarise([r for r in rset if not r['sector98'] and r['label']=='BOTH_PRIOR_STRENGTHS'])}
  for label in ('BOTH_PRIOR_STRENGTHS','NO_PRIOR_STRENGTH'):
   sample=[r for r in rset if r['label']==label]
   out[period]['labels'][label]['week_bootstrap_95_mean_excess_spy_pp']=ci_week(sample,'excess_spy_pct_points',seed=202611170030)
 result={'asof_utc':NOW.isoformat(),
  'classification':'EXPLORATORY_RETROSPECTIVE_CLOSE_TO_CLOSE_NO_INDEPENDENT_HOLDOUT_NO_BROKER_FILLS',
  'input_3809_event_pairs':len(E),'complete_spy_date_pairs':len(rows),
  'unique_symbol_year_primary_pairs':len(primary),'duplicate_symbol_year_removed':len(rows)-len(primary),
  'frozen_prior_strength_rule':"At the close five sessions before a calendar-listed release, prior 5-session and 10-session stock returns both positive AND each exceeds SPY over the same completed prior spans; do not use post-entry future price to select.",
  'outcome':'pre5 close -> previous trading-day close, NOT noon exit, bid/ask or fill',
  'analysis_split':'calendar events Aug-Sep vs Oct-Nov, neither an untouched forward holdout',
  'SPY':'paid SIP split-adjusted daily CLOSE, positive volume',
  'estimated_roundtrip_cost_bps_for_sensitivity_only':20,
  'groups':out,
  'original_issuer_earnings_date_verified':False,
  'eps_revision_original_availability_verified':False,
  'post_signal_bid_ask_spread_and_exit_1300_et_known':False,
  'different_independently_validated_holdout_sessions':0,
  'broker_access':'NONE; historical market-data GET only',
  'no_orders':True,'no_live_or_paper_changes':True,
  'source_paths':[str(EVENTS),str(SECTORS)],
  'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (EVENTS,SECTORS)},
  'limitations':['Earnings dates gathered retrospectively and may differ from pre-signal availability',
  'Pre5 pre10 returns reconstructed algebraically from 5/10/15-day END-anchored closes; confirm time ordering in regression',
  'Historic strategy not precommitted before the retrospective outcomes existed, so later chronological split is descriptive',
  'No genuine immutable pre-event issuer calendar, EPS revision, 1m quotes, release-time, noon-before release, fill, fees, protective stop or overnight gap outcomes',
  '20bps is hypothetical transaction friction, not a verified broker execution cost',
  'Symbol-year dedup removes repeated-quarter dependence but remaining ticker and sector correlations persist',
  'Cluster bootstrap uses calendar week only; broad event cohort is survivorship-selected']}
 assert not DST.exists()
 result['raw_record_n_disclosed']=0
 fd=os.open(DST,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 print(json.dumps({'file':str(DST),'primary_n':len(primary),'early':out['EARLY_AUG_SEP'],'later':out['LATER_OCT_NOV'],'no_orders':True},sort_keys=True))
if __name__=='__main__':
 assert signal_known_at_minus5(5.,15.5,28.205)[0]>9.9
 assert abs(signal_known_at_minus5(5.,15.5,28.205)[1]-22.1)<0.05
 run()
