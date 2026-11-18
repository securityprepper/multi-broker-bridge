#!/usr/bin/python3
"""READ-ONLY prospective QW discovery-lead forward checks, 2026-11-18.
No paper or live broker API, no orders, no source modifications.
"""
import os,json,stat,sqlite3,datetime as dt,urllib.request,urllib.parse,collections,statistics,time,hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
UTC=dt.timezone.utc
CT=ZoneInfo("America/Chicago")
now=dt.datetime.now(UTC)
gpath=Path('/var/cache/securityprepper-holiday/task-gate.json')
s=os.lstat(gpath);g=json.loads(gpath.read_text())
when=lambda key:dt.datetime.fromisoformat(g[key].replace('Z','+00:00')).astimezone(UTC)
assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022
assert g.get('schema_version')==1 and g.get('status_valid') is True and g.get('timezone')=='America/Chicago'
assert g.get('calendar_coverage_ok') is True and g.get('calendar_revision') and g.get('paused') is False
assert dt.timedelta(0)<=now-when('published_at')<=dt.timedelta(seconds=150) and now<when('valid_until') and now<when('next_check_at')
assert dt.datetime.fromisoformat(g['calendar_coverage_through']).date()>=now.astimezone(CT).date()
print("VALIDATED_GATE",now.astimezone(CT).isoformat(),flush=True)
date='2026-11-18'
cut=dt.datetime.fromisoformat(date+'T18:00:00+00:00')
last=dt.datetime.fromisoformat(date+'T19:35:00+00:00')
start=dt.datetime.fromisoformat(date+'T14:30:00+00:00')
con=sqlite3.connect("file:/var/lib/securityprepper-quality-watch/state.sqlite3?mode=ro",uri=True)
first={key:{} for key in ('expanded_buy_preflight_candidates','broad_sp500_research_leads','news_preflight_candidates')}
raw=collections.Counter()
for asof,summary in con.execute("SELECT asof,signal_summary FROM scans WHERE asof>=? AND asof<? ORDER BY id",(start.isoformat(),cut.isoformat())):
    obs=dt.datetime.fromisoformat(asof.replace('Z','+00:00'))
    if obs.tzinfo is None:obs=obs.replace(tzinfo=UTC)
    d=json.loads(summary)
    raw['scans']+=1
    for key in first:
        for event in d.get(key,[]):
            symbol=event.get('symbol')
            if not isinstance(symbol,str) or not symbol.isascii() or not symbol.replace('.','').isalpha() or len(symbol)>8:continue
            raw[key+'_events']+=1
            et=event.get('asof_utc') or event.get('observed_at_utc')
            try: event_time=dt.datetime.fromisoformat(et.replace('Z','+00:00'))
            except Exception:continue
            if event_time.tzinfo is None:continue
            if not dt.timedelta(0)<=obs-event_time<=dt.timedelta(minutes=4):continue
            if symbol not in first[key]:
                first[key][symbol]={'observed':obs,'signal_source':event_time,
                    'evidence_score':event.get('score'),'signal_p5':event.get('p5'),
                    'news':event.get('news_clearance',event.get('qualified_issuer_news'))}
con.close()
symbols=set.union(*(set(s) for s in first.values()))|{'SPY'}
print('DISCOVERY_UNIVERSE',len(symbols),'PER_SOURCE',{k:len(v) for k,v in first.items()},flush=True)
# Pure, authenticated historical Alpaca DATA GET (not paper orders).
base=Path('/etc/securityprepper/alpaca-feed/private')
key=(base/'alpaca_data_key_id').read_text().strip();secret=(base/'alpaca_data_secret').read_text().strip()
assert key and secret
headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret,'Accept':'application/json'}
hist={}
failure=[]
syms=sorted(symbols)
for j in range(0,len(syms),16):
    group=syms[j:j+16]
    token=None
    loops=0
    try:
        while True:
            loops+=1
            if loops>15:raise RuntimeError('PAGINATION_LIMIT')
            params={'symbols':','.join(group),'timeframe':'1Min','start':start.isoformat(),
                'end':last.isoformat(),'feed':'sip','adjustment':'split','limit':10000}
            if token:params['page_token']=token
            url='https://data.alpaca.markets/v2/stocks/bars?'+urllib.parse.urlencode(params)
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers,method='GET'),timeout=12) as response:
                if response.status!=200:raise ValueError('HTTP_STATUS_'+str(response.status))
                payload=response.read(8000000)
            if len(payload)>=8000000:raise RuntimeError('TRUNCATED_BATCH')
            data=json.loads(payload)
            if not isinstance(data,dict) or not isinstance(data.get('bars'),dict):raise ValueError('BAD_SIP_DATA')
            for sym,rows in data['bars'].items():
                hist.setdefault(sym,[]).extend(rows)
            token=data.get('next_page_token')
            if not token:break
    except Exception as e:
        failure.append({'batch_index':j//16,'symbol_count':len(group),'error_type':type(e).__name__,'details':str(e)[:85]})
    if (j//16)%3==0:print('DATA_GROUPS',j//16+1,'of',(len(syms)+15)//16,'page_reads',loops,flush=True)
# dedup timestamps; reject any result with no observed bars
series={}
for sym,rows in hist.items():
    out={}
    for b in rows:
        try:
            t=dt.datetime.fromisoformat(b['t'].replace('Z','+00:00'))
            if t.tzinfo is None:t=t.replace(tzinfo=UTC)
            prices=tuple(float(b[x]) for x in ('o','h','l','c'))
            if not (start<=t<last and min(prices)>0 and b.get('v',0)>0 and prices[2]<=prices[0]<=prices[1] and prices[2]<=prices[3]<=prices[1]):continue
            out[t]=dict(t=t,o=prices[0],h=prices[1],l=prices[2],c=prices[3])
        except Exception:continue
    series[sym]=[out[t] for t in sorted(out)]
print('HISTORICAL_BAR_COVERAGE',len(series),'failures',len(failure),flush=True)
# Align to strict AFTER observed scan time, never use a not-yet-completed bar.
def follow(sym,observed,horizon):
    rows=series.get(sym,[])
    target_start=observed.replace(second=0,microsecond=0)+dt.timedelta(minutes=1)
    idx=next((i for i,r in enumerate(rows) if r['t']>=target_start),None)
    if idx is None:return None
    entry=rows[idx]
    if (entry['t']-target_start).total_seconds()>90:return None
    to=entry['t']+dt.timedelta(minutes=horizon)
    realized=[r for r in rows[idx:] if r['t']>=entry['t'] and r['t']+dt.timedelta(minutes=1)<=to]
    if len(realized)<horizon-2 or not realized or (to-(realized[-1]['t']+dt.timedelta(minutes=1))).total_seconds()>90:return None
    # The entry is a next-minute bar OPEN proxy, not a proven executable ask.
    ret=(realized[-1]['c']/entry['o']-1)*100
    return {'ret_pct':ret,'entry_proxy':entry['o'],'entry_time_utc':entry['t'].isoformat(),
        'last_close_time_utc':(realized[-1]['t']+dt.timedelta(minutes=1)).isoformat(),
        'covered_bars':len(realized),'minimum_pct':(min(x['l'] for x in realized)/entry['o']-1)*100,
        'maximum_pct':(max(x['h'] for x in realized)/entry['o']-1)*100}
outcomes={}
stats={}
for key,signals in first.items():
    samples=[]
    reasons=collections.Counter()
    for symbol,e in signals.items():
        sample={'symbol':symbol,'observed_at_utc':e['observed'].isoformat(),
            'original_bar_availability_utc':e['signal_source'].isoformat(),
            'news_status':e['news']}
        for horizon in (15,60):
            result=follow(symbol,e['observed'],horizon)
            spy=follow('SPY',e['observed'],horizon)
            if result:
                sample[str(horizon)+'m']=result
                if spy:sample[str(horizon)+'m_excess_vs_spy_pct']=result['ret_pct']-spy['ret_pct']
            else:reasons['missing_'+str(horizon)+'m']+=1
        samples.append(sample)
    outcomes[key]=samples
    scored60=[x for x in samples if x.get('60m')]
    scored15=[x for x in samples if x.get('15m')]
    def compact(xs,key):
        vals=[x[key]['ret_pct'] for x in xs]
        return {'n':len(vals),'up_n':sum(x>0 for x in vals),
                'mean_close_only_pct':round(statistics.mean(vals),4) if vals else None,
                'median_close_only_pct':round(statistics.median(vals),4) if vals else None,
                'mean_020pct_cost_proxy_pct':round(statistics.mean(vals)-0.2,4) if vals else None,
                'positive_after_020pct_cost_proxy_n':sum(x>0.2 for x in vals)}
    stats[key]={'candidate_symbols':len(signals),
      'horizon15':compact(scored15,'15m'),'horizon60':compact(scored60,'60m'),
      'missing_counts':dict(reasons),
      'news_clear_asof_count':sum(e['news']=='NEWS_CLEAR_ASOF' for e in signals.values())}
# Look at where the full-day biggest winners actually appeared early, not assumed executable.
snapshot=json.load(open('/var/lib/securityprepper-broad-market/sp500_latest.json'))
gainers=[]
for e in snapshot.get('top_gainers',[])[:12]:
    sym=e['symbol']
    entry={'symbol':sym,'current_rth_vs_previous_close_pct':e['rth_change_pct'],'observed_in_live_scan':{
          key:sym in signals for key,signals in first.items()}}
    for key,signals in first.items():
        if sym in signals:
            entry[key+'_first_observed_at_utc']=signals[sym]['observed'].isoformat()
            val=follow(sym,signals[sym]['observed'],60)
            if val:entry[key+'_forward_60m_close_proxy_pct']=round(val['ret_pct'],3)
            prev=e['previous_completed_rth_close']
            if val and prev:entry[key+'_prior_close_to_entry_proxy_pct']=round((val['entry_proxy']/prev-1)*100,3)
    gainers.append(entry)
report={'type':'QW_PRICE_ONLY_PROSPECTIVE_FORWARD_HORIZONS',
 'sample_date_chicago':date,'run_time_utc':dt.datetime.now(UTC).isoformat(),
 'broker_order_permission':False,'broker_orders_submitted':0,
 'universe_size_unique':len(symbols)-1,'holiday_revision_verified':g['calendar_revision'],
 'scan_cutoff_utc':cut.isoformat(),'bars_must_be_completed_by_utc':last.isoformat(),
 'first_scan_appearance_is_not_first_news_observation':True,
 'historical_price_is_not_executable_ask_bid':True,
 'assumed_cost_020pct_is_only_sensitivity_not_actual_after_fee':True,
 'strict_no_lookahead':True,'summary':stats,'top_rth_winners_early_discovery':gainers,
 'data_batch_errors':failure,'all_outcomes':outcomes}
out=Path('/tmp/trading_strategy_research_20261118T1334')
out.mkdir(mode=0o700,exist_ok=True)
outfile=out/'quality_watch_early_leads_20261118_asof.json'
outfile.write_text(json.dumps(report,default=str,sort_keys=True,indent=2))
os.chmod(outfile,0o600)
print('RESULT_SUMMARY',json.dumps(stats),flush=True)
print('WINNERS_EARLY',json.dumps(gainers[:8]),flush=True)
print('REPORT_PATH',outfile,'REPORT_SHA256',hashlib.sha256(outfile.read_bytes()).hexdigest(),flush=True)
