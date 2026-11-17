"""R1/earnings read-only, exploratory sector-matched and growth eligibility diagnostic.

Post-hoc descriptive only: historical earnings dates are not issuer-confirmed, and
latest issuer universe/SEC data may be revised; NOT a forward trading evaluation.
No DB, brokerage or network access.
"""
from __future__ import annotations
import collections,datetime as dt,json,math,random,statistics
from pathlib import Path

ROOT=Path('/var/lib/securityprepper-earnings-anticipation')
OUTPUT=Path('/tmp/v2-trading-strategy-research/research/v2_20261116_2130_preearnings_matched_diagnostic.json')
SEED=20261116

def positive_rate(a):
    return sum(x>0 for x in a)/len(a) if a else None

def wilson(count,n):
    if not n:return None
    z=1.96;p=count/n
    d=1+z*z/n
    midpoint=(p+z*z/(2*n))/d
    e=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(max(0,midpoint-e),4),round(min(1,midpoint+e),4)]

def nearest_control(event, controls, n=20):
    volume=event.get('median_20day_dollar_volume')
    assert volume and volume>0
    # Historical 20-day volume observed for each event. Avoid current market cap.
    return sorted(controls,key=lambda p:(
        abs(math.log(p['median_20day_dollar_volume']/volume)),
        p['symbol']))[:n]

def main():
    broad=json.loads((ROOT/'research-20261116-broad-market-pre-earnings-3809.json').read_text())
    sector=json.loads((ROOT/'research-20261116-sector-98-last-earnings.json').read_text())
    latest=json.loads((ROOT/'latest.json').read_text())
    events=broad['pairs']
    assert len(events)==3809 and len({(p['symbol'],p['earnings_date']) for p in events})==3809
    by_pair={(p['symbol'],p['earnings_date']):p for p in events}
    sector_syms=set(sector['events'])
    assert len(sector_syms)==98
    controls=collections.defaultdict(list)
    for p in events:
        if p['symbol'] not in sector_syms:
            controls[p['earnings_date']].append(p)
    matched=[];unmatched=[]
    for sym,event in sector['events'].items():
        date=(event.get('previous_event_calendar') or {}).get('date')
        row=by_pair.get((sym,date))
        if not row or not event.get('returns_available'):
            unmatched.append(sym)
            continue
        comps=nearest_control(row,controls[date])
        assert comps
        matched.append({
            'symbol':sym,'earnings_date':date,
            'event_return5_pct':row['return5_pct'],
            'event_return10_pct':row['return10_pct'],
            'peer_control_5d_mean_pct':statistics.mean(p['return5_pct'] for p in comps),
            'peer_control_5d_positive_fraction':positive_rate([p['return5_pct'] for p in comps]),
            'n_controls':len(comps),
            'cluster_week':date[:4]+'-W'+str(dt.date.fromisoformat(date).isocalendar().week).zfill(2)
        })
    assert len(matched)==98 and len(matched)+len(unmatched)==98
    # Date/week clustered uncertainty, not independent event bootstrap.
    grouped=collections.defaultdict(list)
    for p in matched:grouped[p['cluster_week']].append(p)
    clusters=list(grouped.values())
    rng=random.Random(SEED)
    delta=[];sector_positive=[];control_positive=[]
    for _ in range(4000):
        group_sample=[rng.choice(clusters) for _ in clusters]
        sample=[p for group in group_sample for p in group]
        delta.append(statistics.mean(p['event_return5_pct']-p['peer_control_5d_mean_pct'] for p in sample))
        sector_positive.append(positive_rate([p['event_return5_pct'] for p in sample]))
        control_positive.append(statistics.mean(p['peer_control_5d_positive_fraction'] for p in sample))
    def percentile(a,p):
        s=sorted(a);return s[max(0,min(len(s)-1,round((len(s)-1)*p)))]
    candidates={p['symbol']:p for p in latest['candidates']}
    recent=[];both=[];unknown=[]
    for sym,c in candidates.items():
        f=c.get('fundamentals') or {}
        eps=f.get('annual_eps_yoy_pct_recent_then_prior') or []
        rev=f.get('annual_revenue_yoy_pct_recent_then_prior') or []
        if len(eps)>=2 and len(rev)>=2:
            if eps[0]>=15 and rev[0]>=15:
                recent.append(sym)
                if eps[1]>=15 and rev[1]>=15:both.append(sym)
        else:unknown.append(sym)
    def eligibility(events_subset):
        point_in_time=[]
        filing_unverified=[]
        for p in events_subset:
            f=(candidates[p['symbol']].get('fundamentals') or {})
            filed=f.get('last_filed')
            # Filed-before-entry is necessary but not sufficient proof of point-in-time
            # XBRL observations, never rely on after-event data.
            if filed and filed<=p['prior6_day']:
                point_in_time.append(p)
            else:filing_unverified.append((p['symbol'],p['earnings_date']))
        returns=[p['return5_pct'] for p in point_in_time]
        k=sum(q>0 for q in returns)
        return {'asof_filed_event_n':len(point_in_time),
                'positive_5d_count':k,
                'positive_5d_fraction':round(k/len(point_in_time),4) if point_in_time else None,
                'positive_5d_wilson95':wilson(k,len(point_in_time)),
                'mean_5d_close_return_pct':round(statistics.mean(returns),4) if returns else None,
                'events_filing_after_entry_or_unknown':filing_unverified,
                'by_calendar_month':dict(collections.Counter(p['earnings_date'][:7] for p in point_in_time))}
    result={
      'created_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'classification':'EXPLORATORY_RETROSPECTIVE_NOT_AFTER_FEE_NOT_FORWARD',
      'source_files':[str(ROOT/f) for f in (
        'latest.json','research-20261116-broad-market-pre-earnings-3809.json',
        'research-20261116-sector-98-last-earnings.json')],
      'controls_method':'20 nearest historical median_20day_dollar_volume ordinary nonsector stock events on the identical Nasdaq calendar earnings date; excludes 98 tracked sector symbols',
      'matched_sector':{
        'n':len(matched),'distinct_earnings_week_clusters':len(clusters),
        'sector_5d_positive_count':sum(p['event_return5_pct']>0 for p in matched),
        'sector_5d_positive_fraction':round(positive_rate([p['event_return5_pct'] for p in matched]),4),
        'matched_control_5d_positive_fraction':round(statistics.mean(p['peer_control_5d_positive_fraction'] for p in matched),4),
        'sector_5d_mean_return_pct':round(statistics.mean(p['event_return5_pct'] for p in matched),4),
        'matched_control_5d_mean_return_pct':round(statistics.mean(p['peer_control_5d_mean_pct'] for p in matched),4),
        'sector_minus_matched_control_mean_5d_pct_points':round(statistics.mean(p['event_return5_pct']-p['peer_control_5d_mean_pct'] for p in matched),4),
        'cluster_week_bootstrap_95_difference_pct_points':[round(percentile(delta,.025),4),round(percentile(delta,.975),4)],
        'cluster_week_bootstrap_95_sector_positive_fraction':[round(percentile(sector_positive,.025),4),round(percentile(sector_positive,.975),4)],
        'cluster_week_bootstrap_95_matched_control_positive_fraction':[round(percentile(control_positive,.025),4),round(percentile(control_positive,.975),4)],
        'individual_sector_events':matched
      },
      'growth':{
        'forward_candidate_symbols':len(candidates),
        'known_valid_two_annual_growth_intervals':len(candidates)-len(unknown),
        'unknown_comparable_annual_growth':len(unknown),
        'one_year_15percent_revenue_and_eps_symbols':len(recent),
        'two_year_15percent_revenue_and_eps_symbols':len(both),
        'one_year_historical':eligibility([p for p in events if p['symbol'] in recent]),
        'two_year_historical':eligibility([p for p in events if p['symbol'] in both]),
        'one_year_symbol_set':recent,'two_year_symbol_set':both
      },
      'limitations':[
       'Retrospective Nasdaq calendar dates are not original issuer-verified earnings session announcements and can be revised after event',
       'The 98-sector symbol universe and latest SEC fundamentals were selected after many historical events, so genuine forward holdout is absent',
       'SEC filed date precedes historical entry but retrieved historical XBRL may include later revisions; only a necessary, not sufficient, as-of guarantee',
       '20 matched controls per sector event reuse controls and are not independent; cluster bootstrap only reflects 12 calendar week clusters',
       'Return series is SIP 1Day close-to-close and ignores actual noon-prior-session exit, bid/ask, fees, stops, quotes, gaps and corporate actions not in snapshot',
       'Original analyst EPS estimate revisions and independent first-seen evidence are missing; cannot attribute returns to changing estimates',
       'No after-fee forward edge, no broker-verified fills, no deployment or threshold change justified'
      ]
    }
    assert 0<=result['matched_sector']['sector_5d_positive_fraction']<=1
    OUTPUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'n_matched':len(matched),'clusters':len(clusters),
        'matched_sector_summary':{k:v for k,v in result['matched_sector'].items() if k!='individual_sector_events'},
        'growth_summary':{k:v for k,v in result['growth'].items() if k not in ('one_year_symbol_set','two_year_symbol_set')}},sort_keys=True))
if __name__=='__main__':main()
