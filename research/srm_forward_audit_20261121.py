#!/usr/bin/env python3
"""Read-only retrospective sustained-riser forward audit, no trading actions.

Source: immutable native SRM events; Alpaca historical SIP and BOATS 1m bars.
Purpose: descriptive post-alert price paths, NOT simulated fills or strategy GO.
"""
from __future__ import annotations
import bisect
import csv
import datetime as dt
import json
import math
import re
import statistics
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

UTC = dt.timezone.utc
CT = ZoneInfo("America/Chicago")
DAY = dt.date(2026, 11, 20)
GATE = Path("/var/cache/securityprepper-holiday/task-gate.json")
EVENTS = Path(f"/var/lib/securityprepper-sustained-riser-monitor/sustained-alerts-{DAY}.jsonl")
LEDGER = Path("/var/lib/securityprepper-sustained-riser-monitor/chatgpt-hourly-sent-events.jsonl")
CREDS = Path("/etc/securityprepper/alpaca-feed/private")
OUT = Path("/tmp/srm-forward-audit-20261121")
OUT.mkdir(mode=0o700, parents=True, exist_ok=True)

def parse_ts(s):
    t = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("NAIVE_TIME")
    return t.astimezone(UTC)

def check_gate():
    j = json.loads(GATE.read_text())
    n = dt.datetime.now(UTC)
    valid = (j.get("schema_version")==1 and j.get("status_valid") is True
        and j.get("timezone")=="America/Chicago"
        and j.get("calendar_coverage_ok") is True
        and j.get("paused") is False
        and parse_ts(j["published_at"])<=n<parse_ts(j["valid_until"])
        and n<parse_ts(j["next_check_at"])
        and j.get("calendar_coverage_through","")>=n.astimezone(CT).date().isoformat())
    if not valid:
        raise RuntimeError("TRUSTED_HOLIDAY_GATE_CLOSED_OR_UNVERIFIED")
    return {"asof":n.isoformat(), "calendar_revision":j.get("calendar_revision")}

def pct(current, base):
    return round((current/base - 1)*100, 4) if base and base>0 and math.isfinite(current) else None

def text_before(s):
    matches = re.findall(r"\b(5m|10m|30m|1h)\s+([+-]?\d+(?:\.\d+)?)%",s)
    return {k:float(v) for k,v in matches}

def fetch_bars(symbols, feed, start, end, headers):
    bars = {s:[] for s in symbols}
    req = 0
    for batch_start in range(0,len(symbols),8):
        subset = symbols[batch_start:batch_start+8]
        token = None
        seen = set()
        for page_no in range(25):
            args = {
                "symbols":",".join(subset),"timeframe":"1Min",
                "start":start.isoformat(),"end":end.isoformat(),
                "feed":feed,"adjustment":"split","sort":"asc","limit":10000
            }
            if token: args["page_token"]=token
            q = "https://data.alpaca.markets/v2/stocks/bars?" + urlencode(args)
            with urlopen(Request(q,headers=headers,method="GET"),timeout=22) as response:
                body = json.load(response)
            req += 1
            if not isinstance(body.get("bars"),dict):
                raise ValueError("MALFORMED_VENDOR_BARS")
            for sym,rows in body["bars"].items():
                if sym in bars:
                    bars[sym].extend(rows)
            new_token = body.get("next_page_token")
            if not new_token:
                break
            if new_token in seen:
                raise ValueError("REPEATED_PAGE_TOKEN")
            seen.add(new_token)
            token = new_token
        else:
            raise ValueError("VENDOR_PAGINATION_INCOMPLETE")
    return bars,req

def valid_bar_items(raw,feed):
    unique = {}
    for a in raw:
        try:
            t=parse_ts(a["t"])
            close=float(a["c"])
            volume=float(a.get("v",0))
            if volume<=0 or close<=0 or not math.isfinite(close):continue
            key=t+dt.timedelta(minutes=1)
            if key in unique and unique[key]["price"]!=close:
                raise ValueError("CONFLICTING_DUPLICATE_COMPLETED_BAR")
            unique[key]={"time":key,"price":close,"volume":volume,"feed":feed}
        except (KeyError,ValueError,TypeError):
            continue
    return list(unique.values())

def first_close_after(points, target, max_delay_s=125):
    # First completed, actual-volume bar ON or AFTER horizon; no stale carry.
    if not points:
        return None
    times=[x["time"] for x in points]
    i=bisect.bisect_left(times,target)
    if i==len(points):return None
    b=points[i]
    if (b["time"]-target).total_seconds()>max_delay_s:return None
    return dict(b)

def last_close_before(points,target,max_age_s=125):
    if not points:return None
    times=[x["time"] for x in points]
    i=bisect.bisect_right(times,target)-1
    if i<0:return None
    b=points[i]
    if (target-b["time"]).total_seconds()>max_age_s:return None
    return dict(b)

def sample(points,target,midprice,max_delay=125):
    b=first_close_after(points,target,max_delay)
    if b is None:return {"target_utc":target.isoformat(),"status":"NO_FRESH_COMPLETED_1M_TRADE","return_pct":None}
    return {"target_utc":target.isoformat(),
            "observed_utc":b["time"].isoformat(),"feed":b["feed"],
            "volume":b["volume"],"trade_close":b["price"],
            "return_pct":pct(b["price"],midprice),"status":"OBSERVED_1M_TRADE"}

def main():
    gate=check_gate()
    raw=[json.loads(l) for l in EVENTS.read_text().splitlines() if l.strip()]
    seen=set();events=[]
    for e in raw:
        if e.get("hour") not in (1,2,3,4,5,6,7,8,9,10):continue
        key=(e.get("symbol"),e.get("first_trend_at_utc"),e.get("hour"))
        if key in seen:continue
        seen.add(key)
        if parse_ts(e["issued_at_utc"]).astimezone(CT).date()!=DAY:continue
        mid=float(e.get("price") or 0)
        if not math.isfinite(mid) or mid<5:continue
        events.append(e)
    events.sort(key=lambda e:e["issued_at_utc"])
    symbols=sorted({e["symbol"] for e in events})
    print("AUTHORIZATION",gate,"events",len(events),"symbols",len(symbols),flush=True)
    headers={"APCA-API-KEY-ID":(CREDS/"alpaca_data_key_id").read_text().strip(),
             "APCA-API-SECRET-KEY":(CREDS/"alpaca_data_secret").read_text().strip()}
    start=parse_ts("2026-11-19T20:45:00Z")
    end=parse_ts("2026-11-21T06:00:00Z")
    whole={s:[] for s in symbols}
    reqs={}
    for feed in ("sip","boats"):
        check_gate()  # fail-closed before each vendor network batch
        returned,requests=fetch_bars(symbols,feed,start,end,headers)
        reqs[feed]=requests
        for sym,entries in returned.items():
            whole[sym].extend(valid_bar_items(entries,feed))
        print("FEED",feed,"requests",requests,"bars_total",sum(len(x) for x in returned.values()),flush=True)
    for sym in whole:
        by_time={}
        for b in whole[sym]:
            if b["time"] in by_time:
                # The two feeds never ought to overlap; do not claim conflict resolution.
                if b["price"]!=by_time[b["time"]]["price"]: raise ValueError("FEED_OVERLAP_CONFLICT")
            else:by_time[b["time"]]=b
        whole[sym]=sorted(by_time.values(),key=lambda b:b["time"])
    previous_rth=parse_ts("2026-11-19T21:00:00Z")
    midnight_start=parse_ts("2026-11-20T06:00:00Z")
    rth_close=parse_ts("2026-11-20T21:00:00Z")
    afterhours_close=parse_ts("2026-11-21T01:00:00Z")
    next_midnight=parse_ts("2026-11-21T06:00:00Z")
    by_key={}
    for l in LEDGER.read_text().splitlines():
        if not l.strip():continue
        a=json.loads(l)
        key=(a.get("symbol"),a.get("first_trend_at_utc"),a.get("hour"))
        by_key.setdefault(key,[]).append(a)
    outcomes=[]
    hourly=[]
    for e in events:
        sym=e["symbol"];mid=float(e["price"]);t=parse_ts(e["issued_at_utc"])
        key=(sym,e["first_trend_at_utc"],e["hour"])
        before=text_before(e.get("text",""))
        ref_previous=last_close_before(whole[sym],previous_rth,125)
        ref_midnight=first_close_after(whole[sym],midnight_start,600)
        refs={
            "previous_rth_close": {
                "price":ref_previous["price"],"source":ref_previous["feed"],"observed_utc":ref_previous["time"].isoformat()
            } if ref_previous else None,
            "first_trade_near_midnight": {
                "price":ref_midnight["price"],"source":ref_midnight["feed"],"observed_utc":ref_midnight["time"].isoformat(),
                "delay_from_midnight_seconds":(ref_midnight["time"]-midnight_start).total_seconds()
            } if ref_midnight else None,
        }
        row={
            "event_id":next((a.get("source_event_id") for a in by_key.get(key,[]) if a.get("source_event_id")),None),
            "ticker":sym,"hour":e["hour"],
            "instrument_note":"LEVERAGED_INVERSE_ETF_INELIGIBLE" if sym=="MUZ" else ("UNLEVERAGED_SECTOR_ETF" if sym=="SOXX" else "ORDINARY_STOCK_UNVERIFIED_CLASS"),
            "continuous_episode_start_utc":e["first_trend_at_utc"],
            "native_signal_issued_utc":t.isoformat(),"native_signal_chicago":t.astimezone(CT).isoformat(),
            "native_alert_price_mid":mid,"native_quote_source":("SIP_NBBO_MID_AS_RECORDED" if "SIP quote midpoint" in e.get("text","") else "SOURCE_COMPLETED_1M_BAR_CLOSE"),
            "native_route_status":e.get("route_status"),
            "trigger":"SOURCE_VERIFIED_60M: 61 completed positive-volume 1m bars, >=9 rising 5m intervals, 4/4 positive 15m segments, 60m change >+1.5%; nonmonotone minute bars possible",
            "before_5m_pct":before.get("5m"),"before_10m_pct":before.get("10m"),
            "before_30m_pct":before.get("30m"),"before_1h_pct":before.get("1h"),
            "since_prev_rth_close_pct":pct(mid,ref_previous["price"]) if ref_previous else None,
            "since_midnight_pct":pct(mid,ref_midnight["price"]) if ref_midnight else None,
            "references":refs,
            "chatgpt_report_prepared_utc":next((a.get("report_handoff_at_utc") for a in by_key.get(key,[]) if a.get("report_handoff_at_utc")),None),
            "forward_from_native_event_mid_not_fill":{},
        }
        for minutes in (5,10,30,60):
            target=t+dt.timedelta(minutes=minutes)
            row["forward_from_native_event_mid_not_fill"][f"+{minutes}m"]=sample(whole[sym],target,mid) if target<=next_midnight else None
        for label,target in [("RTH_CLOSE",rth_close),("AFTERHOURS_CLOSE_7PM_CT",afterhours_close),("MIDNIGHT_FOLLOWING_DAY",next_midnight)]:
            if target<=t:
                row["forward_from_native_event_mid_not_fill"][label]={"target_utc":target.isoformat(),"status":"BEFORE_OR_AT_NATIVE_ALERT","return_pct":None}
            elif label=="MIDNIGHT_FOLLOWING_DAY":
                # Midnight cannot be claimed with 19:00-24:00 carry; require a real close +/- 2m.
                result=sample(whole[sym],target,mid,120)
                if result["status"]=="NO_FRESH_COMPLETED_1M_TRADE":
                    result["status"]="NO_VERIFIED_MIDNIGHT_TRADE; DO_NOT_CARRY_FORWARD_EARLIER_PRICE"
                row["forward_from_native_event_mid_not_fill"][label]=result
            else:
                # Session close: latest completed minute ending AT or just before the actual close.
                close=last_close_before(whole[sym],target,125)
                row["forward_from_native_event_mid_not_fill"][label]={
                    "target_utc":target.isoformat(),"observed_utc":close["time"].isoformat(),
                    "trade_close":close["price"],"feed":close["feed"],"return_pct":pct(close["price"],mid),
                    "status":"OBSERVED_1M_TRADE"
                } if close else {"target_utc":target.isoformat(),"status":"NO_FRESH_COMPLETED_1M_TRADE","return_pct":None}
        h=1
        while t+dt.timedelta(hours=h)<=next_midnight:
            target=t+dt.timedelta(hours=h)
            result=sample(whole[sym],target,mid)
            hourly.append({"event_ticker":sym,"episode_start_utc":e["first_trend_at_utc"],"native_issued_utc":t.isoformat(),
                "hours_after_alert":h,"requested_horizon_ct":target.astimezone(CT).isoformat(),**result})
            h+=1
        row["available_completed_bars"]={
            "count":len(whole[sym]),
            "first_utc":whole[sym][0]["time"].isoformat() if whole[sym] else None,
            "last_utc":whole[sym][-1]["time"].isoformat() if whole[sym] else None}
        outcomes.append(row)
    summary={"day":str(DAY),"method":"Indicative native source quote midpoint (or completed 1m bar) to future completed 1m SIP/BOATS split-adjusted trade close; not broker execution or after-fee P/L",
         "time_anchor":"native SRM issued_at_utc (not later ChatGPT report handoff)",
         "previous_rth_close_reference":"Nov 19 15:00 America/Chicago",
         "midnight_reference":"First real completed BOATS 1m close within 10 minutes of 00:00 America/Chicago (actual time labeled)",
         "rth_close":"Nov 20 15:00 America/Chicago","afterhours_close":"Nov 20 19:00 America/Chicago",
         "end_midnight":"Nov 21 00:00 America/Chicago",
         "trigger":"verifiable continuous 60m rising, >=1.5%; episode start and original signed 5m/10m/30m/1h retained",
         "vendor_requests":reqs,"event_total":len(outcomes),"distinct_symbols":len(symbols),
         "signal_hour_counts":dict(Counter(row["hour"] for row in outcomes)),
         "group_statistics":{}}
    for group,subset in [
        ("all_historical_source_events",outcomes),
        ("ordinary_stock_only",[r for r in outcomes if r["instrument_note"]=="ORDINARY_STOCK_UNVERIFIED_CLASS"]),
        ("unleveraged_ETF_only",[r for r in outcomes if r["instrument_note"]=="UNLEVERAGED_SECTOR_ETF"]),
        ("excluded_leveraged_inverse",[r for r in outcomes if r["instrument_note"]=="LEVERAGED_INVERSE_ETF_INELIGIBLE"])
    ]:
        s={}
        for horizon in ("+5m","+10m","+30m","+60m","RTH_CLOSE","AFTERHOURS_CLOSE_7PM_CT","MIDNIGHT_FOLLOWING_DAY"):
            vals=[r["forward_from_native_event_mid_not_fill"][horizon]["return_pct"] for r in subset
                  if isinstance(r["forward_from_native_event_mid_not_fill"].get(horizon),dict)
                  and r["forward_from_native_event_mid_not_fill"][horizon].get("return_pct") is not None]
            s[horizon]={"eligible":len(subset),"observed":len(vals),"positive":sum(v>0 for v in vals),
                        "negative":sum(v<0 for v in vals),"zero":sum(v==0 for v in vals),
                        "mean_pct":round(statistics.mean(vals),4) if vals else None,
                        "median_pct":round(statistics.median(vals),4) if vals else None}
        summary["group_statistics"][group]=s
    pjson=OUT/"audit-nov20.json"
    pjson.write_text(json.dumps({"summary":summary,"events":outcomes,"hourly":hourly},indent=2,sort_keys=True)+"\n")
    flat=[]
    for row in outcomes:
        o={k:v for k,v in row.items() if k not in ("forward_from_native_event_mid_not_fill","references","available_completed_bars")}
        for label,v in row["forward_from_native_event_mid_not_fill"].items():
            o[label+"_pct"]=v.get("return_pct") if isinstance(v,dict) else None
            o[label+"_status"]=v.get("status") if isinstance(v,dict) else "AFTER_MIDNIGHT"
        o["previous_close_source_time"]=row["references"]["previous_rth_close"]["observed_utc"] if row["references"]["previous_rth_close"] else None
        o["midnight_baseline_source_time"]=row["references"]["first_trade_near_midnight"]["observed_utc"] if row["references"]["first_trade_near_midnight"] else None
        flat.append(o)
    with (OUT/"audit-nov20-summary.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    with (OUT/"audit-nov20-hourly.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(hourly[0]));w.writeheader();w.writerows(hourly)
    (OUT/"audit-nov20-statistics.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print("RESULT_DIR",OUT)
    print("STATS",json.dumps(summary["group_statistics"]["ordinary_stock_only"],sort_keys=True),flush=True)
    print("MISSING_MIDNIGHT",sum(r["forward_from_native_event_mid_not_fill"]["MIDNIGHT_FOLLOWING_DAY"]["return_pct"] is None for r in outcomes))
    print("HOURLY_ROWS",len(hourly),"KNOWN",sum(r["return_pct"] is not None for r in hourly))
    for e in outcomes[:6]+outcomes[-6:]:
        f=e["forward_from_native_event_mid_not_fill"]
        print("EXAMPLE",e["ticker"],e["native_signal_chicago"],
              "prev",e["since_prev_rth_close_pct"],"midnight_start",e["since_midnight_pct"],
              "5/10/30/60",[f[f"+{m}m"]["return_pct"] for m in (5,10,30,60)],
              "RTH",f["RTH_CLOSE"].get("return_pct"),"7PM",f["AFTERHOURS_CLOSE_7PM_CT"].get("return_pct"),
              "24h",f["MIDNIGHT_FOLLOWING_DAY"].get("status"))
if __name__=="__main__":main()