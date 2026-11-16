"""Read-only comprehensive issuer news screening for the owner-followed universe.

This is NOT the PAPER order executor and NEVER clears missing source coverage.
It prioritizes latest MBB/quality BUY_WATCH, then rotates all owner-followed
stock tickers. A fully authenticated issuer+SEC+licensed source bundle may be
written to the existing separate trusted publisher. Missing issuer RSS cannot
become NEWS_CLEAR_ASOF: its SEC/news checks are diagnostic review ONLY.
"""
from __future__ import annotations
import argparse,datetime as dt,hashlib,json,os,re,sqlite3,subprocess,time,stat,pwd
from pathlib import Path
from zoneinfo import ZoneInfo
from recommendation_paper_bridge.news_source_collector import (
    ISSUER_RSS, BASELINE_SYMBOLS, CIK_MAP, HOLIDAY_GATE, OUTPUT,
    sec_snapshot, news_pages, source_manifest, SourceUnknown,
)
from recommendation_paper_bridge.news_clearance_publisher import (
    safe_read,owner_protected,atomic_write,holiday_allows,when,EvidenceBlocked
)
from recommendation_paper_bridge.news_eligibility import yesterday_today_start

UNIVERSE=Path('/etc/securityprepper/recommendation-paper-bridge/normal-followed-universe.json')
STATUS=Path('/var/lib/securityprepper-news-universe-screener/status.json')
LEDGER=Path('/var/lib/securityprepper-news-universe-screener/coverage.json')
QUALITY=Path('/var/lib/securityprepper-quality-watch/state.sqlite3')
MBB_SERVICE='trading-sector-paper-executor.service'
MAX_BATCH=40
MAX_RUNTIME=19.0
MAX_JOURNAL=400_000
VALID_SYMBOL=re.compile(r'[A-Z][A-Z0-9.]{0,11}\Z')
UTC=dt.timezone.utc

class ScreeningBlocked(ValueError):pass

def universe_read(path=UNIVERSE):
    try:doc=safe_read(path)
    except (OSError,ValueError,TypeError,EvidenceBlocked) as exc:
        raise ScreeningBlocked('UNIVERSE_REFERENCE_NOT_TRUSTED') from exc
    if (not isinstance(doc,dict) or doc.get('schema_version')!=1 or
        doc.get('universe_name')!='SECURITYPREPPER_NORMAL_FOLLOWED_STOCKS'):
        raise ScreeningBlocked('UNIVERSE_SCHEMA_UNVERIFIED')
    values=doc.get('symbols')
    if (not isinstance(values,list) or not 50<=len(values)<=800 or
        any(not isinstance(s,str) or not VALID_SYMBOL.fullmatch(s) for s in values)
        or len(values)!=len(set(values)) or values!=sorted(values)):
        raise ScreeningBlocked('UNIVERSE_TICKER_SET_INVALID')
    excluded=doc.get('not_company_news_eligible_etf_references')
    if not isinstance(excluded,list) or set(values)&set(excluded):
        raise ScreeningBlocked('ETF_AS_ISSUER_REFERENCE_BLOCKED')
    retired=doc.get('retired_symbol_successors')
    if not isinstance(retired,dict) or set(values)&set(retired):
        raise ScreeningBlocked('RETIRED_SYMBOL_AS_ACTIVE_ISSUER')
    return values

def _uniq(items):return list(dict.fromkeys(items))

def _clean(seq,valid):
    return _uniq(x for x in seq if isinstance(x,str)
        and VALID_SYMBOL.fullmatch(x) and x in valid)

def recent_quality(now,db=QUALITY):
    """Only previous complete latest quality scan, no broker/API calls."""
    try:
        with sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True,timeout=2) as conn:
            row=conn.execute('SELECT asof,signal_summary FROM scans ORDER BY id DESC LIMIT 1').fetchone()
        if not row:return []
        at=when(row[0])
        if not dt.timedelta(0)<=now-at<=dt.timedelta(minutes=3):return []
        doc=json.loads(row[1]);out=[]
        if not isinstance(doc,dict):return []
        for sym in doc.get('shortlist',[]):out.append(sym)
        for item in doc.get('qualified',[]):
            if isinstance(item,dict):out.append(item.get('symbol'))
        return out
    except (OSError,ValueError,TypeError,sqlite3.Error,KeyError):return []

def recent_mbb(now,runner=subprocess.run):
    """Completed timestamped journal records as demand hints, NEVER clearance."""
    cmd=['/usr/bin/journalctl','--quiet','--no-pager','-o','json','-u',MBB_SERVICE,
         '--since',(now-dt.timedelta(minutes=3)).isoformat(),
         '--until',now.isoformat(),'-n','80']
    try:proc=runner(cmd,capture_output=True,text=True,timeout=2)
    except (OSError,subprocess.SubprocessError):return []
    if proc.returncode!=0 or not isinstance(proc.stdout,str) or len(proc.stdout)>MAX_JOURNAL:
        return []
    events=[]
    for line in proc.stdout.splitlines():
        if len(line)>100000:continue
        try:
            outer=json.loads(line)
            when_utc=dt.datetime.fromtimestamp(int(outer['__REALTIME_TIMESTAMP'])/1e6,UTC)
            obj=json.loads(outer['MESSAGE'])
        except (KeyError,TypeError,ValueError,OverflowError,UnicodeError):continue
        if (not dt.timedelta(0)<=now-when_utc<=dt.timedelta(minutes=3)
            or not isinstance(obj,dict) or obj.get('status')!='SCAN_COMPLETE'):
            continue
        syms=obj.get('buy_watch_symbols',[])
        if isinstance(syms,list) and len(syms)<=300:
            events.append((when_utc,syms))
    events.sort(key=lambda row:row[0],reverse=True)
    return _uniq(sym for _,syms in events for sym in syms)

def rotating(items,count,now):
    """Deterministic rotation; every ordinary name eventually receives a check."""
    if not items or count<=0:return []
    # 16 new slots per minute; 286 symbols -> ~18 minutes when active.
    minute=int(now.timestamp())//60
    start=(minute*count)%len(items)
    return [items[(start+i)%len(items)] for i in range(min(count,len(items)))]

def candidates(now,universe,ids,mbb=None,quality=None,baseline=BASELINE_SYMBOLS):
    """Prioritize up to 24 live-signal names; reserve >=16 slots for watchlist.

    New market-discovered tickers are allowed only when independently mapped
    to a SEC identity; they remain NEWS_UNKNOWN without issuer/feed evidence.
    """
    valid=set(universe)|set(ids)
    observed_mbb=_clean(recent_mbb(now) if mbb is None else mbb,valid)
    observed_quality=_clean(recent_quality(now) if quality is None else quality,valid)
    # Rotating priority groups avoids starving a 40-name simultaneous signal.
    head=rotating(observed_mbb,14,now)
    second=rotating([s for s in observed_quality if s not in head],6,now)
    priority=_uniq(head+second+_clean(baseline,valid))[:24]
    tail=rotating([s for s in universe if s not in priority],MAX_BATCH-len(priority),now)
    return _uniq(priority+tail)[:MAX_BATCH]

def partial_screen(symbol,cik,now,clock):
    """For symbols without allowlisted issuer-owned RSS, two-source REVIEW ONLY.

    Never put these records into the publisher's source directory; neither
    SEC-only nor licensed-news-only can independently clear a PAPER buy.
    """
    cutoff=yesterday_today_start(now)
    result={'status':'NEWS_UNKNOWN_OFFICIAL_ISSUER_RSS_UNVERIFIED',
            'sec_identity':'UNKNOWN','licensed_news':'UNKNOWN',
            'in_window_event_count':None,'buy_clearance_eligible':False}
    try:
        sec=sec_snapshot(symbol,cik,cutoff,now,clock)
        result['sec_identity']='VERIFIED'
        result['exchange']=sec['exchange']
        result['sec_in_window_events']=len(sec['events'])
    except (SourceUnknown,ValueError,TypeError,KeyError,OSError) as exc:
        result['sec_identity']=getattr(exc,'reason',type(exc).__name__)
        return result
    try:
        licensed=news_pages(symbol,cutoff,now,clock,issuer_name=sec['name'])
        result['licensed_news']='COMPLETE_ORIGINAL_RECEIPT'
        result['in_window_event_count']=len(licensed['events'])+len(sec['events'])
        result['review_events']=sum(e.get('status')=='review_needed'
            for e in licensed['events'])+len(sec['events'])
        if result['review_events']:
            result['status']='REVIEW_WATCH_ONLY_MISSING_ISSUER_SOURCE'
    except (SourceUnknown,ValueError,TypeError,KeyError,OSError) as exc:
        result['licensed_news']=getattr(exc,'reason',type(exc).__name__)
    return result

def load_sec_ticker_directory(path=CIK_MAP):
    """Read the already commissioned alpacafeed-owned reference securely.

    Ownership need not be root: the publisher does NOT trust this directory
    for clearance. Every symbol+CIK+exchange is rechecked against the original
    independently fetched SEC issuer submission by sec_snapshot().
    """
    allowed_uid=pwd.getpwnam('alpacafeed').pw_uid
    parent=path.parent.lstat()
    st=path.lstat()
    if (path.is_symlink() or not stat.S_ISDIR(parent.st_mode) or
        not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or
        parent.st_uid!=allowed_uid or st.st_uid!=allowed_uid or
        parent.st_mode&0o022 or st.st_mode&0o022 or
        st.st_size<30 or st.st_size>3_000_000):
        raise ScreeningBlocked('UNTRUSTED_SEC_DIRECTORY_REFERENCE')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        if os.fstat(fd).st_ino!=st.st_ino:
            raise ScreeningBlocked('SEC_DIRECTORY_REFERENCE_CHANGED')
        raw=os.read(fd,3_000_001)
    finally:os.close(fd)
    try:
        doc=json.loads(raw)
        ids=doc['symbols']
    except (TypeError,ValueError,KeyError) as exc:
        raise ScreeningBlocked('SEC_DIRECTORY_REFERENCE_BAD_FORMAT') from exc
    if not isinstance(ids,dict) or len(ids)<50:
        raise ScreeningBlocked('SEC_DIRECTORY_REFERENCE_INCOMPLETE')
    return ids

def load_prior_ledger(path=LEDGER):
    try:
        d=safe_read(path)
        if d.get('schema_version')==1 and isinstance(d.get('symbols'),dict):
            return d['symbols']
    except (OSError,ValueError,TypeError,EvidenceBlocked):pass
    return {}

def run(*,now=None,clock=lambda:dt.datetime.now(UTC),universe=UNIVERSE,
        source=OUTPUT,status=STATUS,ledger=LEDGER,holiday=HOLIDAY_GATE,
        ciks=CIK_MAP,forced=None,do_mbb=True,do_quality=True):
    now=now or clock()
    if now.tzinfo is None:raise ScreeningBlocked('NAIVE_CLOCK')
    now=now.astimezone(UTC)
    try:g=safe_read(holiday)
    except (OSError,ValueError,TypeError,EvidenceBlocked):g=None
    if not holiday_allows(g,now):
        return {'status':'HOLIDAY_FAIL_CLOSED','broker_orders':0,'symbols_attempted':0}
    tracked=universe_read(universe)
    try:ids=load_sec_ticker_directory(ciks)
    except (OSError,ValueError,TypeError,KeyError,EvidenceBlocked) as exc:
        raise ScreeningBlocked('SEC_TICKER_MAP_NOT_TRUSTED') from exc
    owner_protected(source,directory=True)
    owner_protected(status.parent,directory=True)
    owner_protected(ledger.parent,directory=True)
    if forced is not None:
        selected=_clean(forced,set(tracked)|set(ids))[:MAX_BATCH]
    else:
        selected=candidates(now,tracked,ids,
            mbb=None if do_mbb else [],quality=None if do_quality else [])
    previous=load_prior_ledger(ledger)
    records={sym:previous.get(sym,{'status':'NOT_YET_SCREENED',
              'buy_clearance_eligible':False}) for sym in tracked}
    completed={};unknown={};ran=0
    begin=time.monotonic()
    for symbol in selected:
        if time.monotonic()-begin>MAX_RUNTIME:break
        row={'last_checked_at_utc':clock().astimezone(UTC).isoformat(),
             'buy_clearance_eligible':False}
        if symbol not in ids:
            row.update(status='NEWS_UNKNOWN_SEC_IDENTITY_UNAVAILABLE')
        elif symbol not in ISSUER_RSS:
            # For all followed tickers without official issuer RSS, still
            # collect independent SEC + licensed data, NEVER publish clearance.
            row.update(partial_screen(symbol,int(ids[symbol]),now,clock))
        else:
            try:
                doc=source_manifest(symbol,int(ids[symbol]),now,clock)
                if len(json.dumps(doc))>250000:
                    raise SourceUnknown('SOURCE_BUNDLE_OVERSIZE')
                atomic_write(source/(symbol+'.json'),doc)
                row.update(status='THREE_SOURCE_BUNDLE_READY_PUBLISHER_DECIDES',
                    issuer_rss='VERIFIED',sec_identity='VERIFIED',
                    licensed_news='COMPLETE_ORIGINAL_RECEIPT',
                    in_window_event_count=len(doc['evidence']))
                completed[symbol]=len(doc['evidence'])
            except (SourceUnknown,EvidenceBlocked,TypeError,KeyError,
                    ValueError,OSError) as exc:
                row.update(status='NEWS_UNKNOWN_SOURCE_INCOMPLETE',
                    error=getattr(exc,'reason',type(exc).__name__))
                stale=source/(symbol+'.json')
                if stale.is_file() and not stale.is_symlink():stale.unlink()
        row['last_checked_at_utc']=clock().astimezone(UTC).isoformat()
        records[symbol]=row
        if symbol not in completed:unknown[symbol]=row['status']
        ran+=1
    # Append dynamic, SEC-mapped signal candidates without presenting them as
    # part of the fixed list; older unseen names retain their known stale state.
    trackedset=set(tracked)
    for symbol in selected:
        if symbol not in trackedset and symbol in records:
            records[symbol]['dynamic_qualified_discovery']=True
    for symbol in selected[ran:]:
        if symbol in trackedset and symbol not in records:
            records[symbol]={'status':'DEFERRED_RUNTIME_LIMIT',
                             'buy_clearance_eligible':False}
    summary={'status':'FOLLOWED_UNIVERSE_SCREENING_CHECKED',
      'asof_utc':clock().astimezone(UTC).isoformat(),
      'universe_stock_count':len(tracked),
      'issuer_rss_catalog_size':len(ISSUER_RSS),
      'batch_selected_count':len(selected),'batch_checked_count':ran,
      'three_source_bundles_published':len(completed),
      'partial_or_unknown_checked':len(unknown),
      'selected_symbols':selected,
      'checked_status_by_symbol':{s:records[s]['status'] for s in selected[:ran]},
      'elapsed_seconds':round(time.monotonic()-begin,3),
      'buy_clearances_published_by_screener':0,
      'paper_broker_orders':0,'live_broker_orders':0,
      'missing_issuer_feed_never_eligible':True}
    state={'schema_version':1,'asof_utc':summary['asof_utc'],
       'normal_followed_stock_count':len(tracked),
       'symbols':records,'missing_issuer_feed_never_eligible':True}
    atomic_write(ledger,state)
    atomic_write(status,summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--once',required=True,action='store_true')
    p.parse_args()
    print(json.dumps(run(),sort_keys=True))
