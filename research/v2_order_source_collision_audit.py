"""Read-only attribution and collision audit of an Alpaca PAPER inventory snapshot.

Does NOT connect to broker, read credentials, call HTTP or modify files. Reports
order counts, not partial broker FILL activity counts. No client IDs emitted.
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

def family(cid):
    s=str(cid or "")
    return "MBB" if s.startswith("MBB-") else "FDR" if s.startswith("FDR-") else "UNATTRIBUTED"

def timestamp(value):
    if not value:raise ValueError("missing timestamp")
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None: raise ValueError("timestamp lacks offset")
    return dt.astimezone(timezone.utc)

def analyze(inv,day="2026-11-09"):
    if not inv.get("paper_only") or not inv.get("broker_verified"):
        raise ValueError("not a broker-verified PAPER inventory")
    if not inv.get("recent_orders_complete"):
        raise ValueError("recent orders history incomplete")
    allrows=[x for x in inv.get("recent_orders",[]) if
             x.get("status")=="filled" and str(x.get("filled_at") or "").startswith(day)]
    ids=[str(x.get("client_order_id") or "") for x in allrows]
    noid=sum(not x for x in ids)
    dupe=len(ids)-len(set(ids))
    family_rows=defaultdict(list)
    for row in allrows:
        family_rows[family(row.get("client_order_id"))].append(row)
    counts={}
    intervals=defaultdict(dict)
    for f in ("MBB","FDR","UNATTRIBUTED"):
        rows=family_rows[f]
        counts[f]={"filled_orders":len(rows),"buy_orders":sum(r.get("side")=="buy" for r in rows),
                   "sell_orders":sum(r.get("side")=="sell" for r in rows),
                   "unique_symbols":len({r.get("symbol") for r in rows}),
                   "strategy_tags":dict(Counter(str(r.get("strategy") or "") for r in rows))}
        groups=defaultdict(list)
        for r in rows:groups[str(r.get("symbol"))].append(r)
        for sym,parts in groups.items():
            buys=sorted((r for r in parts if r.get("side")=="buy"),key=lambda x:x["filled_at"])
            sells=sorted((r for r in parts if r.get("side")=="sell"),key=lambda x:x["filled_at"])
            if len(buys)==len(sells)==1:
                b,s=buys[0],sells[0]
                if abs(float(b.get("filled_qty") or 0)-float(s.get("filled_qty") or 0))<1e-9:
                    start,end=timestamp(b["filled_at"]),timestamp(s["filled_at"])
                    if start<=end:intervals[f][sym]=(start,end)
    shared=sorted(set(intervals["MBB"])&set(intervals["FDR"]))
    simultaneous=[]
    mingap=[]
    for sym in shared:
        aa,ab=intervals["MBB"][sym]
        ba,bb=intervals["FDR"][sym]
        if max(aa,ba)<min(ab,bb):simultaneous.append(sym)
        if ab<=ba:gap=(ba-ab).total_seconds()/60
        elif bb<=aa:gap=(aa-bb).total_seconds()/60
        else:gap=0.
        mingap.append((sym,round(gap,2)))
    return {"date":day,"inventory_asof_utc":inv.get("asof_utc"),
      "broker_verified":True,"position_count_snapshot":inv.get("positions_count"),
      "open_order_count_snapshot":inv.get("open_orders_count"),
      "filled_orders_total":len(allrows),"by_family":counts,
      "missing_client_order_ids":noid,"duplicate_client_order_ids":dupe,
      "shared_symbols_between_MBB_and_FDR":shared,
      "fully_pairable_shared_symbols":len(shared),
      "simultaneously_open_both_strategies":simultaneous,
      "minutes_between_nearest_exposure":dict(mingap),
      "note":"Order snapshots cannot reconcile individual partial FILL activity IDs or prove no other broker writer outside this date/range."}

if __name__=="__main__":
    pa=argparse.ArgumentParser()
    pa.add_argument("--inventory",required=True)
    pa.add_argument("--day",default="2026-11-09")
    args=pa.parse_args()
    print(json.dumps(analyze(json.loads(Path(args.inventory).read_text()),args.day),indent=2))
