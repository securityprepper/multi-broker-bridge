"""Offline, read-only compatibility audit for two-falling-bar MBB PAPER exits.

Never attributes actual cause without immutable decision/order-ID proof.
Does not place orders or write broker state.
"""
import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
ONE_MIN = timedelta(minutes=1)
START = time(8,30)
FLAT = time(13,40)

def when(s):
    return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(CT)

def two_falling(a,b,c):
    return b["h"]<a["h"] and b["l"]<a["l"] and c["h"]<b["h"] and c["l"]<b["l"]

def compatibility(trade, bars, lookback_seconds=180):
    entry_at=when(trade["entry_at"])
    exit_at=when(trade["exit_at"])
    if not START<=exit_at.time()<FLAT: return {"status":"NOT_RTH"}
    if trade["source"]!="MBB": return {"status":"NOT_MBB"}
    if float(trade["exit"])>=float(trade["entry"]): return {"status":"NOT_REALIZED_LOSS"}
    elapsed=(exit_at-entry_at).total_seconds()
    if not 0<elapsed<=600: return {"status":"NOT_RAPID_LE10M"}
    completed=sorted(
        ((when(b["t"])+ONE_MIN,b)
         for b in bars
         if entry_at<when(b["t"])+ONE_MIN<=exit_at),
        key=lambda x:x[0])
    if len(completed)<3: return {"status":"INSUFFICIENT_POST_ENTRY_BARS"}
    candidates=[]
    for i in range(2,len(completed)):
        (ta,a),(tb,b),(tc,c)=completed[i-2:i+1]
        if not 0<=(exit_at-tc).total_seconds()<=lookback_seconds:continue
        if tb-ta!=ONE_MIN or tc-tb!=ONE_MIN:continue
        if not two_falling(a,b,c):continue
        entry=float(trade["entry"]); close=float(c["c"])
        change=(close/entry-1)
        peak=max([entry]+[float(bb["h"]) for _,bb in completed[:i+1]])
        trail=close/peak-1
        if not -.01<change<0:continue
        # Respect higher-priority trailing reversal rather than asserting a two-bar cause.
        if peak>=entry*1.005 and trail<=-.005:continue
        candidates.append({"bars_ending_at_ct":tc.isoformat(),
              "age_before_actual_fill_s":round((exit_at-tc).total_seconds(),2),
              "change_at_bar_pct":round(100*change,4),
              "three_bar_close_move_pct":round(100*(close/float(a["c"])-1),4)})
    if not candidates:return {"status":"NO_EXCLUSIVE_COMPATIBLE_PATTERN_IN_WINDOW"}
    return {"status":"TWOBAR_COMPATIBLE_NOT_CAUSE_PROVEN","candidate":candidates[-1]}

def aggregate(source, quote_source=None):
    if source.get("broker_orders_submitted")!=0 or source.get("research_only") is not True:
        raise ValueError("requires prior read-only research cache")
    if not isinstance(source.get("trades"),list) or not isinstance(source.get("bars"),dict):
        raise ValueError("bad input")
    quotes=quote_source.get("quotes",{}) if quote_source else {}
    rows=[]
    for trade in source["trades"]:
        if trade["source"]!="MBB":continue
        result=compatibility(trade,source["bars"].get(trade["day"]+"|"+trade["symbol"],[]))
        if result["status"] in ("NOT_RTH","NOT_MBB","NOT_REALIZED_LOSS","NOT_RAPID_LE10M"):
            continue
        actual=(float(trade["exit"])-float(trade["entry"]))*float(trade["qty"])
        row={"day":trade["day"],"symbol":trade["symbol"],"status":result["status"],
             "actual_gross_usd":round(actual,2)}
        if "candidate" in result:row["candidate"]=result["candidate"]
        quote=quotes.get(trade["day"]+"|"+trade["symbol"],{})
        if quote.get("status")=="FRESH_TIGHT_INDICATIVE_QUOTE" and float(quote.get("bid_size",0))>=float(trade["qty"]):
            row["flat_bid_gross_mark_usd"]=round((float(quote["bid"])-float(trade["entry"]))*float(trade["qty"]),2)
        else:row["flat_bid_gross_mark_usd"]=None
        rows.append(row)
    hit=[x for x in rows if x["status"]=="TWOBAR_COMPATIBLE_NOT_CAUSE_PROVEN"]
    quotable=[x for x in hit if x["flat_bid_gross_mark_usd"] is not None]
    summary={
       "scope":"ONE_BROKER_VERIFIED_PAPER_ACCOUNT_ACCOUNT_ID_NOT_IN_CACHE",
       "method":"RTH MBB filled loss positions held <=10m; completed consecutive SIP 1m bars; compatible within <=180s of filled exit; NOT proof of decision reason",
       "news_asof":"NEWS_UNKNOWN_HISTORICAL_CONTROLS_ONLY",
       "eligible_sessions":sorted({x["day"] for x in rows}),
       "loss_rapid_rth":len(rows),
       "two_falling_compatible":len(hit),
       "other_or_insufficient":dict(Counter(x["status"] for x in rows if x not in hit)),
       "compatible_actual_gross_usd":round(sum(x["actual_gross_usd"] for x in hit),2),
       "compatible_with_fresh_flat_bid":len(quotable),
       "compatible_fresh_flat_bid_gross_mark_usd":round(sum(x["flat_bid_gross_mark_usd"] for x in quotable),2),
       "compatible_fresh_flat_bid_winners":sum(x["flat_bid_gross_mark_usd"]>0 for x in quotable),
       "compatible_fresh_flat_bid_losers":sum(x["flat_bid_gross_mark_usd"]<0 for x in quotable),
       "short_three_bar_move_under_0p10pct":sum(abs(x["candidate"]["three_bar_close_move_pct"])<0.1 for x in hit),
       "broker_orders_submitted":0,"research_only":True,
       "claim":"NO_GO; no causal exit attribution, quote is nonexecuted mark, missing 20+ independent days"}
    return {"summary":summary,"rows":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--flat-quotes")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    raw=json.load(open(args.input))
    quote=json.load(open(args.flat_quotes)) if args.flat_quotes else None
    result=aggregate(raw,quote)
    with open(args.output,"x") as f:json.dump(result,f,indent=2,sort_keys=True)
    print(json.dumps(result["summary"],sort_keys=True))

if __name__=="__main__":
    main()

