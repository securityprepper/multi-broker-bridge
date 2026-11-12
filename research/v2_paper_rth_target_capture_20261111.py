"""Historical PAPER fill/1Min SIP threshold audit; READ ONLY local research cache, NO HTTP/orders.
Conservative stop-first if intraminute target and stop both touch; high touch is not a fill.
"""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict, Counter
import json
import argparse
C=ZoneInfo("America/Chicago")
argp=argparse.ArgumentParser(description="Offline, non-executable PAPER target sensitivity")
argp.add_argument("--fills",required=True,help="locally authorized private paired fill/SIP cache")
argp.add_argument("--flat-quotes",required=True,help="locally authorized as-of SIP flat bid snapshots")
args=argp.parse_args()
D=json.load(open(args.fills))
if D.get("research_only") is not True or D.get("broker_orders_submitted")!=0:
    raise SystemExit("Unsupported input: require existing GET-only research cache")
BID=json.load(open(args.flat_quotes))["quotes"]
T=[.005,.01,.015,.02,.025,.03,.04,.05]
S=[.01,.02,.025]
def loc(t):return datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(C)
def next_start(dt):
    z=dt.replace(second=0,microsecond=0)
    return z if dt==z else z+timedelta(minutes=1)
def all_path(row):
    buy=loc(row["entry_at"])
    exit_=loc(row["exit_at"])
    start=next_start(buy)
    flat=buy.replace(hour=13,minute=40,second=0,microsecond=0)
    seen={}
    for b in D["bars"].get(row["day"]+"|"+row["symbol"],[]):
        ts=loc(b["t"])
        if start<=ts and ts+timedelta(minutes=1)<=flat:
            if ts in seen:raise ValueError("duplicate bar")
            seen[ts]=b
    wanted=int((flat-start).total_seconds()//60)
    series=[(start+timedelta(minutes=i),seen.get(start+timedelta(minutes=i))) for i in range(wanted)]
    return series, seen, flat
rows=[]
for tr in D["trades"]:
    series,seen,flat=all_path(tr)
    if not series:status="NO_AFTER_ENTRY_WINDOW"
    elif all(x is not None for _,x in series):status="FULL"
    else:status="GAPPED"
    entry=float(tr["entry"]); sell=float(tr["exit"]);q=float(tr["qty"])
    have=[b for _,b in series if b is not None]
    x={"source":tr["source"],"day":tr["day"],"symbol":tr["symbol"],"qty":q,
       "filled_entry":entry,"filled_exit":sell,"actual":round((sell-entry)*q,4),
       "status":status,"bars":len(have),"missing":len(series)-len(have),
       "high":max([float(b["h"]) for b in have],default=None),
       "completed_close_max":max([float(b["c"]) for b in have],default=None)}
    for tgt in T:
        k=f"{tgt:.4f}"
        x["touch_"+k]=any(float(b["h"])>=entry*(1+tgt) for b in have)
        x["close_"+k]=any(float(b["c"])>=entry*(1+tgt) for b in have)
    if status=="FULL":
        for stop in S:
            for target in T:
                label=f"target_{target:.4f}_stop_{stop:.4f}"
                event=None; px=None; event_at=None
                for ts,b in series:
                    lower=float(b["l"])<=entry*(1-stop)
                    upper=float(b["h"])>=entry*(1+target)
                    # stop first if both, even though true path is unknowable
                    if lower: event="STOP_FIRST";px=entry*(1-stop);event_at=ts;break
                    if upper:event="TARGET_TOUCH_NOT_PROOF_OF_FILL";px=entry*(1+target);event_at=ts;break
                if event is None:
                    quote=BID.get(tr["day"]+"|"+tr["symbol"],{})
                    if quote.get("status")=="FRESH_TIGHT_INDICATIVE_QUOTE" and quote.get("bid_size",0)>=q:
                        px=float(quote["bid"]);event="FLAT_INDICATIVE_SIP_BID";event_at=flat
                    else:event="FLAT_QUOTE_UNKNOWN"
                x[label]={"event":event,
                 "pnl_proxy":round((px-entry)*q-.003*entry*q,4) if px is not None else None,
                 "exit_at":event_at.isoformat() if event_at else None}
    rows.append(x)
print("SOURCE",len(rows),"distinct_days",sorted({r["day"] for r in rows}),
      "source_counts",dict(Counter(r["source"] for r in rows)),
      "continuity",dict(Counter(r["status"] for r in rows)))
for group,rr in [("ALL",rows),("MBB", [r for r in rows if r["source"]=="MBB"]),
 ("FDR", [r for r in rows if r["source"]=="FDR"]),
 ("RAPID_MBB", [r for r,tr in zip(rows,D["trades"]) if r["source"]=="MBB" and (loc(tr["exit_at"])-loc(tr["entry_at"])).total_seconds()<=600])]:
 print("GROUP",group,"total",len(rr),"full",sum(r["status"]=="FULL" for r in rr))
 for target in T:
    k=f"{target:.4f}"
    obs=[r for r in rr if r["high"] is not None]
    full=[r for r in rr if r["status"]=="FULL"]
    print(" target_pct",target*100,"OBSERVED_HIGH_TOUCH",sum(r["touch_"+k] for r in obs),"/",len(obs),
          "OBSERVED_COMPLETE_1MIN_CLOSE",sum(r["close_"+k] for r in obs),"/",len(obs),
          "FULLPATH_HIT",sum(r["touch_"+k] for r in full),"/",len(full))
 print(" STOP_FIRST_MODEL fullpath only, friction=0.30% entry notional, normal stop=1%")
 full=[r for r in rr if r["status"]=="FULL"]
 for target in T:
    res=[r[f"target_{target:.4f}_stop_{.01:.4f}"] for r in full]
    usable=[x for x in res if x["pnl_proxy"] is not None]
    print("  tgt",target*100,"stop_first",sum(x["event"]=="STOP_FIRST" for x in res),
          "target_touch",sum(x["event"]=="TARGET_TOUCH_NOT_PROOF_OF_FILL" for x in res),
          "flat_bid",sum(x["event"]=="FLAT_INDICATIVE_SIP_BID" for x in res),
          "unknown_flat",sum(x["event"]=="FLAT_QUOTE_UNKNOWN" for x in res),
          "net_proxy_if_target_limit_fills",round(sum(x["pnl_proxy"] for x in usable),2),
          "wins",sum(x["pnl_proxy"]>0 for x in usable),"/",len(usable))
# no private IDs/rows in sanitized output
