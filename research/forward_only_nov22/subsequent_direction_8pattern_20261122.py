#!/usr/bin/env python3
"""Research-only: identify genuinely AFTER-signal UP/DOWN patterns at beginning
of the day. Predeclared families, first qualifying signal per symbol/day/side
and rule, segment-separated validation; do not trade or modify production.
Retrospective development has already exposed some 2026 outcomes: this is
NOT a pristine untouched hypothesis holdout.
"""
from pathlib import Path
import csv,collections,datetime as dt,gzip,importlib.util,json,math,statistics
from zoneinfo import ZoneInfo
R=Path("/var/lib/securityprepper-two-year-intraday-research")
SOURCE=R/"minute_early_features_20241120_20261120.jsonl.gz"
DIRECTION=Path("/tmp/srm_2yr_early_direction_20261121.py")
p=importlib.util.spec_from_file_location("dir",DIRECTION);q=importlib.util.module_from_spec(p);p.loader.exec_module(q)
ETFS=q.etf_for
GATE=Path("/var/cache/securityprepper-holiday/task-gate.json")
def stamp(x):return dt.datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(dt.timezone.utc)
def gate():
 j=json.loads(GATE.read_text());n=dt.datetime.now(dt.timezone.utc)
 if not(j.get("schema_version")==1 and j.get("status_valid") is True and j.get("calendar_coverage_ok") is True and j.get("timezone")=="America/Chicago" and j.get("paused") is False and stamp(j["published_at"])<=n<stamp(j["valid_until"]) and n<stamp(j["next_check_at"])):
  raise RuntimeError("GATE_NOT_TRUSTED_UNPAUSED")
 return j.get("calendar_revision")
def seg(d):return "TRAIN" if d<="2025-11-19" else ("VALIDATE" if d<="2026-05-19" else "HOLDOUT")
def ret(p0,p1):return 100*(p1/p0-1) if p0 and p1 and p0>0 else None
def stats():
 return {"n":0,"future_up":0,"future_down":0,"future_mixed":0,"positive":0,"gross_sum":0.,"gross_sq_sum":0.,"after25bp_wins":0,"days":set(),"symbol_day":set(),"market_beat":0,"market_known":0,"sector_beat":0,"sector_known":0,"benchmark_sum":0.}
def add(o,ev):
 z=ev["after_signal_direction_pct"];o["n"]+=1;o["gross_sum"]+=z;o["gross_sq_sum"]+=z*z;o["positive"]+=int(z>0);o["after25bp_wins"]+=int(z>.25)
 o["future_up"]+=int(z>=.75);o["future_down"]+=int(z<=-.75);o["future_mixed"]+=int(-.75<z<.75)
 o["days"].add(ev["date"]);o["symbol_day"].add((ev["symbol"],ev["date"]))
 if ev["benchmark_signed_pct"] is not None:
  o["market_beat"]+=int(z>ev["benchmark_signed_pct"]);o["market_known"]+=1;o["benchmark_sum"]+=ev["benchmark_signed_pct"]
 if ev["sector_signed_pct"] is not None:
  o["sector_beat"]+=int(z>ev["sector_signed_pct"]);o["sector_known"]+=1
def summary(o):
 n=o["n"]
 if not n:return {"n":0}
 mu=o["gross_sum"]/n
 sd=math.sqrt(max(0.,(o["gross_sq_sum"]-o["gross_sum"]**2/n)/(n-1))) if n>1 else None
 return {"n":n,"distinct_days":len(o["days"]),"distinct_symbol_days":len(o["symbol_day"]),
 "future_signed_mean_pct":round(mu,4),"cost_25bp_mean_proxy_pct":round(mu-.25,4),
 "positive_pct":round(100*o["positive"]/n,2),"net_positive_gt25bp_pct":round(100*o["after25bp_wins"]/n,2),
 "forward_UP_pct":round(100*o["future_up"]/n,2),"forward_DOWN_pct":round(100*o["future_down"]/n,2),
 "forward_MIXED_pct":round(100*o["future_mixed"]/n,2),
 "stock_exceeds_signed_SPY_pct":round(100*o["market_beat"]/o["market_known"],2) if o["market_known"] else None,
 "market_n":o["market_known"],"avg_signed_SPY_future_pct":round(o["benchmark_sum"]/o["market_known"],4) if o["market_known"] else None,
 "stock_exceeds_signed_sector_pct":round(100*o["sector_beat"]/o["sector_known"],2) if o["sector_known"] else None,
 "sector_n":o["sector_known"],
 "naive_std_pct":round(sd,4) if sd is not None else None
 }
def main():
 sourcegate=gate()
 # Model's source observations are first-120m completed SIP 1m trade closes.
 # Benchmarks must be same-date and same-time as signal with no lookahead.
 refs,breadth=q.load()
 gate()
 totals=collections.defaultdict(stats)
 pairs=collections.defaultdict(stats)
 symbols=collections.defaultdict(stats)
 minute=collections.defaultdict(stats)
 failures=collections.Counter()
 results=[]
 names=["SECTOR_LEAD_STOCK_LAG_TURN","MARKET_SECTOR_PEER_CONTINUATION",
        "LARGE_GAP_REJECTED","OPPOSITE_GAP_REVERSAL","CALM_OPENING_BREAKOUT",
        "STRONG_GAP_CONTINUATION","PEER_EARLY_BREADTH","OPEN_RANGE_CONFIRMED_BREAK"]
 # Bound later-test selection to time only; no future outcome in eligibility.
 csize=0
 with gzip.open(SOURCE,"rt") as src:
  for j,line in enumerate(src,1):
   x=json.loads(line);s=x["symbol"];d=x["date"]
   g=q.map_sector.get(s);sector=ETFS.get(g)
   if not g or not sector or s in q.sector_references:continue
   r=refs.get(("SPY",d));e=refs.get((sector,d));peers=breadth.get((g,d))
   if not(r and e and peers):failures["MISSING_BENCHMARKS"]+=1;continue
   flat=x.get("hard_flat_price");openp=x["rth_open"];prev=x.get("prev_rth_close")
   if not flat or flat<=0 or not openp or openp<5 or not prev or prev<=0:continue
   bf=e.get("flatten");mf=r.get("flatten")
   closes=x["minute_close"];highs=x["minute_high"];lows=x["minute_low"];sp=r["close"];sc=e["close"]
   used=set();gpp=ret(prev,openp)
   for m in range(6,121):
    idx=m-1
    if idx>=len(closes):continue
    price=closes[idx]
    if price is None or price<5:continue
    if idx>=len(sp) or idx>=len(sc) or sp[idx] is None or sc[idx] is None:continue
    sp0=sp[idx];sc0=sc[idx]
    if sp0<5 or sc0<5:continue
    fromopen=ret(openp,price);fromopen_m=ret(r["open"],sp0);fromopen_e=ret(e["open"],sc0)
    last5=ret(closes[idx-5],price) if closes[idx-5] is not None else None
    last3=ret(closes[idx-3],price) if idx>=3 and closes[idx-3] is not None else None
    sectorlast5=ret(sc[idx-5],sc0) if sc[idx-5] is not None else None
    marketlast5=ret(sp[idx-5],sp0) if sp[idx-5] is not None else None
    if None in (fromopen,fromopen_m,fromopen_e,last5,last3,sectorlast5,marketlast5):continue
    minutes_recent=closes[idx-5:idx+1]
    if any(t is None for t in minutes_recent):continue
    # Exclude own stock from current-sector breadth from since-open.
    n0=peers[2][idx] - int(s in q.member_of and g in q.member_of[s])
    if n0<3:continue
    for direction in (+1,-1):
     same_count=peers[0][idx] if direction==1 else peers[1][idx]
     if s in q.member_of and g in q.member_of[s]:
      if direction*fromopen>=.10:same_count-=1
     pfrac=same_count/n0
     f0=direction*fromopen;g0=direction*gpp
     m0=direction*fromopen_m;e0=direction*fromopen_e
     l5=direction*last5;l3=direction*last3
     lm=direction*marketlast5;le=direction*sectorlast5
     eligible=[]
     # Sector and peer strength precedes fresh stock turnaround, not an extended chase.
     if m>=10 and -.6<=f0<=.1 and l3>=.15 and e0>=.3 and m0>=.10 and pfrac>=.7 and le>=.15:
      eligible.append("SECTOR_LEAD_STOCK_LAG_TURN")
     if m>=6 and f0>=.35 and l5>=.20 and e0>=.25 and m0>=.10 and pfrac>=.70 and le>=.10:
      eligible.append("MARKET_SECTOR_PEER_CONTINUATION")
     # Large previous-close gap in the opposite direction is REJECTED by early
     # stock reversal and sector agreement, investigate future continuation.
     if m<=45 and -g0>=1.5 and f0>=.5 and l5>=.20 and m0>=0.1 and e0>=.15 and pfrac>=.6:
      eligible.append("LARGE_GAP_REJECTED")
     if m<=45 and -g0>=2.5 and f0>=.3 and l3>=.20 and lm>=.1 and le>=.15:
      eligible.append("OPPOSITE_GAP_REVERSAL")
     if m>=15 and abs(gpp)<.5 and f0>=.7 and l5>=.25 and e0>=.25 and m0>=.15 and pfrac>=.65:
      eligible.append("CALM_OPENING_BREAKOUT")
     if m<=30 and g0>=1.5 and f0>=.35 and l5>=.2 and e0>=.25 and m0>=.15 and pfrac>=.65:
      eligible.append("STRONG_GAP_CONTINUATION")
     if m>=8 and pfrac>=.8 and f0>=.2 and l5>=.05 and e0>=.2 and m0>=.1 and le>=.1:
      eligible.append("PEER_EARLY_BREADTH")
     if m>=15 and f0>=.2 and pfrac>=.65 and l3>=.15 and m0>=.1 and e0>=.2:
      # Market opening range (first ten completed minutes); signal at least 5
      # minutes after opening range became known, not same-bar high anticipation.
      if all(z is not None for z in highs[:10]+lows[:10]):
       high10=max(highs[:10]);low10=min(lows[:10])
       if direction*ret(openp,price)>.2 and \
          ((direction==1 and price>high10*1.002) or (direction==-1 and price<low10*.998)) and \
          ((direction==1 and closes[idx-1]>high10) or (direction==-1 and closes[idx-1]<low10)):
        eligible.append("OPEN_RANGE_CONFIRMED_BREAK") # actually confirmed OPEN RANGE 2-BAR BREAKOUT
     for name in eligible:
      key=(name,direction)
      if key in used:continue
      used.add(key)
      if not flat or flat<5:continue
      # Contemporaneous signal price is completed minute close. The notional
      # return to 13:40 is indicative, not a broker bid/ask-executable fill.
      ret_s=ret(price,flat); signed=direction*ret_s
      mfuture=direction*ret(sp0,mf) if mf and mf>0 else None
      efuture=direction*ret(sc0,bf) if bf and bf>0 else None
      event={
       "symbol":s,"date":d,"side":"UP" if direction==1 else "DOWN",
       "rule":name,"sector":g,"minute_after_open":m,
       "source_time_CT":f"{8+(30+m)//60:02d}:{(30+m)%60:02d}",
       "segment":seg(d),"signal_close":round(price,5),"flat_price":round(flat,5),
       "signed_stock_return_from_signal_to_flat_pct":round(signed,4),
       "after_signal_direction_pct":signed,
       "realized_remaining_class":"UP" if ret_s>=.75 else ("DOWN" if ret_s<=-.75 else "MIXED"),
       "benchmark_signed_pct":mfuture,"sector_signed_pct":efuture,
       "features":{"gap_from_prev_close_pct":round(gpp,4),
                   "stock_move_from_open_pct":round(fromopen,4),
                   "stock_recent_5m_pct":round(last5,4),
                   "SPY_from_open_pct":round(fromopen_m,4),
                   "sector_from_open_pct":round(fromopen_e,4),
                   "peer_same_direction_fraction":round(pfrac,4)},
       "simulated_fill":False,"cost_proxy_roundtrip_pct":.25
      }
      add(totals[(name,direction,seg(d))],event)
      add(pairs[(name,direction,seg(d),g)],event)
      add(symbols[(name,direction,seg(d),s)],event)
      add(minute[(name,direction,seg(d),m)],event)
      results.append({k:v for k,v in event.items() if k not in ("features","after_signal_direction_pct")})
   if j%30000==0:
    gate()
    print("EVAL_PROGRESS",j,"events",len(results),flush=True)
 print("EVENTS",len(results),"TOTALS",len(totals),flush=True)
 group=[]
 for (name,direction,period),z in sorted(totals.items()):
  group.append({"rule":name,"side":"UP" if direction==1 else "DOWN","period":period,**summary(z)})
 each=[]
 for (name,direction,period,g),z in sorted(pairs.items()):
  each.append({"rule":name,"side":"UP" if direction==1 else "DOWN","period":period,"sector":g,**summary(z)})
 each_sym=[]
 for (name,direction,period,s),z in sorted(symbols.items()):
  each_sym.append({"rule":name,"side":"UP" if direction==1 else "DOWN","period":period,"symbol":s,**summary(z)})
 # Train-only per symbol/rule selection, check independent later periods,
 # but no "independent untouched hypothesis holdout" due to previous look.
 cand=collections.defaultdict(list)
 for (name,dir0,period,s),z in symbols.items():
  if period!="TRAIN" or z["n"]<25:continue
  t=summary(z)
  # Reward gross signal-to-future effect only after simulated spread allowance,
  # but penalize low training denominator and directional noise.
  score=t["cost_25bp_mean_proxy_pct"]-(t["naive_std_pct"] or 100)/z["n"]**.5
  cand[s].append((score,name,dir0))
 selections=[]
 for s,a in sorted(cand.items()):
  sc,n,dr=max(a)
  val=summary(symbols.get((n,dr,"VALIDATE",s),stats()))
  test=summary(symbols.get((n,dr,"HOLDOUT",s),stats()))
  train=summary(symbols[(n,dr,"TRAIN",s)])
  good=(val["n"]>=15 and test["n"]>=20 and
        train["cost_25bp_mean_proxy_pct"]>.0 and val["cost_25bp_mean_proxy_pct"]>.0 and
        test["cost_25bp_mean_proxy_pct"]>.0 and
        val["net_positive_gt25bp_pct"]>=55 and test["net_positive_gt25bp_pct"]>=55 and
        val["stock_exceeds_signed_SPY_pct"]>=50 and test["stock_exceeds_signed_SPY_pct"]>=50)
  selections.append({"symbol":s,"rule":n,"side":"UP" if dr==1 else "DOWN","train":train,"validation":val,"holdout":test,
                     "date_separated_support":good,"trade_authorized":False})
 root={"schema":1,"cohort":"2024-11-20 through 2026-11-20","asof":dt.datetime.now(dt.timezone.utc).isoformat(),
       "signal_anchor":"every completed RTH 1m bar 8:36–10:30 CT, first qualifying event per symbol/day/rule/side",
       "forward_anchor":"post-signal price to required 13:40 CT flat, actual time-labeled bar close, not prior-close to day close",
       "no_true_untouched_hypothesis_cohort":"Prior research already inspected portions of later dates; label validation as exploratory and require fresh prospective sessions",
       "cost_proxy_pct":.25,"no_real_executable_bidask_or_fills":True,
       "source_calendar_gate_revision":sourcegate,"source_rows_read":j,"signal_event_count":len(results),"rules":names,
       "aggregates":group,"by_sector":each,"symbol_selected":selections}
 (R/"SUBSEQUENT_DIRECTION_EXPLORATORY_PATTERN_SCAN_20261122.json").write_text(json.dumps(root,indent=2))
 with (R/"SUBSEQUENT_DIRECTION_PATTERN_BY_PERIOD.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(group[0]));w.writeheader();w.writerows(group)
 with (R/"SUBSEQUENT_DIRECTION_PATTERN_BY_SECTOR.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(each[0]));w.writeheader();w.writerows(each)
 with (R/"SUBSEQUENT_DIRECTION_TRAIN_SELECTED_BY_SYMBOL.csv").open("w",newline="") as f:
  for x in selections:x.pop("trade_authorized",None)
  keys=["symbol","rule","side","train_n","train_net_proxy_pct","validation_n","validation_net_proxy_pct","holdout_n","holdout_net_proxy_pct","holdout_future_direction_win_pct","exploratory_supported"]
  w=csv.writer(f);w.writerow(keys)
  for x in selections:
   t,v,h=x["train"],x["validation"],x["holdout"]
   w.writerow([x["symbol"],x["rule"],x["side"],t.get("n",0),t.get("cost_25bp_mean_proxy_pct"),v.get("n",0),v.get("cost_25bp_mean_proxy_pct"),h.get("n",0),h.get("cost_25bp_mean_proxy_pct"),h.get("net_positive_gt25bp_pct"),x["date_separated_support"]])
 print("DONE","patterns",len(group),"events",len(results),"train_chosen_symbol_models",len(selections),
       "exploratory_supported",sum(x["date_separated_support"] for x in selections),flush=True)
 for x in group:
  if x["period"]=="HOLDOUT":
   print("HOLDOUT",x["rule"],x["side"],x["n"],x.get("distinct_days"),x.get("cost_25bp_mean_proxy_pct"),x.get("net_positive_gt25bp_pct"),x.get("stock_exceeds_signed_SPY_pct"),flush=True)
if __name__=="__main__":main()