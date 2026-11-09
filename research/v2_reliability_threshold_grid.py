"""V2 only: timestamp-causal 52-week sector-linked emergency threshold precision stress.

Reads local adjusted Alpaca SIP 5-minute candles read-only. NO broker/network/order code.
Labels use completed session outcomes only AFTER the signal is generated.
Signals use completed candles and strictly prior RTH closes; no EOD leakage.
A 5-minute next-bar opening mark is NOT a verified executable extended-hours fill.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import datetime, time, timedelta
from math import sqrt
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

ET=ZoneInfo("America/New_York")
FIRST_RTH=time(9,30); LAST_RTH=time(15,55)
RAW_INPUTS=(
    "/tmp/semis_52wk_5min_sip_adjusted.json",
    "/tmp/semis_peers_52wk_5min_adjusted.json",
)
THRESHOLDS=(2.0,2.5,3.0)
FIVE_MINUTES=timedelta(minutes=5)
FIFTEEN_MINUTES=timedelta(minutes=15)

def minute_close_at_or_before(history, timestamp, max_age_minutes=5):
    """Use only already-completed price observations. 'timestamp' is decision time."""
    for minutes_back in range(max_age_minutes+1):
        t=timestamp-timedelta(minutes=minutes_back)
        value=history.get(t)
        if value is not None and t+FIVE_MINUTES<=timestamp:
            return value
    return None

def threshold_met(previous_close, current_close, close_15min_ago,
                  minimum_total_pct, minimum_15m_pp, side):
    """The recent 15-minute decline is INCLUDED in the total decline."""
    if not previous_close or not current_close or not close_15min_ago:
        return False
    total=(current_close/previous_close-1)*100
    delta15=(current_close-close_15min_ago)/previous_close*100
    sign=1 if side=="up" else -1
    return total*sign + 1e-9 >= minimum_total_pct and delta15*sign + 1e-9 >= minimum_15m_pp

def wilson_lower(successes, n, z=1.96):
    """95% lower confidence bound for signal/trade event precision."""
    if n<=0:return 0.0
    p=successes/n; z2=z*z
    return (p+z2/(2*n)-z*sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)

def classify_day(previous_close, opening, regular_close):
    """Outcome-only classification; never passed as a live signal feature."""
    total=(regular_close/previous_close-1)*100
    intraday=(regular_close/opening-1)*100
    return {"severe_down": min(total,intraday)<=-5,
            "severe_up": max(total,intraday)>=5,
            "total_pct":round(total,4),"rth_pct":round(intraday,4)}

def to_decision_map(raw_inputs):
    sessions=defaultdict(dict)
    all_symbols=set()
    for path in raw_inputs:
        raw=json.load(open(path))
        for symbol, observations in raw.items():
            all_symbols.add(symbol)
            for ts, candle in observations.items():
                stamp=datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(ET)
                # Timestamp denotes the START of its 5-minute candle.
                session_key=(symbol,stamp.date().isoformat())
                sessions[session_key][stamp]=(float(candle[0]),float(candle[3]))
    return sessions,sorted(all_symbols)

def build_rows(sessions, symbols):
    """Build each day's observations with previous COMPLETED session close only."""
    previous={}
    rows=[]
    # Sort chronologically across symbols, so previous closings cannot be same-day.
    for (sym,day), bars in sorted(sessions.items(),key=lambda a:(a[0][1],a[0][0])):
        rth=[(stamp,v) for stamp,v in sorted(bars.items()) if FIRST_RTH<=stamp.time()<=LAST_RTH]
        if len(rth)<60 or rth[-1][0].time()<time(15,45):
            continue
        prior=previous.get(sym)
        if prior is not None and prior[0]<day:
            opening=rth[0][1][0];closing=rth[-1][1][1]
            outcome=classify_day(prior[1],opening,closing)
            rows.append({"sym":sym,"day":day,"prior":prior[1],"rth_open":opening,
                         "rth_close":closing,"bars":bars,"outcome":outcome})
        previous[sym]=(day,rth[-1][1][1])
    return rows

def breadth_confirm(signal_symbol, day, decision_time, direction,
                    sessions, previous_close_by_sym, all_symbols):
    """Require point-in-time SOXX and >=half of OTHER peer stock changes in direction.

    Confirming data MUST be as-of completed bars; no future candle or final close.
    Previous closes must be from prior completed sessions, not today's close.
    """
    sign=1 if direction=="up" else -1
    available=[]
    for peer in all_symbols:
        if peer in ("SOXX",signal_symbol):
            continue
        prev=previous_close_by_sym.get(peer)
        if not prev:
            continue
        bars=sessions.get((peer,day),{})
        p=minute_close_at_or_before({ts:pair[1] for ts,pair in bars.items()},decision_time)
        if p is not None:
            available.append(sign*(p/prev-1)*100)
    soxxprev=previous_close_by_sym.get("SOXX")
    soxx_price=minute_close_at_or_before(
        {ts:pair[1] for ts,pair in sessions.get(("SOXX",day),{}).items()},decision_time)
    if soxxprev is None or soxx_price is None or len(available)<5:
        return False
    soxx_move=sign*(soxx_price/soxxprev-1)*100
    # No future-based sector labels; half of contemporaneous peers changing >=0.5pp.
    return soxx_move>=.5 and sum(x>=.5 for x in available)*2>=len(available)

def first_signal(row, threshold, direction, confirm, sessions, prior_map, symbols,
                 end_by=time(15,55)):
    """First STRICT 15m momentum signal; as-of close of completed 5m candle."""
    previous=row["prior"]
    # 5m bar timestamp indicates its start, so 'decision_time' is at its END.
    close_bars={ts:pair[1] for ts,pair in row["bars"].items()}
    for ts, price in sorted(close_bars.items()):
        if ts.time()<time(4,0) or ts.time()>end_by:continue
        earlier=close_bars.get(ts-FIFTEEN_MINUTES)
        if not threshold_met(previous,price,earlier,threshold,1.0,direction):
            continue
        decision_time=ts+FIVE_MINUTES
        if confirm and not breadth_confirm(row["sym"],row["day"],decision_time,
                                           direction,sessions,prior_map,symbols):
            continue
        return {"when":decision_time.isoformat(),"price":price,
                "last_total_pp":round((price/previous-1)*100,4),
                "last_15m_pp":round((price-earlier)/previous*100,4),
                "bar_start":ts}
    return None

def run(raw_paths=RAW_INPUTS):
    sessions,symbols=to_decision_map(raw_paths)
    rows=build_rows(sessions,symbols)
    rowlookup={(r["day"],r["sym"]):r for r in rows}
    days=sorted({r["day"] for r in rows})
    output={"input_sources":list(raw_paths),"stock_days":len(rows),
            "days":len(days),"symbols":symbols,
            "severe_down":sum(r["outcome"]["severe_down"] for r in rows),
            "severe_up":sum(r["outcome"]["severe_up"] for r in rows),
            "thresholds":[],"not_verified":[
                "Actual SIP/BOATS executable bid-ask quotes and fill eligibility",
                "Preceding-evening news, economic releases and synchronized futures observations",
                "Non-semiconductor sector cohorts and matched V1 fills"],
            "interpretation":"Signals are as-of 5m prices; classifications and next-open marks are retrospective outcome-only."}
    # as-of previous completed regular closes per symbol, day
    prior_maps=defaultdict(dict)
    for r in rows:
        prior_maps[r["day"]][r["sym"]]=r["prior"]
    # The NEXT session's opening price is an outcome only, NEVER a live feature.
    next_rth_open={}
    by_sym=defaultdict(list)
    for row in rows:by_sym[row["sym"]].append(row)
    for sym,history in by_sym.items():
        history.sort(key=lambda x:x["day"])
        for prior_row,next_row in zip(history,history[1:]):
            next_rth_open[(prior_row["day"],sym)]=next_row["rth_open"]
    output["prior_close_severe_down"]=sum(r["outcome"]["total_pct"]<=-5 for r in rows)
    output["prior_close_severe_up"]=sum(r["outcome"]["total_pct"]>=5 for r in rows)
    output["rth_severe_down"]=sum(r["outcome"]["rth_pct"]<=-5 for r in rows)
    output["rth_severe_up"]=sum(r["outcome"]["rth_pct"]>=5 for r in rows)
    # Exclude incomplete days from comparisons: valid prior full close and current close both present.
    for threshold in THRESHOLDS:
        for direction in ("down","up"):
            for sector_confirm in (False,True):
                signals=[]
                for r in rows:
                    s=first_signal(r,threshold,direction,sector_confirm,
                                   sessions,prior_maps[r["day"]],symbols)
                    if not s:continue
                    flags=r["outcome"]
                    severe=flags["severe_"+direction]
                    # Is the price decline/gain already at 5% when first warned?
                    early=abs(s["last_total_pp"])<5
                    cutoff=datetime.fromisoformat(s["when"])
                    preopen=cutoff.time()<time(9,30)
                    # The signal bar is closed. Assume first tradeable price mark on NEXT 5m bar:
                    nextbar=r["bars"].get(s["bar_start"]+FIVE_MINUTES)
                    nextprice=nextbar[0] if nextbar else None
                    # Hypothetical mark vs RTH close/next RTH OPEN when available.
                    signals.append({"sym":r["sym"],"day":r["day"],"when":s["when"],
                        "side":direction,"severe":severe,"early":early,"preopen":preopen,
                        "price_pct":s["last_total_pp"],"15m_pp":s["last_15m_pp"],
                        "nextbar_mark":nextprice,"rth_close":r["rth_close"],
                        "next_rth_open":next_rth_open.get((r["day"],r["sym"])),
                        "total_day_pct":flags["total_pct"],"rth_day_pct":flags["rth_pct"]})
                hits=sum(x["severe"] for x in signals)
                false=len(signals)-hits
                denom=output["severe_"+direction]
                early=sum(x["severe"] and x["early"] for x in signals)
                preopen=sum(x["severe"] and x["preopen"] for x in signals)
                periodresult=[]
                for cohort,period in [("earlier",lambda day:day<"2026-09-01"),
                                      ("later",lambda day:day>="2026-09-01")]:
                    xs=[s for s in signals if period(s["day"])]
                    cohort_hits=sum(s["severe"] for s in xs)
                    # Gross return vs same-day RTH close at NEXT 5m bar open, with 30bp assumed round-trip.
                    vals=[]; overnight_vals=[]; vals_by_day=defaultdict(list)
                    for s in xs:
                        p=s["nextbar_mark"]
                        if p:
                            raw=100*(s["rth_close"]/p-1)
                            trade_ret=(raw if direction=="up" else -raw)-.30
                            vals.append(trade_ret)
                            vals_by_day[s["day"]].append(trade_ret)
                            if s["next_rth_open"]:
                                change=100*(s["next_rth_open"]/p-1)
                                overnight_vals.append((change if direction=="up" else -change)-.30)
                    periodresult.append({"cohort":cohort,"count":len(xs),"major_hits":cohort_hits,
                        "others":len(xs)-cohort_hits,
                        "modeled_to_rth_close_avg_net_pct":round(mean(vals),4) if vals else None,
                        "modeled_win_fraction_to_close":round(sum(x>0 for x in vals)/len(vals),4) if vals else None,
                        "modeled_win_lower95_to_close":round(wilson_lower(sum(x>0 for x in vals),len(vals)),4) if vals else None,
                        "independent_signal_days":len(vals_by_day),
                        "day_equal_avg_net_pct":round(mean([mean(a) for a in vals_by_day.values()]),4) if vals_by_day else None,
                        "modeled_to_next_open_avg_net_pct":round(mean(overnight_vals),4) if overnight_vals else None,
                        "modeled_win_fraction_to_next_open":round(sum(x>0 for x in overnight_vals)/len(overnight_vals),4) if overnight_vals else None,
                        "modeled_next_open_count":len(overnight_vals),
                        "modeled_count":len(vals)})
                # Exact earliest severe hit and a few misses; do not claim best/selected approach.
                major_days={(r["day"],r["sym"]) for r in rows if r["outcome"]["severe_"+direction]}
                detected={(s["day"],s["sym"]) for s in signals if s["severe"]}
                missing=sorted(major_days-detected)
                signals_sorted=sorted((s for s in signals if s["severe"]),key=lambda s:s["when"])
                output["thresholds"].append({"threshold_pct":threshold,"last15min_pp":1.0,
                    "direction":direction,"sector_confirmation":sector_confirm,
                    "signals":len(signals),"major_detected":hits,
                    "major_total":denom,"other_warnings":false,
                    "hit_rate_of_signals":round(hits/len(signals),4) if signals else None,
                    "hit_precision_lower95":round(wilson_lower(hits,len(signals)),4) if signals else None,
                    "recall_major":round(hits/denom,4) if denom else None,
                    "early_before_5pct":early,"major_preopen":preopen,
                    "earliest_severe_hit":signals_sorted[0] if signals_sorted else None,
                    "missed_examples":missing[:8],"unwarned_major":len(missing),
                    "earlier_later":periodresult})
    return output

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    result=run()
    Path(args.out).write_text(json.dumps(result,indent=2,default=str)+"\n")
    print(json.dumps({"stock_days":result["stock_days"],"severe_down":result["severe_down"],
        "severe_up":result["severe_up"],"thresholds":[
            {k:row[k] for k in ("threshold_pct","direction","sector_confirmation","major_detected","major_total","other_warnings","hit_rate_of_signals","major_preopen","early_before_5pct")}
            for row in result["thresholds"]]},indent=2))
