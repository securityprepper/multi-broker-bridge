"""Read-only broker order fill-average vs hypothetical mark at 13:40 ET.
No network; all inputs are read-only snapshots. No broker actions.
"""
import json,collections
from decimal import Decimal as D
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
inv=json.loads(Path('/var/lib/securityprepper-paper-inventory/current.json').read_text())
market=json.loads(Path('/tmp/v2-run20-broker-churn/nov9_rth_sip_1m_to1340CT.json').read_text())['bars']
t1340=datetime(2026,11,9,14,40,tzinfo=ET)
tstart=datetime(2026,11,9,9,30,tzinfo=ET)
def tm(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(ET)
def pre1340_mark(sym):
    # require exact fully completed 13:39-13:40 ET trade minute
    arr=[a for a in market.get(sym,[]) if tm(a[0]).strftime('%H:%M')=='14:39']
    return D(str(arr[0][4])) if len(arr)==1 else None
orders=collections.defaultdict(list)
for x in inv['recent_orders']:
    cid=str(x.get('client_order_id') or '')
    if x.get('status')!='filled' or not str(x.get('filled_at') or '').startswith('2026-11-09'):
        continue
    label='MBB' if cid.startswith('MBB-') else 'FDR' if cid.startswith('FDR-') else 'OTHER'
    if label=='OTHER':continue
    a={'family':label,'sym':x['symbol'],'side':x['side'],
       'qty':D(str(x['filled_qty'])), 'avg':D(str(x['filled_avg_price'])),'at':tm(x['filled_at']),
       'type':x.get('type'),'created_at':tm(x['created_at'])}
    if a['avg']<=0 or a['qty']<=0:raise ValueError('Invalid fill economics')
    orders[label].append(a)

def reconstruct(label):
    allx=sorted(orders[label],key=lambda x:(x['at'],x['side']))
    lots=collections.defaultdict(collections.deque);closed=[]
    for o in allx:
        sym=o['sym']
        if o['side']=='buy':
            lots[sym].append({'qty':o['qty'],'entry_qty':o['qty'],'entry_price':o['avg'],'at':o['at']})
        elif o['side']=='sell':
            n=o['qty']
            while n:
                if not lots[sym]:raise ValueError('Unmatched sale '+sym+' '+label)
                lot=lots[sym][0];used=min(n,lot['qty'])
                closed.append({'sym':sym,'entry_time_et':lot['at'].isoformat(),'exit_time_et':o['at'].isoformat(),
                               'entry_price':float(lot['entry_price']),'exit_price':float(o['avg']),
                               'qty':float(used),'realized_usd':float(used*(o['avg']-lot['entry_price'])),
                               'exit_before_1340':o['at']<=t1340,'entry_before_1340':lot['at']<t1340,
                               'entry_rth':lot['at']>=tstart,'hold_mark':float(pre1340_mark(sym)) if pre1340_mark(sym) else None,
                               'hold_usd':float(used*(pre1340_mark(sym)-lot['entry_price'])) if pre1340_mark(sym) else None})
                n-=used;lot['qty']-=used
                if not lot['qty']:lots[sym].popleft()
        else:raise ValueError('Unknown side')
    openlots=[{'sym':sym,'qty':float(x['qty']),'entry_time_et':x['at'].isoformat()} for sym,v in lots.items() for x in v if x['qty']>0]
    return closed,openlots
out={}
for lab in ('MBB','FDR'):
    closed,openlots=reconstruct(lab)
    eligible=[x for x in closed if x['entry_before_1340'] and x['exit_before_1340'] and x['hold_mark'] is not None]
    rth=[x for x in eligible if x['entry_rth']]
    early=[x for x in eligible if not x['entry_rth']]
    def metrics(rows):
        syms=set(x['sym'] for x in rows)
        return {'matched_closed_parts':len(rows),'symbols':len(syms),'realized_usd':round(sum(x['realized_usd'] for x in rows),2),
                'hold_to_1340_usd_gross_mark':round(sum(x['hold_usd'] for x in rows if x['hold_usd'] is not None),2),
                'hold_minus_actual_usd':round(sum(x['hold_usd']-x['realized_usd'] for x in rows if x['hold_usd'] is not None),2),
                'hold_positive_lots':sum(x['hold_usd']>0 for x in rows if x['hold_usd'] is not None),
                'actual_positive_lots':sum(x['realized_usd']>0 for x in rows)}
    all_actual=metrics(closed)
    out[lab]={'all':all_actual,'open_lots':openlots,'eligible':metrics(eligible),'rth_entries':metrics(rth),
              'premarket_entries':metrics(early),'eligible_by_sym':{s:metrics([x for x in eligible if x['sym']==s]) for s in sorted(set(x['sym'] for x in eligible))},
              'eligibility':{'original_exit_by_1340':len([x for x in closed if x['exit_before_1340']]),
                             'excluded_after_1340_exit':len([x for x in closed if not x['exit_before_1340']]),
                             'marked_eligible':len(eligible)}}
Path('/tmp/v2-run20-broker-churn/hold1340CT_audit_private.json').write_text(json.dumps({'summary':out,'matched_lots':{z:reconstruct(z)[0] for z in ('MBB','FDR')}},indent=2))
print(json.dumps(out,indent=2))
