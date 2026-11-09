"""V2 OFFLINE ONLY: preopen + first-hour crash protection and false-alarm costs.

Signals use timestamped completed bars. Actual 5m next OPEN and later opens
are retrospective, never a claimed fill or live input; no broker I/O.
"""
from __future__ import annotations
import argparse, json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import mean
from research.v2_stock_risk_dayphase import ET, ingest, first_signal
from research.v2_reversal_and_limit_stress import all_days
from research.v2_asof_sector_confirmation import prior_regular_closes
from research.v2_premarket_sector_snapshot import earliest_signal
from research.v2_early_flip_sensitivity import first_flip,VARIANTS

T5=timedelta(minutes=5)
F=0.0015
LIMIT=0.003

def normalize_strict(hit,bars):
    if hit is None:return None
    asof,kind,start,change=hit
    entry=bars.get(asof)
    return {"asof":asof.isoformat(),"source":"strict_"+kind,
            "signal_price":bars[start][3],
            "next_bar_open":entry[0] if entry else None,
            "total_pct":round(100*change,4)}

def normalize_breadth(hit,previous_close):
    if hit is None:return None
    return {"asof":hit["asof"],"source":"sector_preopen",
            "signal_price":hit["observed_price"],
            "next_bar_open":hit["next_bar_open"],
            "total_pct":round(100*(hit["observed_price"]/previous_close-1),4)}

def normalize_flip(hit):
    if not hit or hit["side"]!="down":return None
    return {"asof":hit["at"],"source":"opening_flip",
            "signal_price":hit["price"],
            "next_bar_open":hit["next_bar_open"],
            "total_pct":hit["total_from_prior_pct"]}

def earliest(hits):
    return min((h for h in hits if h),key=lambda x:(x["asof"],x["source"]),
               default=None)

def price_scenario(hit,prev_close,next_regular_open,morning_open=None):
    """Early sell vs holding through following open, with limit eligibility.

    A rejected/ineligible order has ZERO hypothetical avoided loss: no fallback
    fill claim and no implicit order replacement. Morning-open comparison
    available only when the warning precedes 09:30.
    """
    nxt=hit["next_bar_open"]
    if nxt is None or next_regular_open is None or min(
            prev_close,nxt,next_regular_open,hit["signal_price"])<=0:
        return None
    sell=nxt*(1-F)
    eligible=sell>=hit["signal_price"]*(1-LIMIT)
    advantage=(100*(sell-next_regular_open*(1-F))/prev_close) if eligible else 0.0
    morning=None
    if morning_open and morning_open>0:
        morning=100*(sell-morning_open*(1-F))/prev_close if eligible else 0.0
    return {"eligible_price_proxy":eligible,
            "advantage_to_next_open_pp":round(advantage,4),
            "advantage_to_same_morning_open_pp":
                    round(morning,4) if morning is not None else None}

def period_summary(rows,attr):
    affected=[r for r in rows if r[attr] is not None]
    severe=[r for r in rows if r["major_down"]]
    hit=[r for r in affected if r["major_down"]]
    nonmajor=[r for r in affected if not r["major_down"]]
    posclose=[r for r in affected if r["major_up"]]
    early=[r for r in hit if r[attr]["total_pct"]>-5]
    scenarios=[r["scores"][attr] for r in affected if r["scores"][attr] is not None]
    benefits=[x["advantage_to_next_open_pp"] for x in scenarios]
    mornings=[x["advantage_to_same_morning_open_pp"] for x in scenarios
              if x["advantage_to_same_morning_open_pp"] is not None]
    nonmajor_scenarios=[r["scores"][attr] for r in nonmajor
                        if r["scores"][attr] is not None]
    nonmajor_benefits=[x["advantage_to_next_open_pp"]
                       for x in nonmajor_scenarios]
    gaps=[r for r in rows if r["gap_down5"]]
    withgap=[r for r in gaps if r[attr] is not None and
             datetime.fromisoformat(r[attr]["asof"]).astimezone(ET)<
             datetime.combine(date.fromisoformat(r["day"]),time(9,30),ET)]
    return {"stockdays":len(rows),"major_down_days":len(severe),"major_up_days":
            sum(r["major_up"] for r in rows),
            "warnings":len(affected),"severe_down_hit":len(hit),
            "severe_down_missed":len(severe)-len(hit),
            "nonmajor_down_warnings":len(nonmajor),
            "major_up_sold_early_risk":len(posclose),
            "severe_hit_before_already_down5":len(early),
            "earliest_severe_warning":min((r[attr]["asof"] for r in hit),default=None),
            "hypothetical_sale_price_scorable":len(scenarios),
            "price_eligible_not_actual_fills":
                sum(s["eligible_price_proxy"] for s in scenarios),
            "mean_advantage_next_open_pp":round(mean(benefits),4) if benefits else None,
            "mean_advantage_same_morning_open_pp":round(mean(mornings),4) if mornings else None,
            "beneficial_nonmajor_early_sale_count":sum(x>0 for x in nonmajor_benefits),
            "harmful_nonmajor_early_sale_count":sum(x<0 for x in nonmajor_benefits),
            "beneficial_early_sale_count":sum(x>0 for x in benefits),
            "harmful_early_sale_count":sum(x<0 for x in benefits),
            "same_day_gap5_count":len(gaps),
            "gap5_with_preopen_warning":len(withgap)}

def analyze(bars,daily):
    universe,daystrings=all_days(bars,daily)
    dates=[date.fromisoformat(x) for x in daystrings]
    prev=dict(zip(dates[1:],dates[:-1]))
    nxt=dict(zip(dates[:-1],dates[1:]))
    closes=prior_regular_closes(bars)
    buckets=defaultdict(lambda:defaultdict(dict))
    for sym,d in bars.items():
        for at,row in d.items():
            buckets[sym][at.date()][at]=row
    out=[]
    for row in universe:
        d=date.fromisoformat(row["day"])
        prevday=prev[d]
        sym=row["sym"]
        morning=bars[sym].get(datetime.combine(d,time(9,30),ET))
        nextd=nxt.get(d)
        nextmorning=bars[sym].get(datetime.combine(nextd,time(9,30),ET)) if nextd else None
        prebase=row["previous_close"]
        # Original conjunction over relevant previous-evening, premarket and RTH opening bars.
        window={**buckets[sym].get(prevday,{}),**buckets[sym].get(d,{})}
        strict=normalize_strict(first_signal(window,prebase,d,prevday,
            {"evening","premarket","rth_open_hour"}),bars[sym])
        breadth=normalize_breadth(
            earliest_signal(bars,closes,sym,prevday,d,"down"),prebase)
        flip=normalize_flip(
            first_flip(bars,closes,sym,prevday,d,VARIANTS["base_100"]))
        pre_candidates=[h for h in (strict,breadth) if h and
                        datetime.fromisoformat(h["asof"]).astimezone(ET)<
                        datetime.combine(d,time(9,30),ET)]
        pre=earliest(pre_candidates)
        anyhit=earliest((strict,breadth,flip))
        outcomes={}
        for key,hit in (("strict",strict),("breadth",breadth),
                        ("opening_flip",flip),("preopen_union",pre),
                        ("all_union",anyhit)):
            outcomes[key]=(price_scenario(hit,prebase,
                nextmorning[0] if nextmorning else None,
                morning[0] if morning and
                hit and datetime.fromisoformat(hit["asof"])<
                    datetime.combine(d,time(9,30),ET) else None)
                if hit else None)
        out.append({"sym":sym,"day":row["day"],
            "close_pct":row["change_pct"],"major_down":row["big_down"],
            "major_up":row["big_up"],"gap_down5": bool(morning and
                100*(morning[0]/prebase-1)<=-5),
            "morning_gap_pct":round(100*(morning[0]/prebase-1),3) if morning else None,
            "strict":strict,"breadth":breadth,"opening_flip":flip,
            "preopen_union":pre,"all_union":anyhit,"scores":outcomes})
    reports={}
    for phase,rows in (("all",out),
            ("earlier",[r for r in out if r["day"]<"2026-09-01"]),
            ("later",[r for r in out if r["day"]>="2026-09-01"])):
        reports[phase]={key:period_summary(rows,key)
                        for key in ("strict","breadth","opening_flip",
                                    "preopen_union","all_union")}
    severe_missed=[r for r in out if r["major_down"] and not r["all_union"]]
    severe_missed.sort(key=lambda x:x["close_pct"])
    pre_missed=[r for r in out if r["major_down"] and not r["preopen_union"]]
    pre_missed.sort(key=lambda x:x["close_pct"])
    up_veto=[r for r in out if r["major_up"] and r["preopen_union"]]
    result={"universe":len(out),
        "major_gains":sum(r["major_up"] for r in out),
        "major_losses":sum(r["major_down"] for r in out),
        "reports":reports,
        "missed_crashes_no_early_union":[
            {"day":r["day"],"symbol":r["sym"],"close_pct":r["close_pct"],
             "morning_gap_pct":r["morning_gap_pct"]}
            for r in severe_missed[:12]],
        "missed_crashes_no_preopen":[
            {"day":r["day"],"symbol":r["sym"],"close_pct":r["close_pct"],
             "morning_gap_pct":r["morning_gap_pct"]}
            for r in pre_missed[:12]],
        "major_up_days_preopen_sell_veto_examples":[
            {"day":r["day"],"symbol":r["sym"],"close_pct":r["close_pct"],
             "alert":r["preopen_union"]["asof"]}
            for r in up_veto[:12]],
        "nov2":[{"symbol":r["sym"],"severe":r["major_down"],
                 "close_pct":r["close_pct"],
                 "preopen":r["preopen_union"],"any":r["all_union"]}
                for r in out if r["day"]=="2026-11-02" and r["major_down"]],
        "limitations":"OHLC next-open price-mark-only, no NBBO, BOATS fills, futures or V1 execution evidence"}
    return result,out

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--primary",default="/tmp/semis_52wk_5min_sip_adjusted.json")
    a.add_argument("--peers",default="/tmp/semis_peers_52wk_5min_adjusted.json")
    a.add_argument("--daily",default="/tmp/semis_52weeks_alpaca_daily.json")
    a.add_argument("--output")
    a.add_argument("--audit-output")
    args=a.parse_args()
    results,rows=analyze(ingest([args.primary,args.peers]),
             json.loads(Path(args.daily).read_text())["split"])
    if args.output:
        Path(args.output).write_text(json.dumps(results,indent=2,sort_keys=True))
    if args.audit_output:
        Path(args.audit_output).write_text(json.dumps(rows,indent=2,sort_keys=True))
    print(json.dumps(results,indent=2,sort_keys=True))

if __name__=="__main__":main()