"""52-week sector threshold audit. Read-only SIP 5-minute trade bars.
Classify regular-hours threshold TOUCH from RTH 09:30 open to intraday OHLC high/low;
separately classify RTH open->close. Overnight uses preceding close reference,
observed 16:00-20:00 ET prior date + 04:00-09:30 ET current date plus opening gap.
SIP does not cover the 20:00-04:00 BOATS window; touch counts are lower bounds.
"""
from __future__ import annotations
import json
from datetime import datetime, time
from zoneinfo import ZoneInfo
from collections import defaultdict
from pathlib import Path
ET=ZoneInfo("America/New_York")
ROOT=Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
FILES = {
    "semiconductors":("/tmp/semis_52wk_5min_sip_adjusted.json","SOXX"),
    "gold_miners":("/tmp/v2-run15-sector-precision-work/alpaca_sip/GDX_sip.json","GDX"),
    "energy":(str(ROOT/"XLE_sip.json"),"XLE"),
    "financials":(str(ROOT/"XLF_sip.json"),"XLF"),
    "industrials":(str(ROOT/"XLI_sip.json"),"XLI"),
    "healthcare":(str(ROOT/"XLV_sip.json"),"XLV"),
    "software":(str(ROOT/"IGV_sip.json"),"IGV"),
}
LIMITS = {
    "semiconductors":{"day":2.0,"night":3.0},
    "gold_miners":{"day":2.0,"night":2.0},
    "energy":{"day":3.0,"night":3.0},
    "financials":{"day":3.0,"night":3.0},
    "industrials":{"day":3.0,"night":3.0},
    "healthcare":{"day":3.0,"night":3.0},
    "software":{"day":3.0,"night":3.0},
}
def pull(path,symbol):
    data=json.loads(Path(path).read_text())
    direct=symbol in data and isinstance(data[symbol],dict)
    if not direct:
        assert data.get("feed")=="sip" and data.get("timeframe")=="5Min" and data.get("adjustment")=="split",path
    raw=data[symbol].items() if direct else ((row[0],row[1:]) for row in data["bars"])
    grouped=defaultdict(lambda:{"rth":[],"pre":[],"post":[]})
    for stamp,row in raw:
        if not len(row)>=5:continue
        t=datetime.fromisoformat(stamp.replace("Z","+00:00")).astimezone(ET)
        if t.weekday()>=5:continue
        q=tuple(float(x) for x in row[:4])
        if q[0]<=0 or q[1]<=0 or q[2]<=0 or q[3]<=0:continue
        category=("rth" if time(9,30)<=t.time()<=time(15,55) else
                  "pre" if time(4,0)<=t.time()<time(9,30) else
                  "post" if time(16,0)<=t.time()<time(20,0) else None)
        if category:grouped[t.date().isoformat()][category].append((t,q))
    valid={}
    for date,b in sorted(grouped.items()):
        rth=sorted(b["rth"]);r=[i for i in rth if i[0].time()==time(9,30)]
        z=[i for i in rth if i[0].time()==time(15,55)]
        if not r or not z or len(rth)<65:continue
        first_open=r[0][1][0];last_close=z[-1][1][3]
        valid[date]={"open":first_open,"close":last_close,
            "rth_high":max(q[1] for _,q in rth),"rth_low":min(q[2] for _,q in rth),
            "post":b["post"],"pre":b["pre"],"rth_bars":len(rth)}
    return valid

def classify(p,threshold):
    return "UP" if p>=threshold else ("DOWN" if p<=-threshold else "NO")

def summarize(sector,valid):
    dates=sorted(valid)
    day_rows=[];night_rows=[]
    dth=LIMITS[sector]["day"];nth=LIMITS[sector]["night"]
    for day in dates:
        r=valid[day];op=r["open"];close=r["close"]
        u=100*(r["rth_high"]/op-1);d=100*(r["rth_low"]/op-1)
        day_rows.append({"date":day,"open":op,"close":close,
            "open_to_close_pct":round(100*(close/op-1),5),
            "max_up_pct":round(u,5),"max_down_pct":round(d,5),
            "touch_up":u>=dth,"touch_down":d<=-dth,
            "end_up":close/op-1>=dth/100,"end_down":close/op-1<=-dth/100})
    for i in range(1,len(dates)):
        day=dates[i];prev=dates[i-1];prev_close=valid[prev]["close"]
        v=valid[day];post=valid[prev]["post"];pre=v["pre"]
        obs=[q for _,q in post+pre]
        # At RTH open the night gap is already observed; don't assume any trades in
        # 20:00-04:00 gap have been captured without full BOATS history.
        hi=max([v["open"]]+[q[1] for q in obs])
        lo=min([v["open"]]+[q[2] for q in obs])
        up=100*(hi/prev_close-1);dn=100*(lo/prev_close-1)
        gap=100*(v["open"]/prev_close-1)
        night_rows.append({"date":day,"previous_day":prev,
            "reference":prev_close,"next_open":v["open"],
            "gap_pct":round(gap,5),"max_observed_up_pct":round(up,5),
            "max_observed_down_pct":round(dn,5),"afterhours_sip_bars":len(post),
            "premarket_sip_bars":len(pre),
            "touch_up":up>=nth,"touch_down":dn<=-nth,
            "gap_up":gap>=nth,"gap_down":gap<=-nth})
    def counts(rows,a,b):
        x=sum(bool(r[a]) for r in rows);y=sum(bool(r[b]) for r in rows)
        both=sum(bool(r[a]) and bool(r[b]) for r in rows)
        return {"up":x,"down":y,"either":x+y-both,"both":both}
    return {
        "sector":sector,"etf":FILES[sector][1],"day_threshold_pct":dth,"night_threshold_pct":nth,
        "complete_rth_days":len(day_rows),"overnight_intervals":len(night_rows),
        "day_touched":counts(day_rows,"touch_up","touch_down"),
        "day_closed_beyond":counts(day_rows,"end_up","end_down"),
        "night_sip_observed_or_gap_touched":counts(night_rows,"touch_up","touch_down"),
        "night_gap_at_open":counts(night_rows,"gap_up","gap_down"),
        "night_with_any_ext_sip_bars":sum(bool(r["afterhours_sip_bars"]+r["premarket_sip_bars"]) for r in night_rows),
        "night_with_both_pre_post_sip":sum(bool(r["afterhours_sip_bars"]) and bool(r["premarket_sip_bars"]) for r in night_rows),
        "first_day":dates[0],"last_day":dates[-1],"day_rows":day_rows,"night_rows":night_rows,
    }

def compute():
    result={}
    for name,(path,sym) in FILES.items():
        result[name]=summarize(name,pull(path,sym))
    return result
if __name__=="__main__":
    results=compute()
    path=Path("/tmp/v2_emergency_threshold_full_year_20261109.json")
    path.write_text(json.dumps(results,indent=2)+"\n")
    for name,v in results.items():
        print(name,v["etf"],"d",v["day_threshold_pct"],v["day_touched"],v["day_closed_beyond"],
              "n",v["night_threshold_pct"],v["night_sip_observed_or_gap_touched"],
              v["night_gap_at_open"],"bars",v["night_with_any_ext_sip_bars"],
              "days",v["complete_rth_days"],v["overnight_intervals"])
