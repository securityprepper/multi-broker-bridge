"""Fixed, pre-existing individual weakness rule; retrospective diagnostic only.
Papers, stops, scheduled services, alerts and broker endpoints are untouched.
"""
from __future__ import annotations
import datetime as dt,os,stat,json,sys
from pathlib import Path
from zoneinfo import ZoneInfo
from collections import defaultdict
from statistics import mean

CT=ZoneInfo("America/Chicago"); ET=ZoneInfo("America/New_York"); UTC=dt.timezone.utc
OUT=Path('/tmp/v2-trading-strategy-research/research/v2_20261116_downside_10session_anchor_diagnostic_v3.json')
def main():
    sys.path.insert(0,'/opt/securityprepper/sector-monitor')
    from holiday_gate import validate_fresh
    p=Path('/var/cache/securityprepper-holiday/task-gate.json');st=p.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022
    g=json.loads(p.read_text());now=dt.datetime.now(UTC)
    assert g.get('status_valid') is True and g.get('timezone')=='America/Chicago' and str(g.get('calendar_revision'))=='2'
    assert not validate_fresh(g,now)['paused']
    pub=dt.datetime.fromisoformat(g['published_at']).astimezone(UTC)
    assert dt.timedelta(0)<=now-pub<=dt.timedelta(seconds=150)
    sys.path[0:0]=['/opt/securityprepper/owned-overnight-direction','/opt/securityprepper/quality-opportunity-watch']
    from owned_direction import batched_bars
    from quality_watch import SECTORS
    selected={'Semiconductors':'SOXX','Gold miners':'GDX','Energy':'XLE','Financials':'XLF','Industrials':'XLI','Healthcare':'XLV','Software':'IGV'}
    symbols=set(selected.values())
    group={}
    for name,etf in selected.items():
        anchors=('CRM','NOW','ADBE') if name=='Software' else SECTORS.get(name,(None,(),()))[2]
        symbols.update(anchors)
        for s in anchors:group[s]=name
        group[etf]=name
    symbols=sorted(symbols)
    credentials={n:Path('/etc/securityprepper/alpaca-feed/private/'+n).read_text().strip()
                 for n in ('alpaca_data_key_id','alpaca_data_secret')}
    daily,daily_failed=batched_bars(symbols,'1Day',dt.datetime(2026,10,27,tzinfo=UTC),
                    dt.datetime(2026,11,17,tzinfo=UTC),'sip',credentials)
    closes={}
    for s,items in daily.items():
        closes[s]={}
        for row in items:
            stamp=dt.datetime.fromisoformat(row['t'].replace('Z','+00:00')).astimezone(ET)
            if float(row.get('c') or 0)>0 and float(row.get('v') or 0)>0:
                closes[s][stamp.date()]=float(row['c'])
    # Anchor ET days are independently observed completed daily market records.
    candidates=sorted(set.intersection(*(set(closes[s]) for s in selected.values())))
    sessions=[d for d in candidates if dt.date(2026,11,3)<=d<=dt.date(2026,11,16)]
    events=[];coverage=[];missing=[];completed=[]
    assert len(sessions)==10, ('SESSION_COVERAGE_UNEXPECTED',len(sessions))
    for day in sessions:
        preceding=[d for d in candidates if d<day]
        if not preceding:continue
        prev=preceding[-1]
        opening=dt.datetime.combine(day,dt.time(9,30),tzinfo=ET)
        finish=dt.datetime.combine(day,dt.time(16,0),tzinfo=ET)
        minutes,failed=batched_bars(symbols,'1Min',opening,finish,'sip',credentials)
        had=0
        for sym in symbols:
            if day not in closes.get(sym,{}) or prev not in closes.get(sym,{}):
                missing.append((str(day),sym,'MISSING_BROKER_INDEPENDENT_BASELINE'));continue
            base=closes[sym][prev]
            pts={}
            for rec in minutes.get(sym,[]):
                try:
                    t=dt.datetime.fromisoformat(rec['t'].replace('Z','+00:00')).astimezone(ET)
                    if opening<=t<finish and int(rec['v'])>0 and float(rec['c'])>0:
                        pts[t]=float(rec['c'])
                except (ValueError,TypeError,KeyError):pass
            if not pts:missing.append((str(day),sym,'NO_MINUTE_BARS'));continue
            completed.append((str(day),sym,len(pts)))
            trigger_candidates=[]
            for stamp in sorted(pts):
                older=pts.get(stamp-dt.timedelta(minutes=15))
                if older is None:continue
                change=100*(pts[stamp]/base-1)
                drop15pp=100*(pts[stamp]-older)/base
                if change<=-2.5 and drop15pp<=-1.0:
                    trigger_candidates.append((stamp,pts[stamp],change,drop15pp))
            if not trigger_candidates:continue
            t,mark,chg,delta=trigger_candidates[0]
            def future(m):
                k=pts.get(t+dt.timedelta(minutes=m))
                return round(100*(k/mark-1),4) if k else None
            out15=future(15);out60=future(60)
            events.append({'day':str(day),'symbol':sym,'sector':group[sym],
                          'prior_rth_close_day':str(prev),'signal_first_completed_bar_ET':(t+dt.timedelta(minutes=1)).isoformat(),
                          'total_from_prior_pct':round(chg,4),'last_15minute_pp':round(delta,4),
                          'close_15m_future_pct':out15,'close_60m_future_pct':out60,
                          'future_bid_ask_not_available':True,'broker_orders':0,
                          'mark_is_trade_close_not_live_available_at':True,
                          'eligible_before_1315CT':(t+dt.timedelta(minutes=1)).time()<dt.time(14,15)})
            had+=1
        coverage.append({'day':str(day),'symbol_universe':len(symbols),
                         'minute_bars_returned_symbols':len(minutes),
                         'provider_failed_symbols':len(failed),'first_watch_symbols':had})
        print('COMPLETED_DAY',day,'watched',had,'provider_failed',len(failed),flush=True)
    valid15=[x for x in events if x['close_15m_future_pct'] is not None]
    valid60=[x for x in events if x['close_60m_future_pct'] is not None]
    by_day={}
    for d in sorted(set(x['day'] for x in events)):
        cases=[x for x in events if x['day']==d]
        check15=[x for x in cases if x['close_15m_future_pct'] is not None]
        check60=[x for x in cases if x['close_60m_future_pct'] is not None]
        by_day[d]={'signals':len(cases),'15m_scored':len(check15),
                   '15m_future_drop':sum(x['close_15m_future_pct']<0 for x in check15),
                   '60m_scored':len(check60),
                   '60m_future_drop':sum(x['close_60m_future_pct']<0 for x in check60)}
    output={'asof':now.isoformat(),'lookback':'10 completed sessions ending Nov16; RETROSPECTIVE, not genuine untouched holdout',
        'fixed_rule':'total <= -2.5pct since prior RTH close and delta <= -1.0pp over preceding completed 15min (overlapping)',
        'news_first_seen_verified':False,'executable_spreads_or_fills_available':False,
        'universe_symbols':symbols,'provider_daily_failed':daily_failed,'session_coverage':coverage,
        'missing_data':missing,'event_count':len(events),'unique_days_with_events':len(by_day),
        '15m_scored':len(valid15),'15m_future_down':sum(x['close_15m_future_pct']<0 for x in valid15),
        '60m_scored':len(valid60),'60m_future_down':sum(x['close_60m_future_pct']<0 for x in valid60),
        'by_day':by_day,'all_events':events,
        'broker_posts':0,'notice_sent':0,'notes':'Historical completed SIP trade closes; no quote/spread fees; related ETF/peer events highly correlated; one historical day does not count as independent trades; next-open labels unavailable.'}
    fd=os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(output,f,indent=2,sort_keys=True);f.write('\n')
    print('FIXED_RULE_COHORT',len(events),len(by_day),'15m',len(valid15),output['15m_future_down'],'60m',len(valid60),output['60m_future_down'])
    print('NO_ORDER_ACTIONS',OUT)
if __name__=='__main__':main()
