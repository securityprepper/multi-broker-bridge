"""Research-only exact Alpaca PAPER order-UUID to decision-journal and fill-activity join.
All network requests are allowlisted GETs. No broker orders or V1 changes.
Private account and broker order IDs stay in process memory; public JSON aggregates only.
"""
from __future__ import annotations
import hashlib, json, subprocess, urllib.parse, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

START = "2026-11-09T00:00:00Z"
ROOT = Path("/etc/securityprepper/alpaca-feed/private")
PRIVATE = Path("/tmp/v2-rapid-exit-run6-20261111/raw_research_private.json")
CHI = ZoneInfo("America/Chicago")
HOST = "https://paper-api.alpaca.markets"

def dt(t):
    x = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("Naive evidence timestamp")
    return x

def dec(n):
    return Decimal(str(n))

def get_json(path):
    if path == "/v2/account":
        pass
    elif path.startswith("/v2/orders?") or path.startswith("/v2/account/activities?"):
        pass
    else:
        raise ValueError("REJECT_NON_GET_ONLY_ALLOWLIST")
    if not path.startswith(("/v2/account", "/v2/orders")):
        raise ValueError("Invalid broker path")
    key = (ROOT/"alpaca_data_key_id").read_text().strip()
    secret = (ROOT/"alpaca_data_secret").read_text().strip()
    request = urllib.request.Request(HOST+path, method="GET",
        headers={"APCA-API-KEY-ID":key, "APCA-API-SECRET-KEY":secret,
                 "Accept":"application/json"})
    with urllib.request.urlopen(request, timeout=15) as res:
        if res.status != 200: raise ValueError("Non-200 broker response")
        data = res.read(3_000_001)
        if len(data) > 3_000_000: raise ValueError("Broker response oversize")
        return json.loads(data)

def fetch_orders():
    query = urllib.parse.urlencode({"status":"all", "after":START,
        "limit":500, "direction":"asc"})
    rows = get_json("/v2/orders?"+query)
    if not isinstance(rows,list) or len(rows)>=500:
        raise ValueError("Order snapshot incomplete")
    if len({x.get("id") for x in rows}) != len(rows):
        raise ValueError("Duplicate broker order UUID")
    if len({x.get("client_order_id") for x in rows}) != len(rows):
        raise ValueError("Duplicate broker client ID")
    return rows

def fetch_fill_activities():
    allrows=[];token=None
    for _ in range(15):
        q={"activity_types":"FILL","after":START,"direction":"asc","page_size":100}
        if token:q["page_token"]=token
        rows=get_json("/v2/account/activities?"+urllib.parse.urlencode(q))
        if not isinstance(rows,list):raise ValueError("Bad activities response")
        if any(x.get("activity_type")!="FILL" for x in rows):
            raise ValueError("Unexpected activity category")
        allrows.extend(rows)
        if len(rows)<100:break
        token=rows[-1].get("id")
        if not token:raise ValueError("Missing activities cursor")
    else:raise ValueError("Truncated activities")
    ids=[x.get("id") for x in allrows]
    if None in ids or len(ids)!=len(set(ids)):
        raise ValueError("Duplicate or missing fill event UUID")
    return allrows

def journal():
    cmd=["journalctl","-u","trading-sector-paper-executor.service",
         "--since","2026-11-09 00:00:00","--until","2026-11-12 00:40:00",
         "--no-pager","-o","json"]
    proc=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=40)
    byuuid={}
    for l in proc.stdout.splitlines():
        try:
            packet=json.loads(l)
            report=json.loads(packet.get("MESSAGE",""))
        except (json.JSONDecodeError,ValueError):
            continue
        if not isinstance(report,dict):continue
        timestamp=datetime.fromtimestamp(int(packet["__REALTIME_TIMESTAMP"])/1000000,
                                         timezone.utc)
        for item in report.get("orders",[]):
            if not isinstance(item,dict) or not item.get("broker_order_id"):continue
            uid=str(item["broker_order_id"])
            if uid in byuuid:raise ValueError("Duplicate submission journal UUID")
            byuuid[uid]={"at":timestamp,"reason":item.get("exit_signal_reason"),
                         "symbol":item.get("symbol"),"side":item.get("side"),
                         "status":item.get("status"),
                         "claimed_filled":item.get("exit_fill_verified")}
    return byuuid

def reconcile(trades, broker_orders, activities, decisions):
    orders_by_client={str(o["client_order_id"]):o for o in broker_orders}
    order_ids={str(o["id"]):o for o in broker_orders}
    if len(orders_by_client)!=len(broker_orders):
        raise ValueError("Duplicate client ID")
    activity_ids=[a.get("id") for a in activities]
    if None in activity_ids or len(activity_ids)!=len(set(activity_ids)):
        raise ValueError("Duplicate/missing fill activity UUID")
    filled_by_order=defaultdict(list)
    for a in activities:
        oid=str(a.get("order_id",""))
        if oid not in order_ids:raise ValueError("FILL activity order UUID not in broker orders")
        filled_by_order[oid].append(a)
    # Every recorded activity must reconcile to the broker's total filled qty
    for uid,rows in filled_by_order.items():
        expected=dec(order_ids[uid]["filled_qty"])
        actual=sum((dec(x["qty"]) for x in rows),Decimal("0"))
        if actual!=expected:
            raise ValueError("FILL quantity mismatch; refuse misleading join")
    pairs=set();used_clients=set()
    result=Counter();byday=Counter();by_source=Counter()
    reasons=Counter();lag=[];unmatched_examples=[];forced_filled=[]
    for t in trades:
        pair=(t["entry_order_id"],t["exit_order_id"])
        if pair in pairs:raise ValueError("Duplicate round-trip client pair")
        pairs.add(pair)
        source=t["source"];day=t["day"]
        byday[(day,source)]+=1
        by_source[source]+=1
        for side,cid in (("entry",pair[0]),("exit",pair[1])):
            if cid in used_clients:raise ValueError("Filled order reused across lots")
            used_clients.add(cid)
            o=orders_by_client.get(cid)
            if not o:raise ValueError("Previously verified filled client ID absent in GET")
            if o.get("status")!="filled" or o.get("side")!=("buy" if side=="entry" else "sell"):
                raise ValueError("Filled order status/side mismatch")
            if str(o.get("symbol"))!=t["symbol"] or dec(o["filled_qty"])!=dec(t["qty"]):
                raise ValueError("Filled symbol/quantity mismatch")
            if abs(dec(o["filled_avg_price"])-dec(t["entry" if side=="entry" else "exit"]))>dec("0.00002"):
                raise ValueError("Filled execution price mismatch")
            if abs((dt(o["filled_at"])-dt(t["entry_at" if side=="entry" else "exit_at"])).total_seconds())>1.0:
                raise ValueError("Filled time mismatch")
            if str(o["id"]) not in filled_by_order:
                raise ValueError("Broker filled order has no FILL UUID activities")
            result[(source,side,"BROKER_FILL_AND_ACTIVITY_VERIFIED")]+=1
            origin=decisions.get(str(o["id"]))
            if source=="MBB":
                if origin:
                    if origin["side"]!=o["side"] or origin["symbol"]!=o["symbol"]:
                        raise ValueError("Decision-journal order UUID identity mismatch")
                    result[(source,side,"JOURNAL_UUID_JOIN")]+=1
                    if side=="exit":
                        reasons[str(origin["reason"])]+=1
                        lag_seconds=(dt(o["filled_at"])-origin["at"]).total_seconds()
                        if lag_seconds < -1: raise ValueError("Fill predates journal response")
                        lag.append(lag_seconds)
                        if origin["claimed_filled"] is True:
                            raise ValueError("Submission journal asserted fill without broker readback")
                else:
                    result[(source,side,"JOURNAL_NOT_IN_RECORD")]+=1
                    if side=="exit":
                        # Independent documented time-exit client namespace:
                        # require the precise deterministic F ref, filled
                        # market order, and broker UUID-backed FILL activities.
                        forced_ref=f'MBB-{day.replace("-","")}-F-{t["symbol"]}'
                        if cid==forced_ref and o.get("type")=="market":
                            forced_filled.append((day,t["symbol"],dt(o["filled_at"]).astimezone(CHI).strftime("%H:%M:%S")))
                            result[(source,side,"FORCED_1340_BROKER_FILLED")]+=1
                        else:
                            unmatched_examples.append((day,t["symbol"]))
        delta=(dt(t["exit_at"])-dt(t["entry_at"])).total_seconds()
        limit="<=2m" if delta<=120 else "<=5m" if delta<=300 else "<=10m" if delta<=600 else "<=30m" if delta<=1800 else ">30m"
        result[(source,"duration",limit)]+=1
    unmatched_orders = [(o["id"],o["client_order_id"]) for o in broker_orders
                        if o["status"]=="filled" and o["client_order_id"] not in used_clients]
    return {"private_scope":"ONE_VERIFIED_PAPER_ACCOUNT",
            "round_trips":len(trades),"distinct_days":len({t["day"] for t in trades}),
            "by_day_source":{f"{day}|{s}":n for (day,s),n in sorted(byday.items())},
            "source_trips":dict(by_source),
            "matched_filled_activity_uuid_events":sum(len(filled_by_order[str(orders_by_client[c]["id"])]) for c in used_clients),
            "unique_filled_order_uuids_in_pairs":len(used_clients),
            "broker_orders_total":len(broker_orders),
            "broker_fill_activities_total":len(activities),
            "decision_journal_submitted_uuid_count":len(decisions),
            "result_count":{str(k):v for k,v in sorted(result.items())},
            "matched_exit_decision_reason_counts":dict(reasons),
            "accepted_sell_to_filled_seconds_min":round(min(lag),2) if lag else None,
            "accepted_sell_to_filled_seconds_median":round(median(lag),2) if lag else None,
            "accepted_sell_to_filled_seconds_max":round(max(lag),2) if lag else None,
            "unmatched_mbb_exit_symbol_days":sorted(unmatched_examples),
            "forced_market_fills_after_1340_ct":sorted(forced_filled),
            "filled_broker_orders_outside_60_pairs":len(unmatched_orders),
            "orders_submitted":0,"research_only":True}

def main():
    snap=json.loads(PRIVATE.read_text())
    if not snap.get("research_only") or snap.get("broker_orders_submitted")!=0:
        raise ValueError("Wrong prior cohort")
    a=get_json("/v2/account")
    if a.get("status")!="ACTIVE" or a.get("trading_blocked") is not False or not a.get("id"):
        raise ValueError("Unverified PAPER account")
    orders=fetch_orders()
    fills=fetch_fill_activities()
    docs=journal()
    report=reconcile(snap["trades"],orders,fills,docs)
    report["broker_account_id_privately_verified"]=True
    report["retrieved_at_utc"]=datetime.now(timezone.utc).isoformat()
    path=Path("/tmp/v2-run12-uuid-reason-join-20261112/sanitized-result.json")
    with path.open("x") as f:json.dump(report,f,indent=2,sort_keys=True)
    path.chmod(0o600)
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()