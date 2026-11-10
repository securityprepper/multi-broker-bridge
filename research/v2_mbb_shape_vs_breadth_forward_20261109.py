"""After-signal AMD historical trade-mark outcome comparison (RESEARCH ONLY).

Compares the first 04:00-08:35 ET net 3/3 positive breadth to first possible
MBB four-candle-shape AMD candidate on the SAME 20 dates. Does not assume
quotes, cash, positions, broker sessions or actual executions.
"""
from __future__ import annotations
import csv, json, statistics
from pathlib import Path
from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from v2_mbb_early_shape_vs_breadth_20261109 import evaluate,SRC,NY
OUT=Path("/tmp/v2_mbb_shape_vs_breadth_forward_20261109.json")
CSV=Path("/tmp/v2_mbb_shape_vs_breadth_forward_20261109.csv")
FAMILIES=("net_breadth_3of3","MBB_eligible_AMD_shape")
def mark_at_first_future_open(bars,signal_dt):
    # no trades recorded after signal time may be used as contemporaneous fills.
    later=[(z,row) for z,row in bars if z>signal_dt and z<=signal_dt+timedelta(minutes=5)]
    return later[0] if later else None

def day_bars(raw,day):
    return sorted((datetime.fromisoformat(ts.replace("Z","+00:00")),row)
                  for ts,row in raw[day]["AMD"].items()
                  if datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(NY).date().isoformat()==day
                  and row[5]=="sip")

def exit_at_flat(bars,day):
    cutoff=datetime.combine(datetime.fromisoformat(day).date(),time(14,40),NY)
    exact=[(z,row) for z,row in bars if z==cutoff]
    return exact[0] if exact else None

def outcomes(audit,raw):
    rows=[]
    for item in audit["days"]:
        d=item["day"]
        bars=day_bars(raw,d)
        end=exit_at_flat(bars,d)
        for family in FAMILIES:
            first=item.get("first",{}).get(family)
            r={"date":d,"policy":family,"signal":first.get("bar_completed_by") if first else None,
               "entry_bar":None,"entry_price":None,
               "flat_bar":end[0].isoformat() if end else None,
               "flat_price":end[1][0] if end else None,
               "signed_gross_pct":None,"signed_net30_pct":None,
               "adverse_excursion_pct":None,"status":"ABSTAIN"}
            if not first:rows.append(r);continue
            t=datetime.fromisoformat(first["bar_completed_by"])
            start=mark_at_first_future_open(bars,t)
            if not start or not end or start[0]>=end[0]:
                r["status"]="NO_ENTRY_OR_EXIT_MARK";rows.append(r);continue
            z,bar=start
            price=float(bar[0]);final=float(end[1][0])
            trough=min(float(row[2]) for tm,row in bars if z<=tm<end[0])
            r.update(entry_bar=z.isoformat(),entry_price=price,
                     signed_gross_pct=round(100*(final/price-1),5),
                     signed_net30_pct=round(100*(final/price-1)-.30,5),
                     adverse_excursion_pct=round(100*(trough/price-1),5),
                     status="SCORED")
            rows.append(r)
    return rows

def metrics(rows):
    out={}
    dates=sorted(set(r["date"] for r in rows))
    for family in FAMILIES:
        x=[r for r in rows if r["policy"]==family]
        n=[r for r in x if r["status"]=="SCORED"]
        split_day=dates[len(dates)//2]
        o={"signal_days":sum(r["signal"] is not None for r in x),"scored":len(n),
           "abstain":sum(r["status"]=="ABSTAIN" for r in x),
           "unscored":sum(r["status"]=="NO_ENTRY_OR_EXIT_MARK" for r in x)}
        for cohort,yy in (("all",n),("first10",[r for r in n if r["date"]<split_day]),
                          ("last10",[r for r in n if r["date"]>=split_day])):
            v=[r["signed_net30_pct"] for r in yy]
            o[cohort]={"n":len(v),"winning_after_30bps":sum(f>0 for f in v),
                        "mean_net_pct":round(statistics.mean(v),4) if v else None,
                        "worst_net_pct":min(v) if v else None,
                        "worst_adverse_excursion_pct":min((r["adverse_excursion_pct"] for r in yy),default=None)}
        out[family]=o
    return out

def main():
    raw=json.loads(SRC.read_text())
    audit=evaluate(raw)
    rows=outcomes(audit,raw)
    result={"asof":"2026-11-09","signal_audit":audit["summary"],
      "comparison":metrics(rows),
      "method":"Signal first at completed one-minute candle close <= scan at :40; enter at first later observed SIP 1m bar OPEN no more than five minutes later; exit 14:40 ET OPEN if observed; 30bp illustrative total friction. Neither mark is an executable quote; no stop/borrow/session/order simulation.",
      "data_limitations":"Already-used 20 days, cross-strategy conflicts excluded, synthetic prior 5 RTH sessions not verified for all dates; P&L cannot be called broker realizable; shorts excluded.",
      "outcomes":rows}
    OUT.write_text(json.dumps(result,indent=2)+"\n")
    with CSV.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(result["comparison"],indent=2))
    print("ROWS",len(rows),"DAILY_CSV",CSV)
if __name__=="__main__":main()
