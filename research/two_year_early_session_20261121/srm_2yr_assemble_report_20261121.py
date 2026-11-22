#!/usr/bin/env python3
"""Concise accountable two-year intraday research report and per-symbol census.
Only research data, no broker actions. Write to root-owned isolated output.
"""
from pathlib import Path
import csv,collections,datetime as dt,json,math,statistics
R=Path("/var/lib/securityprepper-two-year-intraday-research")
CLASS=json.loads((R/"rth_daily_classifier_summary.json").read_text())
PREV=json.loads((R/"secondary_previous_close_end_classification.json").read_text())
EARLY=json.loads((R/"minute_by_minute_first120_market_sector_breadth_holdout.json").read_text())
NIGHT=json.loads((R/"premarket_510minute_priorclose_market_sector_holdout.json").read_text())
STOP=json.loads((R/"trailing_stops_train_validate_untouched_holdout.json").read_text())
MATCH=json.loads((R/"MATCHED_STOP_VALIDATION_SUMMARY.json").read_text())
RULES=json.loads((R/"first_120_minute_rule_events_summary.json").read_text())
U=json.loads(Path("/var/lib/securityprepper-two-year-early-session-research/manifest_config.json").read_text())
FROZEN=json.loads(Path("/var/lib/securityprepper-two-year-sector-backtest/full_membership_frozen.json").read_text())
PRIORITY=json.loads(Path("/opt/securityprepper/quality-opportunity-watch/priority_universe.json").read_text())
etfs={v["etf"] for v in FROZEN["groups"].values()}|{"SPY","SOXX","IGV","SOXL"}
primary={}
for g,v in PRIORITY["groups"].items():
 for sym in v:primary.setdefault(sym,g)
for g,v in FROZEN["groups"].items():
 for sym in v["peers"]:primary.setdefault(sym,g)
 for sym in [v["etf"]]:primary.setdefault(sym,g+" ETF")
# Compare LONG versus SHORT from TRAIN-ONLY score, never the holdout.
rth={};rth_score={}
for x in EARLY.get("per_symbol_picks",[]):
 tr=x.get("train",{});n=tr.get("n",0)
 if n<30 or tr.get("net_proxy_mean_pct") is None:continue
 std=tr.get("gross_stdev") or 100
 score=tr["net_proxy_mean_pct"]-std/(n**.5)
 if score>rth_score.get(x["symbol"],float("-inf")):
  rth[x["symbol"]]=x;rth_score[x["symbol"]]=score
pre={x["symbol"]:x for x in NIGHT.get("per_symbol_training_time_choice",[]) if "train" in x}
best={x["symbol"]:x for x in MATCH.get("selected_picks",[]) if "train" in x}
# Current last-completed regular session is a market-data evidence watermark,
# not a fresh intraday quote; research-only, never a new BUY recommendation.
last={}
with (R/"daily_classes_20241120_20261120.csv").open(newline="") as f:
 for x in csv.DictReader(f):
  if x["date"]=="2026-11-20":
   last[x["symbol"]]=(float(x["split_adj_rth_close"]),x["date"])
counts=collections.Counter();classified=[]
for s in U["symbols"]:
 c=CLASS["each_symbol"].get(s,{})
 t=PREV["by_symbol"].get(s,{})
 r=rth.get(s,{})
 n=pre.get(s,{})
 z=best.get(s,{})
 t0=z.get("train",{});v0=z.get("validation",{});h0=z.get("holdout",{})
 rr=r.get("validation",{});rh=r.get("holdout",{})
 nn=n.get("validate",{});nh=n.get("holdout",{})
 hist_last=last.get(s)
 status="HISTORICAL_NONTRADEABLE_REFERENCE" if s in etfs else "HISTORICAL_ORDINARY_STOCK_NOT_TRADE_AUTHORIZED"
 if not hist_last:status="NO_RECENT_LAST_RTH_PRICE_REF"
 elif hist_last[0]<5:status="UNDER5_HISTORICAL_NO_PUBLIC_TICKER"
 d={
 "ticker":s,"sector_or_category":primary.get(s,"OTHER_UNMAPPED"),"instrument_scope":status,
 "eligible_days":c.get("eligible_days",0),
 "UP_days":c.get("up",0),"DOWN_days":c.get("down",0),"MIXED_days":c.get("mixed",0),
 "UP_pct":round(100*c.get("up",0)/c["eligible_days"],2) if c.get("eligible_days") else None,
 "DOWN_pct":round(100*c.get("down",0)/c["eligible_days"],2) if c.get("eligible_days") else None,
 "MIXED_pct":round(100*c.get("mixed",0)/c["eligible_days"],2) if c.get("eligible_days") else None,
 "previous_close_UP_days":t.get("UP",0),"previous_close_DOWN_days":t.get("DOWN",0),"previous_close_FLAT_days":t.get("FLAT_RANGE",0),
 "last_RTH_date_ref":hist_last[1] if hist_last else None,
 "last_RTH_split_adjusted_trade_close_ref":round(hist_last[0],6) if hist_last else None,
 "premarket_train_selected_CT":n.get("minute_local_CT"),
 "premarket_selected_side":n.get("signal_side"),
 "premarket_validation_n":nn.get("observed"),
 "premarket_validation_open_to_flat_gross_pct":nn.get("mean_directional_rth_open_flat_pct"),
 "premarket_holdout_n":nh.get("observed"),
 "premarket_holdout_open_to_flat_gross_pct":nh.get("mean_directional_rth_open_flat_pct"),
 "premarket_train_val_hold_positive_proxy":n.get("positive_proxy_on_all_three_periods",False),
 "rth_train_selected_minute_after_open":r.get("first_half_training_selected_minute"),
 "rth_selected_side":r.get("side"),
 "rth_validation_n":rr.get("n"),
 "rth_validation_to_flat_net_proxy_pct":rr.get("net_proxy_mean_pct"),
 "rth_holdout_n":rh.get("n"),
 "rth_holdout_to_flat_net_proxy_pct":rh.get("net_proxy_mean_pct"),
 "rth_passes_3_periods":r.get("robust_directional_edge_candidate",False),
 "stop_train_selected_rule":z.get("rule"),
 "stop_train_selected_side":z.get("side"),
 "stop_train_selected_trailing_pct":z.get("train_chosen_stop_pct"),
 "stop_train_n":t0.get("n"),
 "stop_train_net_proxy_pct":t0.get("net_proxy_avg_pct"),
 "stop_validation_n":v0.get("n"),
 "stop_validation_net_proxy_pct":v0.get("net_proxy_avg_pct"),
 "stop_holdout_n":h0.get("n"),
 "stop_holdout_net_proxy_pct":h0.get("net_proxy_avg_pct"),
 "stop_holdout_win_pct":h0.get("win_pct"),
 "stop_holdout_hold_to_flat_net_proxy_pct":h0.get("hold_without_stop_avg_pct"),
 "stop_holdout_worst_net_proxy_pct":h0.get("worst_net_pct"),
 "stop_independent_proxy_positive":z.get("three_period_positive_and_better_than_hold",False),
 "strategy_readiness":"NO_BROKER_GO_RESEARCH_ONLY"
 }
 classified.append(d);counts[status]+=1
# User-facing shortlist filters historical last-session trade evidence >= $5
# and ordinary-stock classification; full historical census remains internal.
out=[x for x in classified if x["instrument_scope"]=="HISTORICAL_ORDINARY_STOCK_NOT_TRADE_AUTHORIZED"]
with (R/"PER_SYMBOL_TWO_YEAR_HISTORICAL_DAYS_AND_STOP_AUDIT.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(classified[0]));w.writeheader();w.writerows(classified)
with (R/"PUBLIC_ORDINARY_STOCK_LAST_SESSION_OVER5_HISTORICAL_RESEARCH.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(classified[0]));w.writeheader();w.writerows(out)
# Aggregate rule/stop/scenario combinations only as overlapping research scenarios:
# not a pooled independent trade series and NOT a tradable portfolio forecast.
stop_grid=MATCH["aggregates"]
with (R/"TRAILING_STOP_SENSITIVITY_BY_DIRECTION_AND_PERIOD.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(stop_grid[0]));w.writeheader();w.writerows(stop_grid)
# Key results and research limitation flags
reports={
"symbols_universe":len(U["symbols"]),"public_ordinary_stock_audits":len(out),
"symbol_day_classes":CLASS["total_eligible_symbol_days"],"classes":CLASS["class_total"],
"previous_close_basis":PREV["classification"],
"premarket_eligible_symbol_days":NIGHT["coverage"]["eligible_symbol_days"],
"premarket_true_midnight_available":NIGHT["coverage"]["has_first_trade_before_0010"],
"premarket_true_midnight_all_three_available":NIGHT["coverage"]["all_three_near_midnight"],
"premarket_missing_midnight":NIGHT["coverage"]["missing_trade_around_midnight"],
"premarket_symbol_choices":len(NIGHT.get("per_symbol_training_time_choice",[])),
"premarket_picks_positive_three_windows":sum(x.get("positive_proxy_on_all_three_periods",False) for x in NIGHT.get("per_symbol_training_time_choice",[])),
"first120_causal_signal_events":RULES["events_total"],"first120_split_counts":RULES["split_counts"],
"rth_time_picks":len(EARLY["per_symbol_picks"]),"rth_time_picks_validated":sum(x.get("robust_directional_edge_candidate",False) for x in EARLY["per_symbol_picks"]),
"simulated_stop_scenarios":STOP["simulated_cases"],
"simulated_stop_picks":len(MATCH["selected_picks"]),
"matched_stop_event_paths":MATCH["matched_event_paths"],
"matched_stop_cases":MATCH["matched_stop_cases"],
"matched_train_selected_symbols":MATCH["training_selected_symbols"],
"simulated_stop_picks_positive_both_and_vs_hold":sum(x.get("three_period_positive_and_better_than_hold",False) for x in MATCH["selected_picks"]),
"historical_last_session_filter":dict(counts),
"simulator_cost_per_side_assumed_pct":0.1,"true_spreads_unknown":True,"fee_fill_readbacks_unavailable":True,
"no_live_or_paper_order_authorized":True,"all_stop_candidates_research_only":True}
(R/"RESEARCH_BRIEF_METRICS_20261121.json").write_text(json.dumps(reports,indent=2))
print("BRIEF_METRICS",json.dumps(reports,sort_keys=True),flush=True)
print("HOLDOUT_STOP_GRID",json.dumps([a for a in stop_grid if a["period"]=="HOLDOUT"],sort_keys=True),flush=True)
print("SAMPLED_SYMBOL_RESULTS")
for sym in ["AMD","MU","NVDA","SNDK","WDC","PANW","CRWD","ZS","FTNT","NET","ANET","VRT","SOXX"]:
 x=next((a for a in classified if a["ticker"]==sym),None)
 if x:print(sym,"days",x["eligible_days"],"U/D/M",x["UP_days"],x["DOWN_days"],x["MIXED_days"],"trail",x["stop_train_selected_trailing_pct"],"rule",x["stop_train_selected_rule"],"OOS",x["stop_holdout_n"],x["stop_holdout_net_proxy_pct"],"validated",x["stop_independent_proxy_positive"])