"""V2 isolated read-only multi-sector two-sided as-of 5m research census.
No news-clearance inference, order, broker account POST or production changes.
Returns descriptive after-signal prices, NOT executable after-fee edge.
"""
from __future__ import annotations
import datetime as dt,stat,json,os,collections,math
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import direction_paper as dp
UTC=dt.timezone.utc
CT=ZoneInfo('America/Chicago')
GATE=Path('/var/cache/securityprepper-holiday/task-gate.json')
gate=json.loads(GATE.read_text());st=os.lstat(GATE);now=dt.datetime.now(UTC)
timestamp=lambda k:dt.datetime.fromisoformat(gate[k].replace('Z','+00:00')).astimezone(UTC)
assert (st.st_uid==0 and stat.S_ISREG(st.st_mode) and not st.st_mode&0o022
        and gate.get('status_valid') is True and gate.get('schema_version')==1
        and gate.get('timezone')=='America/Chicago' and gate.get('calendar_coverage_ok') is True
        and bool(gate.get('calendar_revision')) and gate.get('calendar_coverage_through','') >= now.astimezone(CT).date().isoformat() and gate.get('paused') is False and dt.timedelta(0)<=now-timestamp('published_at')<=dt.timedelta(seconds=150)
        and now<timestamp('valid_until') and now<timestamp('next_check_at')),'HOLIDAY_NOT_VERIFIED'
SECTORS={'SOXX':['NVDA','AMD','MU'],
'GDX':['NEM','AEM','WPM'],
'XLE':['XOM','CVX','COP'],
'XLF':['JPM','BAC','GS'],
'XLI':['CAT','GE','ETN'],
'XLV':['UNH','JNJ','LLY'],
'IGV':['MSFT','CRM','PANW']}
DAY_LIMIT={'SOXX':5,'GDX':5,'XLE':3,'XLF':3,'XLI':3,'XLV':3,'IGV':4}
SYMBOLS=list(dict.fromkeys([s for etf,peers in SECTORS.items() for s in [etf]+peers]))
headers=dp.market_headers()
rows={}
for date in ('2026-11-17','2026-11-18','2026-11-19'):
    url='https://data.alpaca.markets/v2/stocks/bars?'+urlencode({
      'symbols':','.join(SYMBOLS),'timeframe':'5Min',
      'start':date+'T14:30:00Z','end':date+'T21:00:00Z',
      'feed':'sip','adjustment':'split','limit':10000})
    bars_by_symbol={}
    page_token=None
    seen_tokens=set()
    for page_no in range(10):
        endpoint=url+('&'+urlencode({'page_token':page_token}) if page_token else '')
        d=dp._fetch_json(endpoint,headers=headers)
        if not isinstance(d.get('bars'),dict):
            raise ValueError('VENDOR_BARS_NOT_OBJECT')
        for symbol,items in d['bars'].items():
            bars_by_symbol.setdefault(symbol,[]).extend(items)
        page_token=d.get('next_page_token')
        if not page_token:break
        if page_token in seen_tokens:raise ValueError('PAGINATION_CYCLE')
        seen_tokens.add(page_token)
    else:raise ValueError('VENDOR_BARS_PAGE_LIMIT')
    day={}
    for symbol in SYMBOLS:
        ls=bars_by_symbol.get(symbol,[])
        r={}
        for bar in ls:
            z=dt.datetime.fromisoformat(bar['t'].replace('Z','+00:00'))
            end=z+dt.timedelta(minutes=5)
            local=end.astimezone(CT)
            if local.date().isoformat()!=date or not (dt.time(8,35)<=local.time()<=dt.time(15,0)):
                continue
            if (not isinstance(bar.get('c'),(int,float)) or bar['c']<=0
                    or not isinstance(bar.get('o'),(int,float)) or bar['o']<=0
                    or not isinstance(bar.get('v'),(int,float)) or bar['v']<=0):
                continue
            r[end.isoformat()]=bar
        # Need full 78 RTH 5-minute completions; gaps make symbol unavailable.
        if len(r)!=78:
            day[symbol]=None
        else: day[symbol]=dict(sorted(r.items()))
    rows[date]=day

def forward(s,date,stamp,future_mins):
    d=rows[date].get(s)
    if not d:return None
    end=dt.datetime.fromisoformat(stamp)+dt.timedelta(minutes=future_mins)
    x=d.get(end.isoformat())
    return x['c'] if x else None

threshold_events=[];weakness_events=[];market_day_summary=[]
for date in ('2026-11-18','2026-11-19'):
    d=rows[date];ydate=(dt.date.fromisoformat(date)-dt.timedelta(days=1)).isoformat()
    daily={'date':date,'symbols_full_78_bars':sum(v is not None for v in d.values()),
           'raw_etf_2close_extremes':0,'peer_confirmed_etf_extremes':0,
           'stock_weakness_signals':0}
    for etf,peers in SECTORS.items():
        bars=d.get(etf)
        if not bars:continue
        l=list(bars.items())
        open_price=l[0][1]['o']
        for i in range(1,len(l)):
            a=l[i-1][1]['c'];b=l[i][1]['c']
            ea=(a/open_price-1)*100
            eb=(b/open_price-1)*100
            up=ea>=DAY_LIMIT[etf] and eb>=DAY_LIMIT[etf]
            down=ea<=-DAY_LIMIT[etf] and eb<=-DAY_LIMIT[etf]
            if not(up or down):continue
            sign=1 if up else -1
            # Only first crossing of each direction per ETF/day, not repeated alarms.
            already=any(x['date']==date and x['sector']==etf and x['direction']==('UP' if sign>0 else 'DOWN') for x in threshold_events)
            if already:continue
            stamp=l[i][0]
            tally=0;peer_available=0
            for peer in peers:
                p=d.get(peer)
                if not p:continue
                peer_available+=1
                peer_open=list(p.values())[0]['o']
                pm=p[stamp]['c']
                if ((pm/peer_open-1)*100)*sign>0:tally+=1
            qualifying=peer_available==3 and tally>=2
            future={}
            for horizon in (15,60):
                price=forward(etf,date,stamp,horizon)
                future[str(horizon)+'m_price_delta_pct']=round((price/b-1)*100,3) if price is not None else None
            threshold_events.append({'date':date,'sector':etf,'direction':'UP' if sign>0 else 'DOWN',
                'signal_available_utc':stamp,'threshold_pct':DAY_LIMIT[etf],
                'signal_close_pct_from_open':round(eb,3),
                'peers_same_direction':tally,'peer_available':peer_available,
                'peer_2of3_confirmed':qualifying,'after_signal':future})
            daily['raw_etf_2close_extremes']+=1
            if qualifying:daily['peer_confirmed_etf_extremes']+=1
    prior=rows.get(ydate,{})
    for sym in SYMBOLS:
        bb=d.get(sym);p=prior.get(sym)
        if not bb or not p:continue
        prev_close=list(p.values())[-1]['c']
        ls=list(bb.items())
        earliest=None
        for i in range(3,len(ls)):
            stamp=ls[i][0]
            # owner permits alerts prior to 13:15 new entry; retain late observations but no buys
            end=dt.datetime.fromisoformat(stamp).astimezone(CT)
            current=ls[i][1]['c'];ago=ls[i-3][1]['c']
            change_since_close=(current/prev_close-1)*100
            decline_15=(current-ago)/prev_close*100
            if change_since_close<=-2.5 and decline_15<=-1:
                earliest=(i,stamp,current,change_since_close,decline_15);break
        if earliest:
            i,stamp,current,total,recent=earliest
            future={}
            for horizon in (15,60):
                p=forward(sym,date,stamp,horizon)
                future[str(horizon)+'m_pct']=round((p/current-1)*100,3) if p is not None else None
            end=dt.datetime.fromisoformat(stamp).astimezone(CT)
            weakness_events.append({'date':date,'symbol':sym,'asof_utc':stamp,
                'signal_before_1315_ct':end.time()<dt.time(13,15),
                'prior_regular_close_decline_pct':round(total,3),'last_15m_decline_pp':round(recent,3),
                'future_after_signal':future})
            daily['stock_weakness_signals']+=1
    market_day_summary.append(daily)

def ratio(events,direction,field):
    eligible=[e for e in events if e.get('direction')==direction and e['after_signal'].get(field) is not None]
    success=sum((e['after_signal'][field] or 0)*(1 if direction=='UP' else -1)>0 for e in eligible)
    return {'success':success,'eligible':len(eligible)}
summary={
  'asof_utc':now.isoformat(),'study_days':['2026-11-18','2026-11-19'],
  'source':'licensed Alpaca SIP completed 5Min bars, full RTH 78 bars per observed symbol',
  'universe_sector_etfs':list(SECTORS),'peer_names':len(SYMBOLS)-len(SECTORS),
  'daily_summary':market_day_summary,'extreme_events':threshold_events,
  'weakness_2p5_total_and_1pp_last15_events':weakness_events,
  'after_signal_directional_accuracy_15m_up':ratio(threshold_events,'UP','15m_price_delta_pct'),
  'after_signal_directional_accuracy_15m_down':ratio(threshold_events,'DOWN','15m_price_delta_pct'),
  'after_signal_directional_accuracy_60m_up':ratio(threshold_events,'UP','60m_price_delta_pct'),
  'after_signal_directional_accuracy_60m_down':ratio(threshold_events,'DOWN','60m_price_delta_pct'),
  'news_clear_asof_verified':False,'quotes_and_spreads_validated':False,
  'broker_after_fee_trades':0,'independent_holdout_days':0,
  'research_only':True,'not_actionable':True,
  'method_notes':'Each 5m bar available only at completed end; earliest two-ETF 5m close shock/side/day, independent 2of3 peers. 15m and 60m future closes are NOT executable fills. No after-fee claim; 2 days are insufficient holdout.'}
out=Path('/tmp/v2-trading-strategy-research/research/v2_20261120_0130_sector_two_sided_forward_census.json')
assert not out.exists(),'NO_OVERWRITE'
fd=os.open(out,os.O_CREAT|os.O_WRONLY|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:json.dump(summary,f,indent=2,sort_keys=True)
print(json.dumps({k:summary[k] for k in (
 'daily_summary','after_signal_directional_accuracy_15m_up','after_signal_directional_accuracy_15m_down',
 'after_signal_directional_accuracy_60m_up','after_signal_directional_accuracy_60m_down')},sort_keys=True))
print('SECTOR_EVENTS',[(e['date'],e['sector'],e['direction'],e['peer_2of3_confirmed'],e['signal_close_pct_from_open']) for e in threshold_events])
print('WEAKNESS_EVENTS',[(e['date'],e['symbol'],e['signal_before_1315_ct'],e['future_after_signal']) for e in weakness_events])
print('ISOLATED_RESULT',out)
