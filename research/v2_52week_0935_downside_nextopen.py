"""Research-only 09:35 downside warning / next regular open avoidance stress.
The warning uses prior FIVE RTH closes + completed 09:30-09:35 5Min SIP bar.
Following RTH opening mark is an OUTCOME, never a signal input.
This is NOT a proposed overnight holding policy; V1 latest-flat stays unchanged.
"""
import json,sys,statistics
from pathlib import Path
from collections import defaultdict
from v2_52week_delayed_anti_churn import load,prior5,forecast,SYMS
from v2_cross_sector_0935_risk_replay import load_sector,context,sector_signal,SECTORS

def cases(sector):
    if sector=="semiconductors":
        bars=load(); h=prior5(bars); etf="SOXX";peers=("AMD","MU","SNDK");spot=None
        def fn(day):return forecast(day,bars,h)
    else:
        etf,peers,spot=SECTORS[sector];bars=load_sector(sector)
        h=context(bars,(etf,)+peers+((spot,) if spot else ()))
        def fn(day):return sector_signal(day,bars,h,etf,peers,spot)
    syms=(etf,)+peers+((spot,) if spot else ())
    days=sorted(d for (s,d) in bars if s==etf and (s,d) in h and
      all((t,d) in h and all(k in bars[t,d] for k in ("09:30","09:35","09:40","15:55")) for t in syms))
    # Use the immediately following ETF regular session, not the next fully eligible
    # signal-data day. Never silently skip over a session with missing peer data.
    all_rth_days=sorted(d for (sym,d),session in bars.items() if sym==etf and "09:30" in session)
    next_rth={d:all_rth_days[i+1] for i,d in enumerate(all_rth_days[:-1])}
    daily=[]
    for i,day in enumerate(days):
        side,chosen,obs=fn(day)
        for s in peers:
            prev=h[s,day][-1];close=bars[s,day]["15:55"][3]
            completed=bars[s,day]["09:30"][3]
            close_pct=100*(close/prev-1)
            severe=close_pct<=-5
            warned=side==-1 and s in chosen
            # Exact next ETF RTH session; absent stock opening quote => missing outcome.
            next_day=next_rth.get(day)
            next_open=(bars[s,next_day]["09:30"][0] if next_day and "09:30" in bars[s,next_day] else None)
            entry=bars[s,day]["09:40"][0]
            benefit=100*(1-next_open/entry) if warned and next_open and entry>0 else None
            daily.append({"sector":sector,"day":day,"symbol":s,
                "observed_warning_0935":bool(warned),"warn_at":"09:35 ET" if warned else None,
                "close_prev_pct":round(close_pct,4),"severe_down":bool(severe),
                "already_down5_at_warning":bool(warned and 100*(completed/prev-1)<=-5),
                "entry_0940_open":round(entry,4),"following_rth_open":round(next_open,4) if next_open else None,
                "early_sale_vs_next_open_gross_pp":round(benefit,4) if benefit is not None else None})
    return daily
def summarize(rows):
    severe=[x for x in rows if x["severe_down"]];warned=[x for x in rows if x["observed_warning_0935"]]
    hits=[x for x in warned if x["severe_down"]]
    misses=[x for x in severe if not x["observed_warning_0935"]]
    usable=[x["early_sale_vs_next_open_gross_pp"] for x in warned if x["early_sale_vs_next_open_gross_pp"] is not None]
    e=sorted(hits,key=lambda x:(x["day"],x["symbol"]))
    early=e[0] if e else None
    return {"total_stock_days":len(rows),"severe_down_stock_days":len(severe),
       "warning_stock_days":len(warned),"severe_hits":len(hits),
       "sensitivity_pct":round(100*len(hits)/len(severe),2) if severe else None,
       "nonsevere_warnings":len(warned)-len(hits),
       "severe_missed":len(misses),"misses_first_10":[(x["day"],x["symbol"]) for x in misses[:10]],
       "severe_hits_after_already_down5":sum(x["already_down5_at_warning"] for x in hits),
       "earliest_major_warning":(early["day"]+"T09:35:00 America/New_York "+early["symbol"]) if early else None,
       "warned_next_open_comparable":len(usable),
       "early_sale_better_vs_next_open_30bp":sum(x>.3 for x in usable),
       "early_sale_mean_gross_vs_next_open_pp":round(statistics.mean(usable),4) if usable else None,
       "early_sale_mean_after30_vs_next_open_pp":round(statistics.mean(x-.3 for x in usable),4) if usable else None,
       "early_sale_worse_by_gt2pp":sum(x<-2 for x in usable)}
if __name__=="__main__":
    out={};daily=[]
    for sector in ["semiconductors",*SECTORS]:
        x=cases(sector);daily+=x
        ordered=sorted({r["day"] for r in x});cut=int(len(ordered)*.7)
        early=set(ordered[:cut]);late=set(ordered[cut:])
        out[sector]={"all":summarize(x),
                     "earlier70":summarize([r for r in x if r["day"] in early]),
                     "later30":summarize([r for r in x if r["day"] in late])}
    base=Path("/tmp/v2-run23-full-year-anti-churn")
    (base/"nextopen-warning-results.json").write_text(json.dumps(out,indent=2))
    (base/"nextopen-warning-daily.json").write_text(json.dumps(daily,indent=2))
    print(json.dumps(out,indent=2))
