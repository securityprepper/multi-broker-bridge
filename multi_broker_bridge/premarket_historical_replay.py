"""Broker-credential read-only, no-lookahead November 9 minute-bar entry study.

This reports historical trade-bar observations, NOT executable asks, fills or
prospectively proven profitability. Never sends, cancels or modifies orders.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import json
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from .auto_paper import _fetch_json,market_headers,DATA_HOST
CT=ZoneInfo("America/Chicago")
SIP_START=datetime(2026,11,9,3,0,tzinfo=CT)
SIP_END=datetime(2026,11,9,13,45,tzinfo=CT)
SYMBOLS=("AMD","MU","SNDK","NVDA","CRWD","PANW","PWR","CAT","GS","RBA",
         "ZS","GE","BA","JPM","BAC")
SOLD=("AMD",Decimal("466.00"),datetime(2026,11,9,7,37,tzinfo=CT))
FDR_SOLD=("AMD",Decimal("464.52"),datetime(2026,11,9,7,30,tzinfo=CT))
ANCHORS=("AMD","MU","SNDK")
SECTOR_ANCHORS={
    "AMD":("AMD","MU","SNDK"),"MU":("AMD","MU","SNDK"),
    "SNDK":("AMD","MU","SNDK"),"NVDA":("AMD","MU","SNDK"),
    "CRWD":("CRWD","PANW","ZS"),"PANW":("CRWD","PANW","ZS"),
    "CAT":("CAT","GE","BA"),"GS":("JPM","BAC","GS"),
    # Neither PWR nor RBA has a separately verified current sector anchor
    # group approved for automatic orders. Never invent one.
}

def bars(sym):
    query=urlencode({"symbols":sym,"timeframe":"1Min",
                     "start":SIP_START.astimezone(timezone.utc).isoformat(),
                     "end":SIP_END.astimezone(timezone.utc).isoformat(),
                     "feed":"sip","limit":"10000","sort":"asc"})
    payload=_fetch_json(DATA_HOST+"/v2/stocks/bars?"+query,
                        headers=market_headers(),timeout=12)
    if payload.get("next_page_token"):
        raise ValueError("Incomplete historical minute chart for "+sym)
    out=[]
    for b in payload.get("bars",{}).get(sym,[]):
        when=datetime.fromisoformat(b["t"].replace("Z","+00:00")).astimezone(CT)
        high,low,close=map(lambda x:Decimal(str(b[x])),("h","l","c"))
        volume=int(b["v"])
        if high<=0 or low<=0 or close<=0 or volume<=0:
            continue
        if not low<=close<=high:continue
        out.append({"dt":when,"high":high,"low":low,"close":close,"vol":volume})
    if len({b["dt"] for b in out})!=len(out):
        raise ValueError("Duplicate minute bars")
    return out

def rising(last4):
    if len(last4)<4:return False
    return (all(last4[i]["dt"]-last4[i-1]["dt"]<=timedelta(seconds=90)
                and last4[i]["high"]>last4[i-1]["high"]
                and last4[i]["low"]>last4[i-1]["low"]
                and (last4[i]["close"]-last4[i-1]["close"])/last4[i-1]["close"]<Decimal(".025")
                for i in range(1,4)) and
            last4[-1]["close"]>last4[0]["close"])

def completed_signal(rows,by_time,time):
    # Current candle must have closed at least a minute ago.
    finished=[b for b in rows if b["dt"]+timedelta(minutes=1)<=time]
    if len(finished)<4 or not rising(finished[-4:]):return None
    return finished[-1]

def minute_at(rows,time):
    eligible=[b for b in rows if b["dt"]+timedelta(minutes=1)<=time]
    return eligible[-1] if eligible else None

def main():
    data={s:bars(s) for s in SYMBOLS}
    out={}
    for sym in SYMBOLS:
        rows=data[sym]
        if not rows:
            out[sym]={"bars":0};continue
        signals=[]
        for idx in range(3,len(rows)):
            seq=rows[idx-3:idx+1]
            if not rising(seq):continue
            asof=seq[-1]["dt"]+timedelta(minutes=1)
            if asof.hour>10 or (asof.hour==10 and asof.minute>0):continue
            leader_confirmed=0
            for a in SECTOR_ANCHORS.get(sym,()):
                cutoff=[b for b in data[a] if b["dt"]+timedelta(minutes=1)<=asof]
                if len(cutoff)>=4 and rising(cutoff[-4:]):leader_confirmed+=1
            if leader_confirmed>=2:
                signals.append((asof,seq[-1]["close"],leader_confirmed))
        first=signals[0] if signals else None
        earliest_after_open=[x for x in signals
                             if x[0].hour*60+x[0].minute>=8*60+30]
        end=datetime(2026,11,9,13,40,tzinfo=CT)
        at_end=minute_at(rows,end)
        out[sym]={
            "historical_one_minute_bar_count":len(rows),
            "sector_anchors_used":list(SECTOR_ANCHORS.get(sym,())),
            "independent_sector_confirmation_available":bool(SECTOR_ANCHORS.get(sym)),
            "first_confirmed_rising_breadth_bar":(
                {"completed_at_CT":first[0].strftime("%H:%M"),
                 "minute_close_proxy":str(first[1]),
                 "three_anchor_confirmation_count":first[2]} if first else None),
            "first_after_0830_CT":(
                {"completed_at_CT":earliest_after_open[0][0].strftime("%H:%M"),
                 "minute_close_proxy":str(earliest_after_open[0][1])}
                if earliest_after_open else None),
            "last_bar_before_1340_CT":(
                {"at_CT":at_end["dt"].strftime("%H:%M"),
                 "close_proxy":str(at_end["close"])} if at_end else None)
        }
    for label,(sym,sale,time) in [("MBB",SOLD),("FDR",FDR_SOLD)]:
        ordered=data[sym]
        after=[b for b in ordered
               if b["dt"]+timedelta(minutes=1)>time and
               b["dt"]+timedelta(minutes=1)<datetime(2026,11,9,10,0,tzinfo=CT)]
        lower=[b for b in after if b["close"]<sale]
        qualifying=[]
        for row in after:
            asof=row["dt"]+timedelta(minutes=1)
            if not (row["close"]<sale*Decimal(".9975")):continue
            eligible=[b for b in ordered if b["dt"]+timedelta(minutes=1)<=asof]
            if len(eligible)<4 or not rising(eligible[-4:]):continue
            anchor_count=0
            for a in ANCHORS:
                anchor_recent=[b for b in data[a] if b["dt"]+timedelta(minutes=1)<=asof]
                if len(anchor_recent)>=4 and rising(anchor_recent[-4:]):anchor_count+=1
            if anchor_count>=2:qualifying.append((asof,row["close"]))
        out[label+"_AMD_REENTRY"]= {
            "prior_premarket_sell_CT":time.strftime("%H:%M"),
            "prior_sell_price":str(sale),
            "bars_below_prior_sell":len(lower),
            "earliest_completed_close_below_sell":lower[0]["dt"].strftime("%H:%M") if lower else None,
            "candidate_with_0_25_pct_discount_and_2of3_anchors_before10":(
                {"time_CT":qualifying[0][0].strftime("%H:%M"),
                 "bar_close_proxy":str(qualifying[0][1])} if qualifying else None),
        }
    print(json.dumps({"status":"READ_ONLY_HISTORICAL_MINUTE_REPLAY",
                      "symbols":out,"note":"minute bars only; no historical executable quotes; not actual entry fills",
                      "orders_submitted":0},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
