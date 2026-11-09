"""V2 research only: train-locked signal stress with ticket commissions and day-cluster risk.

Sources are timestamped as-of, frozen candidate event ledgers previously replayed
from actual Alpaca SIP 5m bars (through Nov 6). No order, broker, network or V1 code.
Outcome fields are used ONLY after the candidate was determined by prior data.
"""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
from collections import defaultdict
from statistics import mean
from math import sqrt

SPLIT="2026-09-01"
CROSS=Path("/tmp/v2-run17-cross-sector-precision")
SEMI=Path("/tmp/v2-run16-semis-atr")
GOLD=Path("/tmp/v2-run18-research")

def wilson_lower(nwin:int,n:int)->float:
    if n==0:return 0.
    z=1.96;p=nwin/n;z2=z*z
    return (p+z2/(2*n)-z*sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)

def cost_return(gross_pct:float,price:float,quantity:int,friction_bps:int=30,commission_per_side:float=1.)->float:
    """One opening & one closing ticket. Modeled, not actual or universal fee."""
    if price<=0 or quantity<1 or friction_bps<0 or commission_per_side<0:
        raise ValueError("invalid cost model")
    return gross_pct-friction_bps/100-200*commission_per_side/(price*quantity)

def by_day_bootstrap(rows, value, seed:int=26, trials:int=1500):
    """Resample independent sessions, NOT correlated stock signals."""
    groups=defaultdict(list)
    for r in rows:groups[r["day"]].append(value(r))
    if len(groups)<2:return None
    day_means=[mean(v) for v in groups.values()]
    rng=random.Random(seed);n=len(day_means)
    vals=sorted(mean(day_means[rng.randrange(n)] for _ in range(n)) for _ in range(trials))
    return [round(vals[int(.025*(trials-1))],4),round(vals[int(.975*(trials-1))],4)]

def stats(rows, value, succ=None):
    seq=[value(x) for x in rows]
    n=len(seq);wins=sum((x>0) for x in seq) if succ is None else sum(succ(r) for r in rows)
    good=sorted(seq)
    return {"signals":n,"days":len({r["day"] for r in rows}),"wins":wins,
        "win_pct":round(100*wins/n,2) if n else None,
        "wilson95_lower_pct":round(100*wilson_lower(wins,n),2) if n else None,
        "mean_pct":round(mean(seq),4) if n else None,
        "median_pct":round(good[n//2],4) if n else None,
        "worst_pct":round(good[0],4) if n else None,
        "day_bootstrap_95_pct":by_day_bootstrap(rows,value)}

def split_rows(rows):
    return {"earlier":[x for x in rows if x["day"]<SPLIT],
            "later":[x for x in rows if x["day"]>=SPLIT]}

def cross_sector(summary,events):
    sectors={}
    for sector,row in summary["sectors"].items():
        k=row["earlier_best_shadow"]
        if not k:
            sectors[sector]={"status":"NO_EARLIER_POLICY"};continue
        xs=events[sector+"_"+k]
        partitions=split_rows(xs);results={}
        for period,items in partitions.items():
            results[period]={"source_policy":k,"direction":items[0]["direction"] if items else None,
                "price_mark_stress":{}}
            for qty in (1,5,10):
                for bps in (15,30,60):
                    key=f"{qty}shares_{bps}bps_1USD_per_side"
                    results[period]["price_mark_stress"][key]=stats(items,lambda x:cost_return(
                        x["gross"],x["entry"],qty,bps))
            results[period]["legacy_30bps_no_ticket"]=stats(items,lambda x:x["net30"])
        sectors[sector]=results
    return sectors

def gold_sector(summary,events):
    k=summary["best_train_shadow"]
    if not k:return {"status":"NO_EARLIER_POLICY"}
    xs=events[k];res={}
    for period,items in split_rows(xs).items():
        res[period]={"source_policy":k,"direction":items[0]["direction"] if items else None,
            "mark_stress":{}}
        for q in (1,5,10):
            for bps in (15,30,60):
                res[period]["mark_stress"][f"{q}shares_{bps}bps_1USD_per_side"]=stats(
                    items,lambda x:cost_return(x["gross_pct"],x["entry_mark"],q,bps))
        res[period]["legacy_30bps_no_ticket"]=stats(items,lambda x:x["net30"])
    return res

def downside(events):
    """Already causal as-of signals from prior replay. No posthoc threshold tuning."""
    out={}
    for rule in ("fixed2","fixed2p5","fixed3"):
        candidate=events[rule]
        x={r["day"]+"|"+r["symbol"]:r for r in candidate}
        if len(x)!=len(candidate):
            raise ValueError("duplicate signal/day (double counted)")
        partitions=split_rows(candidate)
        grouped={}
        for period,rows in partitions.items():
            major=sum(bool(r["major"]) for r in rows)
            nonmajor=len(rows)-major
            returns=lambda r:r["sell_adv_30bp"]
            extreme_up=sum(r["sell_adv_30bp"]<-2 for r in rows)
            grouped[period]={"event_quality_vs_next_open":stats(rows,returns),
                "major_hits":major,"nonmajor_warnings":nonmajor,
                "warnings_with_2pp_or_more_missed_rebound":extreme_up,
                "major_before_minus5_hits":sum(r["major"] and r["before_minus5"] for r in rows),
                "major_pre_regular_open_hits":sum(r["major"] and "T09:" not in r["at"] and
                     ("T04:" in r["at"] or "T05:" in r["at"] or "T06:" in r["at"] or "T07:" in r["at"] or "T08:" in r["at"]) for r in rows),
                "earliest_major_warning":min((r["at"] for r in rows if r["major"]),default=None)}
        out[rule]=grouped
    return out

def run(cross=CROSS,semi=SEMI,gold=GOLD):
    jc=json.loads((cross/"results.compact.json").read_text())
    ec=json.loads((cross/"results.json.events.json").read_text())
    jg=json.loads((gold/"gold_lead_lag.compact.json").read_text())
    eg=json.loads((gold/"gold_lead_lag.json.events.json").read_text())
    es=json.loads((semi/"adaptive_results.json.events.json").read_text())
    return {"source":"locked historical actual timestamped Alpaca SIP 5m event audits",
        "training_split":SPLIT,"source_dataset_end":"2026-11-06",
        "sector_sessions":jc["sector_counts"],"gold_sector_sessions":jg["status"],
        "cross_sector":cross_sector(jc,ec),"gold":gold_sector(jg,eg),
        "semiconductor_sell_warning_costs":downside(es),
        "safety":"NO BROKER CONTACT; NO PAPER OR LIVE ORDERS",
        "limitations":["Replay uses price marks not executable NBBO/BOATS asks/bids or fills",
                       "Ticket model illustrative: $1 per side, not Alpaca fee schedule",
                       "Sample policies locked by earlier-period selection; all remain NO GO",
                       "Indicators use completed 5m bars and prior five completed sessions from source replays",
                       "No synchronized earnings/news/futures or matched V1 executions; no causal prediction from retrospective labels",
                       "Resampled sessions are only a descriptive uncertainty estimate, not fully OOS proof"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=run()
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True))
    for s,r in result["cross_sector"].items():
        print(s,r.get("later",{}).get("price_mark_stress",{}).get("1shares_30bps_1USD_per_side"))
    print("GOLD",result["gold"]["later"]["mark_stress"]["1shares_30bps_1USD_per_side"])
    for k,r in result["semiconductor_sell_warning_costs"].items():
        print(k,r["later"])

if __name__=="__main__":main()