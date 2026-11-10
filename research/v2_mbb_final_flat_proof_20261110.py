"""Offline, fail-closed MBB PAPER 13:40 flat/14:00 readback research audit.

Reads an existing complete GET-only PAPER inventory and timestamped journald JSON
lines. Never connects to broker, reads credentials, modifies strategy, or orders.
A broker order-level FIFO match does not prove exclusive strategy share ownership.
"""
from __future__ import annotations
import argparse, collections, json
from datetime import datetime, date, time
from decimal import Decimal
from zoneinfo import ZoneInfo

CT=ZoneInfo("America/Chicago")
D=Decimal

def ts(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None: raise ValueError("naive timestamp")
    return d.astimezone(CT)

def parse_journal(lines):
    records=[]
    for line in lines:
        try:
            outer=json.loads(line); data=json.loads(outer["MESSAGE"])
            at=datetime.fromtimestamp(int(outer["__REALTIME_TIMESTAMP"])/1000000,CT)
            if data.get("status")=="PAPER_DAILY_EXIT_GUARD":
                records.append({"when":at,"kind":"guard",**data.get("exit_guard",{})})
            elif all(k in data for k in ("broker_verified","positions_count","open_orders_count")):
                records.append({"when":at,"kind":"readback",**{
                    k:data[k] for k in ("broker_verified","positions_count","open_orders_count")}})
        except (ValueError,TypeError,KeyError,AttributeError,json.JSONDecodeError):
            continue
    return records

def audit(s, records, day):
    day=date.fromisoformat(day)
    start=datetime.combine(day,time(0),CT)
    cutoff=datetime.combine(day,time(13,15),CT)
    flatten=datetime.combine(day,time(13,40),CT)
    verification=datetime.combine(day,time(14,0),CT)
    if any(s.get(k) is not True for k in ("broker_verified","paper_only","recent_orders_complete")):
        raise ValueError("unverified, non-PAPER or incomplete inventory")
    asof=ts(s["asof_utc"])
    if asof.date()!=day or asof<verification: raise ValueError("snapshot not post-verification")
    if ts(s["recent_orders_since_utc"])>start: raise ValueError("insufficient order-history coverage")
    if s.get("positions_count")!=len(s.get("positions",[])) or s["positions_count"]!=0:
        raise ValueError("non-flat broker positions")
    if s.get("open_orders_count")!=len(s.get("open_orders",[])) or s["open_orders_count"]!=0:
        raise ValueError("working broker orders")
    if s.get("orders_submitted_by_exporter")!=0: raise ValueError("inventory writer submitted orders")
    relevant=[]
    seen=set()
    for o in s.get("recent_orders",[]):
        cid=o.get("client_order_id")
        if not isinstance(cid,str) or not cid.startswith("MBB-"+day.strftime("%Y%m%d")+"-"): continue
        if cid in seen: raise ValueError("duplicate MBB order id")
        seen.add(cid)
        if o.get("side")=="buy":
            submit=ts(o["submitted_at"])
            if submit.date()!=day or submit>=cutoff: raise ValueError("late or wrong-session BUY submission")
        if o.get("status")!="filled": continue
        filled=ts(o["filled_at"])
        if filled.date()!=day or filled>asof: raise ValueError("invalid fill time")
        qty=D(str(o["filled_qty"])); price=D(str(o["filled_avg_price"]))
        if not all(v.is_finite() and v>0 for v in (qty,price)): raise ValueError("invalid fill number")
        if o.get("side") not in ("buy","sell"):raise ValueError("unknown order side")
        relevant.append((filled,str(o["symbol"]),o["side"],qty,price))
    relevant.sort()
    fifo=collections.defaultdict(collections.deque)
    pnl=D(0); wins=losses=0; first_flat_sell=None; last_fill=None
    for filled,symbol,side,qty,price in relevant:
        last_fill=filled
        if side=="buy":
            fifo[symbol].append([qty,price])
            continue
        if filled>=flatten and first_flat_sell is None:first_flat_sell=filled
        remaining=qty; gain=D(0)
        while remaining:
            if not fifo[symbol]: raise ValueError("unmatched sell or inherited strategy shares")
            lot=fifo[symbol][0];used=min(remaining,lot[0]);gain+=used*(price-lot[1])
            lot[0]-=used;remaining-=used
            if lot[0]==0:fifo[symbol].popleft()
        pnl+=gain;wins+=gain>0;losses+=gain<0
    if any(fifo.values()):raise ValueError("MBB filled inventory not flat")
    eligible=[r for r in records if r["when"].date()==day and r["when"]<=asof]
    before=[r for r in eligible if r.get("kind")=="guard" and flatten<=r["when"]<verification
            and r.get("flat_verified") is True and r.get("status")=="FLAT_IN_BROKER_SNAPSHOT"
            and r.get("overdue") is False]
    after=[r for r in eligible if r.get("kind")=="guard" and r["when"]>=verification
           and r.get("flat_verified") is True and r.get("status")=="FLAT_IN_BROKER_SNAPSHOT"
           and r.get("overdue") is False]
    independent=[r for r in eligible if r.get("kind")=="readback" and r["when"]>=verification
                 and r.get("broker_verified") is True and r.get("positions_count")==0
                 and r.get("open_orders_count")==0]
    if not(before and after and independent):
        raise ValueError("missing timely flat guard and independent post-14:00 readback")
    def fmt(x):return x.astimezone(CT).isoformat(timespec="seconds")
    return {
        "verification":"PAPER_DAILY_FLAT_CONFIRMED",
        "broker_snapshot_asof_ct":fmt(asof),
        "first_flat_guard_ct":fmt(min(r["when"] for r in before)),
        "post_1400_guard_ct":fmt(min(r["when"] for r in after)),
        "first_independent_post_1400_readback_ct":fmt(min(r["when"] for r in independent)),
        "last_mbb_fill_ct":fmt(last_fill) if last_fill else None,
        "first_mbb_flatten_fill_ct":fmt(first_flat_sell) if first_flat_sell else None,
        "mbb_filled_buys":sum(r[2]=="buy" for r in relevant),
        "mbb_filled_sells":sum(r[2]=="sell" for r in relevant),
        "winning_exits":wins,"losing_exits":losses,
        "gross_realized_paper_usd":str(pnl.quantize(D("0.01"))),
        "open_broker_positions":0,"open_broker_orders":0,
        "fee_adjusted_profit_known":False,"exclusive_strategy_ownership_proven":False,
        "new_strategy_approval":False,"research_submitted_orders":0
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--inventory",required=True)
    p.add_argument("--journal",required=True)
    p.add_argument("--day",required=True)
    a=p.parse_args()
    with open(a.inventory,encoding="utf-8") as f:s=json.load(f)
    with open(a.journal,encoding="utf-8") as f:r=parse_journal(f)
    print(json.dumps(audit(s,r,a.day),sort_keys=True))

if __name__=="__main__":main()
