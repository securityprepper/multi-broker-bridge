"""Offline macro announcement opportunity budget; not trading signals.
Official release CALENDAR dates only; no historical consensus surprise data.
Data: historical Alpaca SIP 5m bars (NOT NBBO/real fills), split adjusted.
Evaluate observable future move after a fixed event-scoped decision time, never
use same-day final outcome in an alert/prediction or as a selector for direction.
"""
import argparse, json
from collections import Counter, defaultdict
from datetime import datetime, date, time, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ET=ZoneInfo("America/New_York")
# BLS release calendars, announced 08:30 ET.
CPI=set("2025-12-18 2026-01-13 2026-02-13 2026-03-11 2026-04-10 2026-05-12 2026-06-10 2026-07-14 2026-08-12 2026-09-11 2026-10-14 2026-11-10".split())
JOBS=set("2025-12-16 2026-01-09 2026-02-11 2026-03-06 2026-04-03 2026-05-08 2026-06-05 2026-07-02 2026-08-07 2026-09-04 2026-10-02 2026-11-06".split())
# Federal Reserve 14:00 ET announcement; 14:30 press conference begins inside
# fixed 13:40 Chicago flat period, so this is just a short-window feasibility test.
FOMC=set("2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16 2026-10-28".split())
SOURCES={
  "SOXX":"/tmp/semis_52wk_5min_sip_adjusted.json",
  "GDX":"/tmp/v2-run15-sector-precision-work/alpaca_sip/GDX_sip.json",
  "XLF":"/tmp/v2-run17-cross-sector-precision/alpaca_sip/XLF_sip.json",
  "XLE":"/tmp/v2-run17-cross-sector-precision/alpaca_sip/XLE_sip.json",
  "IGV":"/tmp/v2-run17-cross-sector-precision/alpaca_sip/IGV_sip.json",
}
def utciso(s):
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("No timezone")
    return t
def load_symbol(symbol, file_path):
    data=json.loads(Path(file_path).read_text())
    if symbol in data:
        raw=data[symbol].items()
        out=[(utciso(t).astimezone(ET),v) for t,v in raw]
    else:
        if data.get("symbol")!=symbol or data.get("feed")!="sip" or data.get("timeframe")!="5Min" or data.get("adjustment")!="split":
            raise ValueError("Invalid Alpaca source")
        out=[(utciso(x[0]).astimezone(ET),x[1:]) for x in data["bars"]]
    days=defaultdict(dict)
    for dt,bar in out:
        if dt.time()<time(9,30) or dt.time()>time(15,55):continue
        if len(bar)<4:raise ValueError("Invalid OHLC")
        o,h,l,c=map(float,bar[:4])
        if o<=0 or c<=0 or l>min(o,c) or h<max(o,c):raise ValueError("Invalid OHLC")
        if dt.time() in days[dt.date().isoformat()]:raise ValueError("Duplicate 5m date/time")
        days[dt.date().isoformat()][dt.time()]=c
    return days

def asof_pair(bars, event_type):
    # Most recent bar at 09:30 (completed 09:35 ET) for morning; 14:00
    # (completed 14:05 ET) for FOMC. 14:35 completes at 14:40 ET=13:40 CT.
    signal=time(14,0) if event_type=="FOMC" else time(9,30)
    final=time(14,35)
    if signal not in bars or final not in bars:return None
    return bars[signal],bars[final]

def realized(directionless_return):
    return abs(directionless_return)>0.003,abs(directionless_return)>0.006

def evaluate(sources=SOURCES):
    results={}
    all_events={"CPI":CPI,"JOBS":JOBS,"FOMC":FOMC}
    for sym,path in sources.items():
        daybars=load_symbol(sym,path)
        results[sym]={}
        for kind,dates in all_events.items():
            # Deliberately non-event controls at the SAME clock horizon,
            # excluding ALL known CPI/JOBS/FOMC dates (not sign-conditioned).
            known_event_days=set().union(*all_events.values())
            controls=[]
            for day, bars in daybars.items():
                if day in known_event_days:continue
                cp=asof_pair(bars,kind)
                if cp:controls.append(cp[1]/cp[0]-1)
            observed=[];missing=[]
            for dt in sorted(dates):
                s=daybars.get(dt,{})
                pair=asof_pair(s,kind)
                if pair is None:missing.append(dt);continue
                p0,p1=pair
                # THIS IS THE REALIZED FUTURE return (unknown at signal time)
                # and ONLY used as a feasibility upper bound, never a label
                # available to the trading decision.
                r=p1/p0-1
                observed.append(r)
            if not observed:
                results[sym][kind]={"event_days_listed":len(dates),"observed":0,"missing":missing}
                continue
            larger30=sum(realized(x)[0] for x in observed)
            larger60=sum(realized(x)[1] for x in observed)
            results[sym][kind]={
                "event_days_listed":len(dates),"observed":len(observed),"missing_count":len(missing),
                "control_non_event_days":len(controls),
                "control_abs_forward_gt_30bp":sum(abs(x)>.003 for x in controls),
                "control_mean_abs_forward_pct":round(sum(abs(x) for x in controls)/len(controls)*100,4) if controls else None,
                "abs_forward_gt_30bp":larger30,"abs_forward_gt_60bp":larger60,
                "forward_up_count":sum(x>0 for x in observed),
                "forward_down_count":sum(x<0 for x in observed),
                "mean_abs_forward_pct":round(sum(abs(x) for x in observed)/len(observed)*100,4),
                "mean_signed_forward_pct":round(sum(observed)/len(observed)*100,4),
                "net_after_30bp_perfect_direction_upper_bound_pct":
                    round((sum(abs(x) for x in observed)/len(observed)-.003)*100,4),
                "sample_start":"2025-11-03","sample_end":"2026-11-06",
                "signal_time_et":"14:05" if kind=="FOMC" else "09:35",
                "exit_time_et":"14:40"}
    return {"scope":"OFFLINE_CALENDAR_NONPREDICTIVE_OPPORTUNITY_BUDGET",
      "no_trade_or_buy_signal":True,"consensus_surprises_available":False,
      "first_observed_macro_surprise":False,
      "realized_move_not_known_at_decision":True,
      "executable_NBBO_prices_verified":False,
      "max_gain_percent_is_unattainable_perfect_direction_upper_bound":True,
      "official_calendar_sources":["bls.gov/schedule/news_release/cpi.htm",
         "bls.gov/schedule/news_release/empsit.htm",
         "federalreserve.gov/monetarypolicy/fomccalendars.htm"],
      "results":results}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    p=Path(args.output)
    if p.exists():raise SystemExit("Never overwrite research output")
    x=evaluate()
    p.write_text(json.dumps(x,indent=2,sort_keys=True))
    print(json.dumps(x,sort_keys=True))
