"""Research-only first locally archived consensus baseline. Never market/order requests.

Stores the collector's already observed Nasdaq snapshot *not* issuer verified
and not an original first-seen analyst revision. Later snapshots may be compared
with explicit interval censoring, but no backfilled historical revisions.
"""
from __future__ import annotations
import datetime as dt,json,os,hashlib,decimal
from pathlib import Path
from zoneinfo import ZoneInfo
SRC=Path('/var/lib/securityprepper-earnings-anticipation/latest.json')
BASE=Path('/tmp/v2-trading-strategy-research/research/pre_earnings_forward_baselines')
NOW=dt.datetime.now(dt.timezone.utc)
SNAP=json.loads(SRC.read_text())
seen=dt.datetime.fromisoformat(SNAP['asof_utc'])
assert seen<=NOW and NOW-seen<dt.timedelta(hours=6)
assert SNAP['strategy_version']=='EARNINGS_ANTICIPATION_V1_SHADOW'
items=[];dedup=set()
for p in SNAP['candidates']:
    sym=p.get('symbol')
    quarter=p.get('fiscal_quarter')
    date=p.get('earnings_date_estimated')
    forecast=p.get('next_consensus_eps')
    if not sym or not quarter or not date:continue
    key=(sym,quarter, date[:4])
    if key in dedup:continue
    dedup.add(key)
    try:
        numerical=str(decimal.Decimal(str(forecast)))
        if not decimal.Decimal(numerical).is_finite():numerical=None
    except (decimal.InvalidOperation,ValueError,TypeError):numerical=None
    items.append({
      'symbol':sym,'fiscal_quarter':quarter,'estimated_earnings_date':date,
      'fiscal_year':date[:4],
      'eps_consensus_from_current_collector':numerical,
      'analyst_estimates_count':p.get('analyst_estimates_count'),
      'issuer_cik':p.get('issuer_cik'),
      'collector_asof_utc':SNAP['asof_utc'],
      'earliest_own_research_archive_utc':NOW.isoformat(),
      'same_quarter_previous_estimate_verified':False,
      'original_first_seen_at_issuer_or_licensed_source_verified':False,
      'release_date_issuer_confirmed':bool(p.get('release_date_issuer_confirmed')),
      'trade_eligible':False
    })
items.sort(key=lambda x:(x['symbol'],x['fiscal_quarter']))
assert len(items)==len(dedup)
BASE.mkdir(parents=True,exist_ok=True)
name=NOW.astimezone(ZoneInfo('America/Chicago')).strftime('2026-11-16_%H%M%S_CT')+'_initial_nasdaq_consensus.json'
output=BASE/name
data={
 'snapshot_purpose':'INITIAL_RESEARCH_ARCHIVE_NEVER_BACKDATED',
 'collector_asof_utc':SNAP['asof_utc'],
 'research_archive_at_utc':NOW.isoformat(),
 'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
 'source_kind':'NASDAQ_ESTIMATE_SHADOW_UNVERIFIED_ISSUER_RELEASE_AND_ORIGINAL_FIRST_SEEN',
 'not_a_point_in_time_revision_for_prior_date':True,
 'no_broker_or_market_api_call':True,
 'no_trade_authorization':True,
 'records':items}
txt=json.dumps(data,indent=2,sort_keys=True)+'\n'
fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o444)
with os.fdopen(fd,'w') as f:
 f.write(txt);f.flush();os.fsync(f.fileno())
os.chmod(output,0o444)
print(json.dumps({'baseline':'STORED_UNVERIFIED_FIRST_RESEARCH_ARCHIVE',
'path':str(output),'rows':len(items),'numeric_consensus':sum(p['eps_consensus_from_current_collector'] is not None for p in items),
'issuer_release_confirmed':sum(p['release_date_issuer_confirmed'] for p in items),
'unverified_prior_estimate_rows':len(items),
'broker_orders':0,'snapshot_sha256':hashlib.sha256(txt.encode()).hexdigest()},sort_keys=True))
