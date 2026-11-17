"""Read-only dashboard math. Missing evidence stays missing."""
from collections import defaultdict, deque
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math
UTC=timezone.utc
CT=ZoneInfo("America/Chicago")
def number(v):
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (TypeError,ValueError): return None
def instant(v):
    if isinstance(v,datetime): return v.replace(tzinfo=v.tzinfo or UTC)
    parsed=datetime.fromisoformat(str(v).replace("Z","+00:00"))
    return parsed.replace(tzinfo=parsed.tzinfo or UTC)
def movement(bars, now, prior_close=None, day_open=None):
    usable=sorted([(instant(b["t"]).timestamp(),number(b["c"])) for b in bars if number(b.get("c")) and instant(b["t"]).timestamp()+60<=now.timestamp()])
    if not usable: return {"price":None,"asof":None,"stale":True,"changes":{}}
    ts,price=usable[-1]
    fresh=0<=now.timestamp()-(ts+60)<=180
    changes={}
    for minutes in (1,5,10,20,30,60,120,240):
        target=ts-minutes*60
        old=[(t,p) for t,p in usable if 0<=target-t<=90]
        changes[str(minutes)]=round((price/old[-1][1]-1)*100,4) if fresh and old else None
    changes["day"]=round((price/prior_close-1)*100,4) if fresh and prior_close else None
    changes["open"]=round((price/day_open-1)*100,4) if fresh and day_open else None
    return {"price":price,"asof":datetime.fromtimestamp(ts+60,UTC).isoformat(),"stale":not fresh,"changes":changes}
def fifo_closed(executions, day, now):
    """Matched long lots only; exclude future fills, preserve missing entry basis."""
    lots=defaultdict(deque); closed=[]
    for e in sorted(executions,key=lambda x:(instant(x["time"]),str(x["id"]))):
        t=instant(e["time"])
        if t>now: continue
        q=number(e["qty"]); p=number(e["price"])
        if not q or not p or q<=0 or p<=0: continue
        key=(e["account"],e.get("instrument",e["symbol"]))
        fee=(number(e.get("fees")) or 0)/q
        if str(e["side"]).lower() in ("buy","bot"):
            lots[key].append([q,p,fee,e.get("source","Unattributed")])
        elif str(e["side"]).lower() in ("sell","sld"):
            left=q; matched=0; cost=0; pnl=0; sources=set()
            while left>1e-8 and lots[key]:
                lot=lots[key][0]; take=min(left,lot[0])
                matched+=take; cost+=take*lot[1]
                pnl+=take*(p-lot[1]-fee-lot[2]); sources.add(lot[3])
                lot[0]-=take; left-=take
                if lot[0]<1e-8: lots[key].popleft()
            if t.astimezone(CT).date().isoformat()==day:
                closed.append({"id":str(e["id"]),"account":e["account"],"broker":e["broker"],"paper":e["paper"],
                    "symbol":e["symbol"],"time":t.isoformat(),"qty":q,"matched_qty":matched,
                    "entry":cost/matched if matched else None,"exit":p,"pnl":round(pnl,4) if left<1e-8 else None,
                    "pct":round(pnl/cost*100,4) if cost and left<1e-8 else None,
                    "source":next(iter(sources)) if len(sources)==1 else ("Mixed sources" if sources else "Unattributed"),
                    "basis_status":"Matched FIFO; includes recorded fees" if left<1e-8 else "Entry history incomplete"})
    return closed

def remaining_sources(executions,account,symbol,quantity,now):
    lots=deque()
    for e in sorted(executions,key=lambda x:(instant(x["time"]),str(x["id"]))):
        if e["account"]!=account or e["symbol"]!=symbol or instant(e["time"])>now:continue
        q=number(e["qty"])
        if not q or q<=0:continue
        if e["side"].lower()=="buy":lots.append([q,e.get("source","Unattributed")])
        elif e["side"].lower()=="sell":
            while q>1e-8 and lots:
                take=min(q,lots[0][0]);q-=take;lots[0][0]-=take
                if lots[0][0]<1e-8:lots.popleft()
    total=sum(x[0] for x in lots)
    sources={x[1] for x in lots}
    return next(iter(sources)) if abs(total-quantity)<1e-6 and len(sources)==1 else "Unattributed"