"""One-shot READ ONLY Alpaca PAPER fill-to-order roundtrip reconstruction."""
import json, hashlib, statistics, collections
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
CT=ZoneInfo("America/Chicago")
D=lambda x:Decimal(str(x))
h=lambda v:hashlib.sha256(str(v).encode()).hexdigest()[:10]
def timeparse(v):return datetime.fromisoformat(v.replace("Z","+00:00"))
def source(o):
    s=str(o.get("client_order_id") or "")
    return "MBB" if s.startswith("MBB-") else "FDR" if s.startswith("FDR-") else ("OTHER" if s else "UNKNOWN")
def audit_roundtrips(fills, orders):
    seen={}; events=[]; issues=collections.Counter()
    for row in fills:
        fid=str(row.get("id") or "")
        if not fid:
            issues["missing_fill_id"]+=1;continue
        if fid in seen:
            if seen[fid]!=row:raise ValueError("Conflicting duplicate fill ID")
            issues["repeated_fill_id_deduplicated"]+=1;continue
        seen[fid]=row
        oid=str(row.get("order_id") or "");o=orders.get(oid)
        if not o:issues["missing_broker_order"]+=1;continue
        try:
            qty=D(row["qty"]);px=D(row["price"]);at=timeparse(row["transaction_time"])
            side=str(o.get("side") or row.get("side")).lower()
            symbol=str(o.get("symbol"))
            assert qty>0 and px>0 and side in ("buy","sell") and symbol
            assert str(row.get("symbol") or symbol)==symbol
        except Exception:
            issues["bad_fill_record"]+=1;continue
        events.append(dict(fill_id=fid,order_id=oid,qty=qty,price=px,at=at,side=side,symbol=symbol,source=source(o)))
    events.sort(key=lambda z:(z["at"],z["fill_id"]))
    queues=collections.defaultdict(collections.deque);groups={};unmatched=collections.Counter();cross=collections.Counter()
    for e in events:
        if e["side"]=="buy":
            oid=e["order_id"]
            if oid not in groups:
                groups[oid]=dict(symbol=e["symbol"],source=e["source"],first=e["at"],last=e["at"],
                 bought=D(0),closed=D(0),entry_cost=D(0),closed_cost=D(0),exit_value=D(0),
                 first_exit=None,last_exit=None,exit_ids=set(),exit_sources=set(),buyfill=0,sellfill=set())
            g=groups[oid]
            g["bought"]+=e["qty"];g["entry_cost"]+=e["qty"]*e["price"]
            g["last"]=max(g["last"],e["at"]);g["buyfill"]+=1
            queues[e["symbol"]].append(dict(oid=oid,qty=e["qty"],price=e["price"],source=e["source"]))
        else:
            remain=e["qty"]
            while remain:
                if not queues[e["symbol"]]:
                    unmatched[e["symbol"]]+=remain;break
                lot=queues[e["symbol"]][0];q=min(remain,lot["qty"]);g=groups[lot["oid"]]
                g["closed"]+=q;g["closed_cost"]+=q*lot["price"];g["exit_value"]+=q*e["price"]
                g["first_exit"]=min(g["first_exit"],e["at"]) if g["first_exit"] else e["at"]
                g["last_exit"]=max(g["last_exit"],e["at"]) if g["last_exit"] else e["at"]
                g["exit_ids"].add(e["order_id"]);g["exit_sources"].add(e["source"]);g["sellfill"].add(e["fill_id"])
                if e["source"]!=lot["source"]:cross[(lot["source"],e["source"])]+=1
                lot["qty"]-=q;remain-=q
                if not lot["qty"]:queues[e["symbol"]].popleft()
    complete=[g for g in groups.values() if g["bought"]==g["closed"] and g["bought"]>0]
    partial=[g for g in groups.values() if g["bought"]>g["closed"]]
    summary=collections.defaultdict(list); examples=[]
    for g in complete:
        start=g["first"].astimezone(CT);end=g["last_exit"].astimezone(CT)
        pnl=g["exit_value"]-g["closed_cost"]
        hold=(end-start).total_seconds()/60
        summary[g["source"]].append((start.date().isoformat(),hold,pnl,g))
        if g["symbol"] in ("AMD","MCHP","CARR","KMI","OXY"):
            examples.append(dict(symbol=g["symbol"],source=g["source"],day=start.date().isoformat(),
             buy_first_ct=start.strftime("%H:%M:%S"),buy_last_ct=g["last"].astimezone(CT).strftime("%H:%M:%S"),
             sell_first_ct=g["first_exit"].astimezone(CT).strftime("%H:%M:%S"),
             sell_last_ct=end.strftime("%H:%M:%S"),duration_min=round(hold,3),
             qty=str(g["bought"]),gross_pnl_usd=str(pnl.quantize(D(".01"))),
             entry_fills=g["buyfill"],exit_fills=len(g["sellfill"]),exit_orders=len(g["exit_ids"]),exit_order_hashes=sorted(h(x) for x in g["exit_ids"]),
             exit_types=sorted(set(str((orders[o].get("order_class"),orders[o].get("type"))) for o in g["exit_ids"])),
             exit_sources=sorted(g["exit_sources"])))
    out=dict(broker="ALPACA_PAPER_BOUNDED_CREDENTIAL",window_start_utc="2026-11-09T00:00:00Z",
     fetched_fill_activities=len(fills),unique_fill_activities=len(seen),matched_fills=len(events),
     broker_orders=len(orders),unique_filled_order_ids=len(set(e["order_id"] for e in events)),
     unresolved=dict(issues),unmatched_sell_qty={k:str(v) for k,v in unmatched.items()},
     cross_source_segments={str(k):v for k,v in cross.items()},complete_entry_orders=len(complete),
     incomplete_entry_orders=len(partial),by_source={},examples=examples)
    for k,rows in summary.items():
        gross=sum((r[2] for r in rows),D(0));dur=[r[1] for r in rows]
        out["by_source"][k]=dict(fully_closed_entry_orders=len(rows),winning_entry_orders=sum(r[2]>0 for r in rows),
            gross_usd=str(gross.quantize(D(".01"))),median_hold_min=round(statistics.median(dur),2),
            rapid_at_most_min={str(t):sum(r[1]<=t for r in rows) for t in (2,5,10,30)},
            session_counts=dict(collections.Counter(r[0] for r in rows)),
            exit_order_classes=dict(collections.Counter(str(orders[oid].get("order_class")) for r in rows for oid in r[3]["exit_ids"])))
    filled_ids=set(e["order_id"] for e in events)
    out["nonfilled_broker_order_statuses"]=dict(collections.Counter(str(o.get("status")) for oid,o in orders.items() if oid not in filled_ids))
    out["filled_order_statuses"]=dict(collections.Counter(str(orders[oid].get("status")) for oid in filled_ids))
    out["filled_order_type_classes"]=dict(collections.Counter(str((orders[oid].get("order_class"),orders[oid].get("type"))) for oid in filled_ids))
    for k,rows in summary.items():
        out["by_source"][k]["exit_order_types"]=dict(collections.Counter(str(orders[oid].get("type")) for r in rows for oid in r[3]["exit_ids"]))
    out["market_exit_details"]=[dict(day=g["first"].astimezone(CT).date().isoformat(),symbol=g["symbol"],source=g["source"],exit_time_ct=g["last_exit"].astimezone(CT).strftime("%H:%M:%S"),exit_order_hashes=sorted(h(x) for x in g["exit_ids"] if orders[x].get("type")=="market")) for g in complete if any(orders[x].get("type")=="market" for x in g["exit_ids"])]
    return out

if __name__=="__main__":
    from multi_broker_bridge import paper_fill_audit as a
    out=audit_roundtrips(a.paged_fills(),a.order_map())
    print(json.dumps(out,sort_keys=True,indent=2,default=str))
