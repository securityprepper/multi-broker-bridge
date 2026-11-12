"""Read-only post-exit continuation audit of broker-verified Alpaca PAPER lots.
SIP completed-minute trade closes are MARKS, never executable prices or fills.
Only the already authorized private local research cache is consumed. No API calls.
"""
from __future__ import annotations
import json
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
HORIZONS = (2, 5, 10, 30)
PRIVATE = Path("/tmp/v2-rapid-exit-run6-20261111/raw_research_private.json")

def local(t):
    return (t if isinstance(t, datetime) else datetime.fromisoformat(t)).astimezone(CT)

def ceil_minute(t):
    t = local(t)
    cut = t.replace(second=0, microsecond=0)
    return cut if t == cut else cut + timedelta(minutes=1)

def assess(trade, bars, minutes):
    exit_at = local(trade["exit_at"])
    end = ceil_minute(exit_at + timedelta(minutes=minutes))
    flat = datetime.fromisoformat(trade["day"] + "T13:40:00-06:00")
    if end >= flat:
        return {"status": "PAST_CAUSAL_FLAT_CUTOFF"}
    path = sorted((local(v["t"]), v) for v in bars)
    start = ceil_minute(exit_at)
    complete = {t: v for t, v in path if start <= t < end}
    expected = []
    cursor = start
    while cursor < end:
        expected.append(cursor)
        cursor += timedelta(minutes=1)
    if not expected or any(t not in complete for t in expected):
        return {"status": "MISSING_CONTIGUOUS_POST_EXIT_1M"}
    last = complete[end - timedelta(minutes=1)]
    mark = float(last["c"])
    if mark <= 0:
        return {"status": "BAD_TRADE_MARK"}
    qty = float(trade["qty"])
    gross_delta = (mark - float(trade["exit"])) * qty
    counterfactual = (mark - float(trade["entry"])) * qty
    cost_30bp = .003 * float(trade["entry"]) * qty
    # This is NOT hypothetical executable P&L: price marks lack executable bid,
    # as-of limit fill uncertainty, and actual fee information.
    return {"status": "COMPLETED_TRADE_BAR_MARK_ONLY",
            "mark_delta_vs_broker_exit_usd": gross_delta,
            "counterfactual_gross_vs_entry_usd": counterfactual,
            "counterfactual_after_assumed_30bp_usd": counterfactual-cost_30bp,
            "mark_return_after_exit_pct": 100*(mark/float(trade["exit"])-1)}

def aggregate(source):
    assert source["research_only"] is True and source["broker_orders_submitted"] == 0
    rows = source["trades"]
    result = {"scope":{"round_trips":len(rows),
                       "sessions":sorted({t["day"] for t in rows}),
                       "sources":dict(Counter(t["source"] for t in rows)),
                       "research_only":True,"orders_submitted":0,
                       "historical_buy_news_status":"NEWS_UNKNOWN_NOT_RESCREENED",
                       "price_basis":"SIP 1m completed trade close; not executable"},
              "horizons":{}}
    for minutes in HORIZONS:
        events=[]
        for trade in rows:
            key=trade["day"]+"|"+trade["symbol"]
            item=assess(trade,source["bars"].get(key,[]),minutes)
            item.update({"source":trade["source"],"day":trade["day"],
                         "rapid_10m":(local(trade["exit_at"])-local(trade["entry_at"])).total_seconds()<=600,
                         "exit_type":trade["exit_type"]})
            events.append(item)
        summary={}
        for group,selection in (("ALL",events),("RAPID_LE_10M",[v for v in events if v["rapid_10m"]]),
                                ("MBB",[v for v in events if v["source"]=="MBB"]),
                                ("FDR",[v for v in events if v["source"]=="FDR"])):
            usable=[v for v in selection if v["status"]=="COMPLETED_TRADE_BAR_MARK_ONLY"]
            summary[group]={
              "population":len(selection),"usable":len(usable),
              "unknown":dict(Counter(v["status"] for v in selection if v["status"]!="COMPLETED_TRADE_BAR_MARK_ONLY")),
              "later_mark_higher":sum(v["mark_delta_vs_broker_exit_usd"]>0 for v in usable),
              "later_mark_lower":sum(v["mark_delta_vs_broker_exit_usd"]<0 for v in usable),
              "later_mark_equal":sum(v["mark_delta_vs_broker_exit_usd"]==0 for v in usable),
              "later_mark_higher_at_least_0_30pct":sum(v["mark_return_after_exit_pct"]>=.30 for v in usable),
              "later_mark_lower_at_least_0_30pct":sum(v["mark_return_after_exit_pct"]<=-.30 for v in usable),
              "sum_mark_delta_vs_broker_exit_usd":round(sum(v["mark_delta_vs_broker_exit_usd"] for v in usable),2),
              "counterfactual_after_assumed_30bp_winners":sum(v["counterfactual_after_assumed_30bp_usd"]>0 for v in usable),
              "distinct_days_usable":len({v["day"] for v in usable})}
        result["horizons"][str(minutes)]=summary
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description="PAPER broker-fills post-exit completed minute research; no API calls")
    parser.add_argument("--input",default=str(PRIVATE))
    parser.add_argument("--output",default="/tmp/v2-rapid-exit-run7-postexit-summary-private.json")
    args=parser.parse_args(argv)
    source=json.loads(Path(args.input).read_text())
    output=aggregate(source)
    path=Path(args.output)
    if path.exists():
        raise RuntimeError("Refusing to overwrite research outcome file")
    path.write_text(json.dumps(output,indent=2,sort_keys=True))
    print(json.dumps(output,sort_keys=True))

if __name__=="__main__":
    main()
