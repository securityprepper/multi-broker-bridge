#!/usr/bin/env python3
"""READ-ONLY per-minute, two-year sector/peer-aligned early direction predictor.
Prospective features use only completed RTH minute m or earlier.
All outcomes are after minute m, and split 2024-25 train / 2025-26
validation / final 2026 holdout. No broker executions.
"""
from pathlib import Path
import csv, collections, datetime as dt, gzip, json, math, statistics, os
MAIN=Path("/var/lib/securityprepper-two-year-intraday-research")
SRC=MAIN/"minute_early_features_20241120_20261120.jsonl.gz"
UNIV=json.loads(Path("/var/lib/securityprepper-two-year-sector-backtest/full_membership_frozen.json").read_text())
PRIORITY=json.loads(Path("/opt/securityprepper/quality-opportunity-watch/priority_universe.json").read_text())["groups"]
GROUPS=UNIV["groups"]
map_sector={}
# Priority selection order: each stock attributed to one primary group.
for g in ("Semiconductors","Cybersecurity","Storage","AI infrastructure"):
 for s in PRIORITY.get(g,[]):
  if s not in map_sector: map_sector[s]=g if g!="Storage" else "Semiconductors"
for g,x in GROUPS.items():
 for s in x["peers"]:map_sector.setdefault(s,g)
for g,x in GROUPS.items():
 map_sector.setdefault(x["etf"],g)
etf_for={g:x["etf"] for g,x in GROUPS.items()}
# Need sector membership counts excluding each target stock.
member_of=collections.defaultdict(list)
for g,x in GROUPS.items():
 for s in x["peers"]:member_of[s].append(g)
for s in PRIORITY.get("Semiconductors",[]):
 if s not in member_of:member_of[s].append("Semiconductors")
for s in PRIORITY.get("Cybersecurity",[]):
 if s not in member_of:member_of[s].append("Cybersecurity")
for s in PRIORITY.get("AI infrastructure",[]):
 if s not in member_of:member_of[s].append("AI infrastructure")
for s in PRIORITY.get("Storage",[]):
 if s not in member_of:member_of[s].append("Semiconductors")
sector_references=set(etf_for.values())|{"SPY"}
def ratio(p0,p1):
 return 100*(p1/p0-1) if p0 and p1 and p0>0 else None
def segment(t):
 return "TRAIN" if t<="2025-11-19" else ("VALIDATE" if t<="2026-05-19" else "HOLDOUT")
def stats_obj():
 return {"n":0,"sum_future_gross_pct":0.0,"sum_squares":0.0,"correct_future":0,"class_counts":collections.Counter(),"n_days":0}
def update(o,r,day_class):
 o["n"]+=1;o["sum_future_gross_pct"]+=r;o["sum_squares"]+=r*r
 o["correct_future"]+=int(r>.25);o["class_counts"][day_class]+=1
def snapshot(x):
 n=x["n"];mu=x["sum_future_gross_pct"]/n if n else None
 sd=math.sqrt(max(0,(x["sum_squares"]-x["sum_future_gross_pct"]**2/n)/(n-1))) if n>1 else None
 return {"n":n,"gross_mean_pct":round(mu,4) if mu is not None else None,
         "gross_stdev":round(sd,4) if sd is not None else None,
         "net_proxy_mean_pct":round(mu-.25,4) if mu is not None else None,
         "win_gt_025_pct":round(100*x["correct_future"]/n,2) if n else None,
         "label_counts":dict(x["class_counts"])}
def load():
 benchmarks={};breadth=collections.defaultdict(lambda:[[0]*120,[0]*120,[0]*120])
 read=0
 with gzip.open(SRC,"rt") as f:
  for line in f:
   x=json.loads(line);read+=1;s=x["symbol"];d=x["date"]
   if s in sector_references:
    benchmarks[(s,d)]={
      "open":x["rth_open"],"prev":x.get("prev_rth_close"),
      "close":x["minute_close"],"flatten":x.get("hard_flat_price")}
   sectors=member_of.get(s,())
   if sectors:
    start=x["rth_open"]
    if start<5:continue
    for i,c in enumerate(x["minute_close"]):
     if c is None or c<5:continue
     p=ratio(start,c)
     for g in sectors:
      out=breadth[(g,d)]
      out[2][i]+=1
      if p is not None and p>=.10:out[0][i]+=1
      if p is not None and p<=-.10:out[1][i]+=1
 print("REF_READY",len(benchmarks),"BREADTH_DAYS",len(breadth),"SOURCE_ROWS",read,flush=True)
 return benchmarks,breadth
def main():
 refs,breadth=load()
 global_stats=collections.defaultdict(stats_obj)
 ticker_stats=collections.defaultdict(stats_obj)
 minute_census=collections.defaultdict(stats_obj)
 per_day=collections.defaultdict(collections.Counter)
 exclude=collections.Counter()
 last=None;line_count=0
 outp=MAIN/"minute_predictor_per_symbol_chosen_signal.csv"
 # Every RTH minute is tested at strict 0.25/0.10/0.10 combined with fresh sector breadth.
 with gzip.open(SRC,"rt") as src:
  for line in src:
   x=json.loads(line);line_count+=1
   s=x["symbol"];d=x["date"];g=map_sector.get(s)
   if not g or s in sector_references:continue
   e=etf_for.get(g)
   sr=refs.get(("SPY",d));er=refs.get((e,d))
   flat=x.get("hard_flat_price")
   if not (sr and er and flat and flat>0):exclude["NO_MARKET_ETF_OR_FLAT"]+=1;continue
   if x["rth_open"]<5:exclude["UNDER5_OPEN"]+=1;continue
   po=x["rth_open"];pclose=x["minute_close"];qmarket=sr["close"];qsector=er["close"]
   peers=breadth.get((g,d))
   if not peers:exclude["NO_PEER"]+=1;continue
   for minute in range(1,121):
    i=minute-1
    if i>=len(pclose) or i>=len(qmarket) or i>=len(qsector):continue
    cp=pclose[i];bm=qmarket[i];be=qsector[i]
    if cp is None or cp<5 or bm is None or be is None or not peers[2][i]:continue
    pr=ratio(po,cp);mpr=ratio(sr["open"],bm);epr=ratio(er["open"],be)
    if pr is None or mpr is None or epr is None:continue
    n=peers[2][i]
    # Original peers may include this symbol. Subtract self to avoid confirmation tautology.
    ispeer=(s in member_of and g in member_of[s])
    n-=int(ispeer)
    if n<3:continue
    for sign in (1,-1):
     self_positive=sign*pr>=.25
     market_positive=sign*mpr>=.10
     sector_positive=sign*epr>=.15
     peer_count=(peers[0][i] if sign==1 else peers[1][i])-(int(sign*pr>=.10) if ispeer else 0)
     peer_fraction=peer_count/n
     if not (self_positive and market_positive and sector_positive and peer_fraction>=.65):continue
     # Future from completed minute i to contemporaneous 13:40 flat; no +1m lookahead in features.
     # This is diagnostic and explicitly NOT an executable entry.
     future=sign*ratio(cp,flat)
     split=segment(d)
     update(global_stats[(minute,sign,split)],future,x["label"])
     update(ticker_stats[(s,minute,sign,split)],future,x["label"])
     update(minute_census[(minute,split)],future,x["label"])
     per_day[(s,d,split)][sign]+=1
   if line_count%30000==0:print("PROGRESS",line_count,flush=True)
 summary={}
 for minute in range(1,121):
  for sign in (+1,-1):
   for split in ("TRAIN","VALIDATE","HOLDOUT"):
    z=global_stats[(minute,sign,split)]
    if z["n"]:summary[f"{minute}:{sign}:{split}"]=snapshot(z)
 # For each stock and side, freeze the signal minute using train data alone,
 # then display independent validation and final untouched holdout.
 picks=[]
 for s in sorted(set(k[0] for k in ticker_stats)):
  for sign in (+1,-1):
   choices=[]
   for m in range(1,121):
    train=ticker_stats.get((s,m,sign,"TRAIN"))
    if not train or train["n"]<30:continue
    st=snapshot(train)
    # Penalize sparse, high-variance positive means; frozen before later periods.
    mu=st["net_proxy_mean_pct"]
    std=st["gross_stdev"] or 100
    score=mu-std/(train["n"]**.5)
    choices.append((score,m))
   if not choices:continue
   score,chosen=sorted(choices,reverse=True)[0]
   train=ticker_stats[(s,chosen,sign,"TRAIN")]
   valid=ticker_stats.get((s,chosen,sign,"VALIDATE")) or stats_obj()
   test=ticker_stats.get((s,chosen,sign,"HOLDOUT")) or stats_obj()
   tr,va,te=map(snapshot,(train,valid,test))
   pick={"symbol":s,"side":"LONG" if sign==1 else "SHORT_RESEARCH_ONLY","first_half_training_selected_minute":chosen,"train":tr,"validation":va,"holdout":te,"train_risk_adjusted_score":round(score,4)}
   # A narrow evidence gate; no live trade authorization even if passed.
   pick["robust_directional_edge_candidate"]=(train["n"]>=30 and valid["n"]>=20 and test["n"]>=20 and
      tr["net_proxy_mean_pct"]>.0 and va["net_proxy_mean_pct"]>.0 and te["net_proxy_mean_pct"]>.0 and
      tr["win_gt_025_pct"]>=55 and va["win_gt_025_pct"]>=55 and te["win_gt_025_pct"]>=55)
   picks.append(pick)
 report={"schema":1,"hypothesis":"Early minute stock+SPY+sector ETF+peer breadth alignment predicts forward return to 13:40 CT hard flat","session_definition":"15:00 CT close; 12:00 CT on official early close","source":"Split-adjusted Alpaca SIP completed 1m; stock floor at observation","train":"2024-11-20 through 2025-11-19","validation":"2025-11-20 through 2026-05-19","holdout":"2026-05-20 through 2026-11-20","cost_proxy":"Fixed conservative -0.25 pct total roundtrip, NOT actual quote spread/fills/fees","global_minute_stats":summary,"per_symbol_picks":picks,"exclusions":dict(exclude),"ticker_days":len(per_day),"rows_read":line_count,
 "hypothetical_GO":False,"trading_authorization":False}
 path=MAIN/"minute_by_minute_first120_market_sector_breadth_holdout.json";path.write_text(json.dumps(report,indent=2))
 with outp.open("w",newline="") as f:
  cols=["symbol","side","train_selected_minute","train_n","train_net_proxy_mean_pct","val_n","val_net_proxy_mean_pct","holdout_n","holdout_net_proxy_mean_pct","holdout_positive_rate","tentative_edge"]
  w=csv.writer(f);w.writerow(cols)
  for a in picks:
   w.writerow([a["symbol"],a["side"],a["first_half_training_selected_minute"],a["train"]["n"],a["train"]["net_proxy_mean_pct"],a["validation"]["n"],a["validation"]["net_proxy_mean_pct"],a["holdout"]["n"],a["holdout"]["net_proxy_mean_pct"],a["holdout"]["win_gt_025_pct"],a["robust_directional_edge_candidate"]])
 print("FINISHED",json.dumps({"rows":line_count,"ticker_days":len(per_day),"candidate_mn_sign_stats":len(summary),"picked":len(picks),"tentative":sum(x["robust_directional_edge_candidate"] for x in picks),"exclusions":dict(exclude)}),flush=True)
 print("PICKS_TOP_VALIDATED",[(x["symbol"],x["side"],x["first_half_training_selected_minute"],x["train"]["net_proxy_mean_pct"],x["validation"]["net_proxy_mean_pct"],x["holdout"]["net_proxy_mean_pct"]) for x in picks if x["robust_directional_edge_candidate"]][:18],flush=True)
if __name__=="__main__":main()