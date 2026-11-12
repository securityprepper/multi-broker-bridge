"""Pure offline Alpaca SIP quote response classifier, no broker client/order actions.

Diagnostic only: cannot reconstruct a quote discarded from an earlier response.
Prices are contemporaneous displayed quotes, never guaranteed executable fills.
"""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation


def timepoint(value):
    if not isinstance(value, str):
        return None
    try:
        t = datetime.fromisoformat(value.replace('Z','+00:00'))
        return t if t.tzinfo is not None else None
    except ValueError:
        return None


def classify(payload, *, start, end, side, filled_qty, max_age_s=1.5, max_spread_pct=1):
    """Classify one pre-fill 5s quote window without masking parser failures as API failures."""
    if side not in ('entry','exit') or filled_qty <= 0 or not (start < end):
        raise ValueError('Bad research argument')
    if not isinstance(payload, dict) or not isinstance(payload.get('quotes'), list):
        return {'status':'MALFORMED_RESPONSE', 'rejected_rows':0}
    if payload.get('next_page_token'):
        return {'status':'PAGINATION_UNRESOLVED', 'rejected_rows':0}
    good=[]; invalid=0; excluded=0
    for x in payload['quotes']:
        if not isinstance(x,dict):
            invalid+=1;continue
        t=timepoint(x.get('t'))
        try:
            bp=Decimal(str(x['bp']));ap=Decimal(str(x['ap']))
            bs=Decimal(str(x['bs']));ass=Decimal(str(x['as']))
        except (KeyError,ValueError,InvalidOperation,TypeError):
            invalid+=1;continue
        if not t or not all(q.is_finite() for q in (bp,ap,bs,ass)):
            invalid+=1;continue
        if bp<=0 or ap<bp or bs<=0 or ass<=0:
            invalid+=1;continue
        if not (start<=t<=end):
            excluded+=1;continue
        spread=Decimal(100)*(ap-bp)/ap
        if spread>Decimal(str(max_spread_pct)):
            excluded+=1;continue
        good.append((t,bp,ap,bs,ass,float(spread)))
    if not good:
        return {'status':'NO_VALID_QUOTE', 'rejected_rows':invalid,
                'excluded_rows':excluded, 'parse_error_present':invalid>0}
    t,bp,ap,bs,ass,spread=max(good,key=lambda q:q[0])
    age=(end-t).total_seconds()
    result={'rejected_rows':invalid,'excluded_rows':excluded,
            'age_seconds':round(age,4),'spread_pct':round(spread,6)}
    if age<0 or age>max_age_s:
        result['status']='STALE_OR_FUTURE_QUOTE';return result
    side_size=ass if side=='entry' else bs
    if side_size<Decimal(str(filled_qty)):
        result['status']='DISPLAYED_SIZE_INSUFFICIENT';return result
    result['status']='FRESH_ASOF_DISPLAYED_QUOTE'
    result['executable_fill_verified']=False
    return result
