"""Off-hours GTC stop breach detection. No broker mutation capability."""
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
import math
ET=ZoneInfo("America/New_York")
ACTIVE={"new","accepted","pending_new","held","queued","confirmed","unconfirmed","partially_filled","submitted","presubmitted","apipending","pendingsubmit"}
def num(x):
    try:
        n=float(x)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None
def stamp(x):
    if isinstance(x,datetime): return x.replace(tzinfo=x.tzinfo or timezone.utc)
    d=datetime.fromisoformat(str(x).replace("Z","+00:00"))
    return d.replace(tzinfo=d.tzinfo or timezone.utc)
def fresh(x,now,seconds):
    try: return 0 <= (now-stamp(x)).total_seconds() <= seconds
    except (ValueError,TypeError,OverflowError): return False
def session(now):
    d=now.astimezone(ET); t=d.time(); w=d.weekday()
    if w<5 and time(9,30)<=t<time(16): return "REGULAR"
    if w<5 and time(4)<=t<time(9,30): return "PREMARKET"
    if w<5 and time(16)<=t<time(20): return "AFTERHOURS"
    if (w in (6,0,1,2,3) and t>=time(20)) or (w<5 and t<time(4)): return "OVERNIGHT"
    return "CLOSED"
def detect(positions,orders,quotes,now):
    """Only verified long equities and active unfilled sell GTC stop orders.
    Evidence TTL: 120s position/order, 90s completed-bar quote. Breach:
    max(one cent, five basis points). One row per native stop order.
    """
    if session(now) in ("REGULAR","CLOSED"): return []
    found=[]; seen=set()
    bykey={(p["account"],p["symbol"]):p for p in positions if not p.get("paper") and p.get("asset") in ("EQUITY","STK","STOCK") and (num(p.get("qty")) or 0)>0}
    for o in orders:
        key=(o.get("account"),o.get("symbol")); p=bykey.get(key)
        oid=(o.get("account"),o.get("id"))
        if not p or oid in seen or not o.get("id") or o.get("paper"): continue
        if str(o.get("side","")).lower() not in ("sell","sld"): continue
        if str(o.get("state","")).lower().replace(" ","") not in ACTIVE: continue
        if str(o.get("tif","")).lower() not in ("gtc","good_till_canceled","good_til_canceled"): continue
        stop=num(o.get("stop")); qty=num(o.get("qty")); filled=num(o.get("filled"))
        if not stop or stop<=0 or qty is None or filled is None or not 0<=filled<qty: continue
        if not fresh(o.get("asof"),now,120) or not fresh(p.get("position_asof"),now,120): continue
        q=quotes.get(p["symbol"],{}); price=num(q.get("price"))
        if not price or q.get("stale",True) or not fresh(q.get("asof"),now,90): continue
        threshold=max(.01,stop*.0005)
        if stop-price+1e-9<threshold: continue
        found.append({"id":str(o["id"]),"account":p["account"],"broker":p["broker"],"paper":False,
            "symbol":p["symbol"],"qty":min(num(p["qty"]),qty-filled),"stop":stop,"price":price,
            "below_pct":round((stop-price)/stop*100,4),"below_amount":round(stop-price,4),
            "price_asof":q["asof"],"order_asof":o["asof"],"position_asof":p["position_asof"],
            "session":session(now),"status":"REPORT ONLY — live closing disabled","detected_at":now.isoformat()})
        seen.add(oid)
    return found
def paper_exit_plan(account,position_qty,stop_order_qty,filled,quote_bid,quote_asof,now,original_terminal=False):
    """Pure plan used by paper commissioning. Never accepts a live account.
    Adapter must cancel/reconcile the native stop before calling with terminal=True.
    """
    if not (account.startswith("DU") or account.startswith("ALPACA_PAPER:")): raise ValueError("PAPER_ACCOUNT_REQUIRED")
    if not original_terminal: raise ValueError("NATIVE_STOP_NOT_TERMINAL")
    if not fresh(quote_asof,now,15): raise ValueError("STALE_BID")
    values=[num(v) for v in (position_qty,stop_order_qty,filled,quote_bid)]
    if any(v is None for v in values): raise ValueError("INVALID_NUMBER")
    pos,total,done,bid=values
    if pos<=0 or total<=0 or not 0<=done<total or bid<=0: raise ValueError("NO_LONG_REMAINDER")
    qty=min(pos,total-done)
    return {"side":"sell","qty":qty,"type":"limit","time_in_force":"day","extended_hours":True,
        "limit_price":round(bid*.999,2),"session":session(now),"live_enabled":False}