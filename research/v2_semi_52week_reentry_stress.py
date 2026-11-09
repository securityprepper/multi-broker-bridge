"""52-week causal one-reentry stress for V2 semiconductors only.

Reenter after first tight-stop exit and >=15min quiet period, requiring
completed 5m SOXX AND stock +/-0.2% from prior RTH close. Execute 10min
after re-confirmation bar start. No broker actions. Last exit 14:40 ET.
"""
import json,statistics
from pathlib import Path
from collections import defaultdict
from v2_52week_delayed_anti_churn import load,prior5,forecast,replay,sample_metrics,SYMS
def forward_reentry(bars,h,day,sym,side,exit_time):
    b=bars[sym,day];sec=bars["SOXX",day]
    def minutes(t):h,m=map(int,t.split(":"));return h*60+m
    after=minutes(exit_time)+15
    for time in sorted(t for t in b if t>exit_time and t<"14:10"):
        if minutes(time)<after or time not in sec:continue
        c=side*100*(b[time][3]/h[sym,day][-1]-1)
        v=side*100*(sec[time][3]/h["SOXX",day][-1]-1)
        if min(c,v)<.2:continue
        # observation is complete at time+5; add one more 5m to next open
        entry_min=minutes(time)+10
        tm=f"{entry_min//60:02d}:{entry_min%60:02d}"
        if tm>="14:40" or tm not in b:return None
        return replay(bars,day,sym,side,"tight_5m",initial=tm)
    return None
def run():
    b=load();h=prior5(b);trades=[];signal_days=0
    for d in sorted({day for s,day in b if s=="SOXX" and (s,day) in h}):
        if not all((s,d) in h and all(t in b[s,d] for t in ("09:30","09:35","09:40","14:40","15:55")) for s in SYMS):continue
        side,stocks,_=forecast(d,b,h)
        if not side:continue
        signal_days+=1
        for s in stocks:
            first=replay(b,d,s,side,"tight_5m")
            if first is None:continue
            first["reentry"]=False;trades.append(first)
            if first["triggered"]:
                nxt=forward_reentry(b,h,d,s,side,first["exit_time"])
                if nxt is not None:
                    nxt["reentry"]=True;trades.append(nxt)
    byposition=defaultdict(list)
    for t in trades:byposition[(t["day"],t["symbol"])].append(t)
    positions=[{"day":day,"sym":s,"trade_count":len(group),
                 "sum_net30":round(sum(x["net30"] for x in group),5),
                 "sum_gross":round(sum(x["gross"] for x in group),5)}
               for (day,s),group in byposition.items()]
    posret=[x["sum_net30"] for x in positions]
    baseline=[x["net30"] for x in trades if not x["reentry"]]
    assert len(baseline)==len(positions)
    out={"signal_days":signal_days,"original_entries":len(positions),"executions":len(trades),
         "reentries":sum(x["reentry"] for x in trades),
         "first_only":sample_metrics([x for x in trades if not x["reentry"]]),
         "all_trade_stats":sample_metrics(trades),
         "per_original_position_after30": {"n":len(positions),
            "mean":round(statistics.mean(posret),4),
            "winning_position_count":sum(v>0 for v in posret),
            "win_pct":round(100*sum(v>0 for v in posret)/len(posret),2),
            "worst":round(min(posret),4)},
         "comparison_not_equivalent":"per-original-position sum net returns approximate equal starting dollar notional; original stop and reentry may use new cash; 5m SIP trade bars lack executable bid/ask and fill eligibility"}
    folder=Path("/tmp/v2-run23-full-year-anti-churn")
    (folder/"reentry-summary.json").write_text(json.dumps(out,indent=2))
    (folder/"reentry-daily.json").write_text(json.dumps(positions,indent=2))
    print(json.dumps(out,indent=2))
    return out
if __name__=="__main__":run()
