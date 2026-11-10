"""Research-only forward 15/60min outcomes FROM signal mark, not prior close.

Follows already-frozen AMD early candidate timestamps for Oct12-Nov6 SIP 1m;
no candidate refitting and no order calls. Compare signal last COMPLETED close
to latest COMPLETED close as-of +15 or +60 minutes. Abstain when stale.
"""
from __future__ import annotations
import json, statistics
from collections import defaultdict
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from v2_mbb_early_shape_vs_breadth_20261109 import SRC
IN=Path("/tmp/v2_mbb_early_shape_vs_breadth_20261109.json")
OUT=Path("/tmp/v2_mbb_shape_forward_15m_60m_20261109.json")
ET=ZoneInfo("America/New_York")
FAMILIES=("net_breadth_3of3","MBB_eligible_AMD_shape")
def observed_completed_close(bars,asof,fresh_minutes=5):
    # Future bar close is known only at its start+60sec, never before.
    x=[(z,float(row[3])) for z,row in bars
       if z+timedelta(minutes=1)<=asof
       and timedelta(0)<=asof-(z+timedelta(minutes=1))<=timedelta(minutes=fresh_minutes)]
    return max(x,key=lambda x:x[0]) if x else None
def extract_day(raw,day):
    return sorted((datetime.fromisoformat(t.replace("Z","+00:00")),v)
                  for t,v in raw[day]["AMD"].items()
                  if v[-1]=="sip" and datetime.fromisoformat(t.replace("Z","+00:00")).astimezone(ET).date().isoformat()==day)
def evaluate(raw,audit):
    daily=[]
    for item in audit["days"]:
        day=item["day"];bars=extract_day(raw,day)
        by_time={z:float(v[3]) for z,v in bars}
        for family in FAMILIES:
            first=item.get("first",{}).get(family)
            r={"date":day,"policy":family,"signal_available_at":None,
               "signal_amd_close":None}
            if first:
                signal=datetime.fromisoformat(first["bar_completed_by"])
                past=datetime.fromisoformat(first["amd_bar_timestamp"])
                base=by_time.get(past)
                if base is not None and past+timedelta(minutes=1)<=signal:
                    r.update(signal_available_at=signal.isoformat(),signal_amd_close=base)
                    for horizon in (15,60):
                        end=observed_completed_close(bars,signal+timedelta(minutes=horizon))
                        if end:
                            pct=100*(end[1]/base-1)
                            r.update({f"h{horizon}_end_timestamp":(end[0]+timedelta(minutes=1)).isoformat(),
                                      f"h{horizon}_end_amd_close":end[1],
                                      f"h{horizon}_forward_pct":round(pct,6),
                                      f"h{horizon}_positive_over_30bps":pct>.30,
                                      f"h{horizon}_direction_up":pct>0.05})
            daily.append(r)
    return daily
def summary(rows):
    out={}
    dates=sorted(set(r["date"] for r in rows));split=dates[len(dates)//2]
    for family in FAMILIES:
        family_rows=[r for r in rows if r["policy"]==family]
        o={"signal_days":sum(bool(r.get("signal_available_at"))
                             for r in family_rows),"abstain_days":sum(not r.get("signal_available_at")
                                                                    for r in family_rows)}
        for horizon in (15,60):
            o[f"h{horizon}"]={}
            for cohort,subset in (("full",family_rows),
                                  ("first10",[r for r in family_rows if r["date"]<split]),
                                  ("last10",[r for r in family_rows if r["date"]>=split])):
                x=[r for r in subset if r.get(f"h{horizon}_forward_pct") is not None]
                returns=[r[f"h{horizon}_forward_pct"] for r in x]
                o[f"h{horizon}"][cohort]={"valid_signals":len(x),
                  "positive_over_30bps":sum(r[f"h{horizon}_positive_over_30bps"] for r in x),
                  "up_direction_over_5bps":sum(r[f"h{horizon}_direction_up"] for r in x),
                  "mean_signed_gross_pct":round(statistics.mean(returns),5) if x else None,
                  "mean_signed_net30_pct":round(statistics.mean(returns)-.30,5) if x else None,
                  "worst_gross_pct":round(min(returns),5) if x else None}
        out[family]=o
    return out
def main():
    raw=json.loads(SRC.read_text());audit=json.loads(IN.read_text())
    rows=evaluate(raw,audit)
    o={"asof":"2026-11-09","source":"Alpaca split-adjusted SIP 1m trade-bar marks reused 20 days Oct12-Nov6",
       "signal_time":"First completed-candle 04:00-08:35 ET as-of 1m scan at :40",
       "future_time":"as-of signal timestamp +15m or +60m using latest completed 1m bar available",
       "baseline":"ONLY the AMD close of the last fully completed bar available at signal time, never previous close",
       "tradeability":"30bps illustrative price-motion hurdle only, not NBBO spreads, fills, stop outcomes or profit",
       "summary":summary(rows),"daily":rows}
    OUT.write_text(json.dumps(o,indent=2)+"\n")
    print(json.dumps(o["summary"],indent=2))
if __name__=="__main__":main()
