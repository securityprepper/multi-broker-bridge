"""Research-only replay of MBB's four-bar rising shape versus net-price breadth.

Never calls broker or data APIs, never reads credentials and cannot place orders.
Uses archived Alpaca split-adjusted SIP 1m trade bars, 20 dates Oct12-Nov6.
This is an as-of qualitative **signal-feasibility** audit, not executable fills.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, time
from decimal import Decimal
import json
from pathlib import Path
from zoneinfo import ZoneInfo

NY=ZoneInfo("America/New_York")
UTC=ZoneInfo("UTC")
SRC=Path("/tmp/sector_complete_20session_alpaca_mixed.json")
OUT=Path("/tmp/v2_mbb_early_shape_vs_breadth_20261109.json")
PEERS=("AMD","MU","SNDK")
MIN_START=time(4,0)
MAX_END=time(8,35)

def parse(symbol_rows):
    return sorted((datetime.fromisoformat(t.replace("Z","+00:00")),float(row[1]),float(row[2]),float(row[3]),str(row[5]))
                  for t,row in symbol_rows.items())

def previous_rth_close(rows,day):
    vals=[(z,p) for z,high,low,p,feed in rows
          if z.astimezone(NY).date()<day
          and time(15,55)<=z.astimezone(NY).time()<=time(15,59)
          and feed=="sip"]
    return vals[-1][1] if vals else None

def eligible_now(rows,day,now):
    # As in auto_paper: data endpoint end=now-30s and incomplete 1m bars
    # discarded. Never use after 'now' observations.
    end=now-timedelta(seconds=30)
    beginning=end-timedelta(minutes=47)
    return [(z,hi,lo,close) for z,hi,lo,close,feed in rows
            if feed=="sip" and z.astimezone(NY).date()==day
            and beginning<=z<=end and z+timedelta(minutes=1)<=now]

def rising_shape(trailing):
    if len(trailing)<4:return False
    recent=trailing[-4:]
    for earlier,later in zip(recent,recent[1:]):
        if not earlier[0]<later[0]<=earlier[0]+timedelta(seconds=90):return False
        if not (later[1]>earlier[1] and later[2]>earlier[2]):return False
        if (later[3]-earlier[3])/earlier[3]>.025:return False
    return recent[-1][3]>recent[0][3]

def observe(data,day,now,close_by_symbol):
    rows={s:eligible_now(data[s],day,now) for s in PEERS}
    valid={s:bool(rows[s]) and timedelta(0)<=now-rows[s][-1][0]<=timedelta(seconds=135)
           for s in PEERS}
    shape={s:bool(valid[s] and len(rows[s])>=4 and rising_shape(rows[s][-5:]))
           for s in PEERS}
    # MBB: rising anchors >=2/3, but only available anchors in denominator.
    available=sum(valid.values())
    rising=sum(shape.values())
    strict=(available>=2 and rising>=2 and rising/available>=.6 and shape["AMD"])

    net={}
    for s in PEERS:
        q=rows[s]
        close=close_by_symbol[s]
        net[s]=bool(q and close and timedelta(0)<=now-q[-1][0]<=timedelta(minutes=10)
                    and q[-1][3]/close-1>=.002)
    breadth_2of3=sum(net.values())>=2 and net["AMD"]
    breadth_3of3=all(net.values())

    return {"MBB_eligible_AMD_shape":strict,"net_breadth_2of3":breadth_2of3,
            "net_breadth_3of3":breadth_3of3,"shapes":shape,
            "anchor_fresh":valid,"net":net,
            "last_completed_amd_bar":rows["AMD"][-1][0].isoformat() if rows["AMD"] else None}

def evaluate(raw):
    results=[]
    for date in sorted(raw):
        day=datetime.fromisoformat(date).date()
        data={s:parse(raw[date][s]) for s in PEERS}
        refs={s:previous_rth_close(data[s],day) for s in PEERS}
        if any(v is None for v in refs.values()):
            results.append({"day":date,"eligible":False,"reason":"missing_prev_rth_close"})
            continue
        # Fixed clock scan 04:00:40 ... 08:35:40 ET inclusive.
        z=datetime.combine(day,MIN_START,NY)+timedelta(seconds=40)
        finish=datetime.combine(day,MAX_END,NY)+timedelta(seconds=40)
        counters=defaultdict(int)
        first={}
        for _ in range(300):
            if z>finish:break
            o=observe(data,day,z,refs)
            for k in ("MBB_eligible_AMD_shape","net_breadth_2of3","net_breadth_3of3"):
                if o[k]:
                    counters[k]+=1
                    if k not in first:first[k]={"bar_completed_by":z.isoformat(),
                                                 "amd_bar_timestamp":o["last_completed_amd_bar"],
                                                 "anchor_shapes":o["shapes"],
                                                 "anchor_net":o["net"]}
            # track stricter overlap at the SAME time as early breadth
            if o["net_breadth_3of3"]:
                counters["net3_while_not_MBB"]+=not o["MBB_eligible_AMD_shape"]
                if not o["MBB_eligible_AMD_shape"] and "first_net3_MBB_disagreement" not in first:
                    first["first_net3_MBB_disagreement"]={"available_at":z.isoformat(),
                                                        "anchor_shapes":o["shapes"],
                                                        "anchor_fresh":o["anchor_fresh"]}
            if o["net_breadth_2of3"]:
                counters["net2_while_not_MBB"]+=not o["MBB_eligible_AMD_shape"]
            z+=timedelta(minutes=1)
        results.append({"day":date,"eligible":True,"counters":dict(counters),"first":first})
    valid=[r for r in results if r["eligible"]]
    labels=("MBB_eligible_AMD_shape","net_breadth_2of3","net_breadth_3of3")
    summary={"dates":len(results),"valid_dates":len(valid),
             "date_first_counts":{k:sum(k in r["first"] for r in valid) for k in labels},
             "date_breadth_without_MBB":{
              "net2":sum("net_breadth_2of3" in r["first"] and
                         "MBB_eligible_AMD_shape" not in r["first"] for r in valid),
              "net3":sum("net_breadth_3of3" in r["first"] and
                         "MBB_eligible_AMD_shape" not in r["first"] for r in valid)},
             "minute_candidate_counts":{k:sum(r["counters"].get(k,0) for r in valid)
                                        for k in (*labels,"net2_while_not_MBB","net3_while_not_MBB")}}
    return {"metadata":{"input":str(SRC),"date_range":(results[0]["day"],results[-1]["day"]),
                        "signal_cutoff":"08:35:40 ET","SIP_only":True,
                        "asof_rule":"at minute :40 source endpoint end=now-30 seconds, only completed candles, no future",
                        "quote_and_broker_constraints_tested":False,
                        "candidate_count_is_buy_plus_exit":True,
                        "sample_status":"20 dates ALREADY researched, exploratory NOT independent prospective",
                        "broad_net_threshold_pct":0.2,
                        "MBB_rule":"AMD 4 completed 1m bars three successive higher highs and lows, max +2.5% per bar, sector >=2 fresh matching anchors"},
            "summary":summary,"days":results}
def main():
    raw=json.loads(SRC.read_text())
    result=evaluate(raw)
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result["summary"],indent=2))
    for d in result["days"]:
        print(d["day"],"INVALID" if not d["eligible"] else
              "net2="+str(d["first"].get("net_breadth_2of3",{}).get("bar_completed_by"))+
              " net3="+str(d["first"].get("net_breadth_3of3",{}).get("bar_completed_by"))+
              " MBB="+str(d["first"].get("MBB_eligible_AMD_shape",{}).get("bar_completed_by")))
if __name__=="__main__":main()
