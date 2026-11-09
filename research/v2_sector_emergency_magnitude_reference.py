"""V2 research-only unusually-large sector moves.
The 90th/95th magnitude cutoffs describe observed shocks, NOT profitable forward predictions.
"""
import csv,json
from collections import defaultdict

def historical_cutoffs(rows,train_fraction=.70,min_training_days=100):
    if not 0<train_fraction<1:
        raise ValueError("invalid training fraction")
    by=defaultdict(list)
    for row in rows:
        s=row["sector"];d=row["day"];p=float(row["ETF_full_day_pct"])
        by[s].append((d,abs(p)))
    results={}
    for sector,items in sorted(by.items()):
        items.sort()
        if len(set(d for d,_ in items))!=len(items):
            raise ValueError("duplicate sector-day")
        stop=int(len(items)*train_fraction)
        if stop<min_training_days:
            raise ValueError("insufficient prior training sessions")
        earlier=sorted(z for _,z in items[:stop])
        later=[z for _,z in items[stop:]]
        def quantile(q):
            return earlier[int((len(earlier)-1)*q)]
        p90=quantile(.90);p95=quantile(.95)
        results[sector]={
            "total_days":len(items),"training_days":stop,
            "first_test_day":items[stop][0],"later_days":len(later),
            "rth_observed_shock_candidate_pct":round(p90,3),
            "extended_observed_shock_candidate_pct":round(p95,3),
            "later_rth_candidate_observed_days":sum(abs(v)>=p90 for v in later),
            "later_extended_candidate_observed_days":sum(abs(v)>=p95 for v in later),
            "is_order_authorization":False,
            "future_continuation_precision":"NOT VALIDATED",
        }
    return results

def read_csv(path):
    with open(path,newline="") as f:
        return historical_cutoffs(csv.DictReader(f))

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:raise SystemExit("usage: script <prior research daily audit CSV>")
    print(json.dumps(read_csv(sys.argv[1]),indent=2))
