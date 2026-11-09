"""Read-only per-order PAPER purchase/sale timing and price ledger, no mutation.

Outputs only ticker, MBB/FDR writer tag, local fill times, filled shares
and average actual simulated price. Multiple partial fills of one order
are aggregated; no account ID or broker order ID is exposed.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import json
from zoneinfo import ZoneInfo
from .paper_fill_audit import paged_fills,order_map

CT=ZoneInfo("America/Chicago")
def main():
    try:
        fills=paged_fills()
        orders=order_map()
        grouped={}
        unmatched=0
        for f in fills:
            if f.get("activity_type")!="FILL":continue
            order=orders.get(str(f.get("order_id","")))
            if order is None:
                unmatched+=1
                continue
            cid=str(order.get("client_order_id",""))
            tag=("MBB" if cid.startswith("MBB-") else
                 "FDR" if cid.startswith("FDR") else
                 "OTHER")
            dt=datetime.fromisoformat(f["transaction_time"].replace("Z","+00:00"))
            side=str(f.get("side","")).lower()
            q=Decimal(str(f["qty"]))
            price=Decimal(str(f["price"]))
            if q<=0 or price<=0 or not q.is_finite() or not price.is_finite():
                raise ValueError("Bad fill")
            key=str(f["order_id"])
            if key not in grouped:
                grouped[key]={"tag":tag,"symbol":str(f.get("symbol")),
                              "side":side,"qty":Decimal(0),"dollars":Decimal(0),
                              "first":dt,"last":dt}
            row=grouped[key]
            if row["side"]!=side or row["symbol"]!=f.get("symbol"):
                raise ValueError("Mixed broker fill sides in one order")
            row["qty"]+=q;row["dollars"]+=q*price
            row["first"]=min(row["first"],dt);row["last"]=max(row["last"],dt)
        out=[]
        for o in grouped.values():
            out.append({"tag":o["tag"],"symbol":o["symbol"],"side":o["side"],
                        "first_fill_ct":o["first"].astimezone(CT).strftime("%Y-%m-%d %H:%M:%S"),
                        "last_fill_ct":o["last"].astimezone(CT).strftime("%H:%M:%S"),
                        "qty":str(o["qty"]),
                        "vwap":str((o["dollars"]/o["qty"]).quantize(Decimal(".001")))})
        out.sort(key=lambda a:(a["first_fill_ct"],a["symbol"],a["side"]))
        print(json.dumps({"status":"READ_ONLY_PAPER_ORDER_TIMING",
                          "date_scope_utc":"2026-11-09T00:00Z onward",
                          "orders":[o for o in out if o["tag"] in ("MBB","FDR")],
                          "missing_order_mapping_fills":unmatched,
                          "writer_counts":{t:sum(o["tag"]==t for o in out)
                                           for t in ("MBB","FDR","OTHER")},
                          "orders_submitted":0},sort_keys=True))
        return 0
    except (ValueError,KeyError,TypeError) as exc:
        print(json.dumps({"status":"AUDIT_INCOMPLETE",
                          "reason_type":type(exc).__name__,"orders_submitted":0}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
