"""Research-only intraday sector-neutral idiosyncratic dislocation.
Fixed rule specified before inspection of outcomes. No network, credentials, or broker actions.
"""
import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median, mean
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
SECTORS = {
    "semiconductors": ("SOXX", ("AMD", "MU", "NVDA")),
    "gold_miners": ("GDX", ("NEM", "AEM")),
    "energy": ("XLE", ("XOM", "CVX")),
    "financials": ("XLF", ("JPM", "BAC")),
    "industrials": ("XLI", ("CAT", "GE")),
    "healthcare": ("XLV", ("UNH", "LLY")),
    "software": ("IGV", ("MSFT", "CRM")),
}
CROSS = Path("/tmp/v2-run17-cross-sector-precision/alpaca_sip")
GOLD = Path("/tmp/v2-run15-sector-precision-work/alpaca_sip")
SEMI = Path("/tmp/semis_52wk_5min_sip_adjusted.json")
SEMI_PEERS = Path("/tmp/semis_peers_52wk_5min_adjusted.json")
TIME_KEYS = ("09:30", "09:55", "10:05", "11:05", "14:40")
FRICTIONS_PP = (0.30, 0.60)  # modeled round-trip, not actual broker quotes
RULE = {"decision_et": "10:00", "next_entry_et": "10:05", "one_hour_exit_et": "11:05",
        "mandatory_exit_et": "14:40", "sector_abs_30m_max_pct": 0.75,
        "peer_median_30m_min_pct": -0.25, "stock_vs_peer_underperformance_pct": 1.50,
        "min_price": 20, "min_30m_shares": 5000, "one_per_sector_date": True}

def date_time_key(ts):
    local = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(ET)
    return local.date().isoformat(), local.strftime("%H:%M")

def safe_bar(row):
    try:
        o, h, l, c, v = (float(x) for x in row[:5])
        if not all(map(math.isfinite, (o, h, l, c, v))) or min(o, h, l, c) <= 0 or v < 0:
            return None
        if l > min(o, c) or h < max(o, c): return None
        return (o, h, l, c, v)
    except (ValueError, TypeError): return None

def slim_bars(rows):
    result = defaultdict(dict)
    for t, *prices in rows:
        d, hhmm = date_time_key(t)
        if hhmm < "09:30" or hhmm > "14:40": continue
        bar = safe_bar(prices)
        if bar: result[d][hhmm] = bar
    return result

def load_bars():
    semi = json.loads(SEMI.read_text())
    semipeers = json.loads(SEMI_PEERS.read_text())
    out = {}
    for sym in {s for etf, names in SECTORS.values() for s in (etf, *names)}:
        if sym in semi: rows = [[k, *v] for k, v in semi[sym].items()]
        elif sym in semipeers: rows = [[k, *v] for k, v in semipeers[sym].items()]
        else:
            p = (GOLD if sym in {"GDX", "NEM", "AEM"} else CROSS) / f"{sym}_sip.json"
            rows = json.loads(p.read_text())["bars"]
        out[sym] = slim_bars(rows)
    return out

def pct(a, b):
    return (b / a - 1) * 100

def complete_asof(day, etf, stocks):
    """Only the 09:30 OPEN and bars through 09:55 are consulted to decide."""
    for sym in [etf, *stocks]:
        bars = day.get(sym, {})
        if any(t not in bars for t in ("09:30", "09:55")): return []
    etfret = pct(day[etf]["09:30"][0], day[etf]["09:55"][3])
    if abs(etfret) > RULE["sector_abs_30m_max_pct"]: return []
    r = {s: pct(day[s]["09:30"][0], day[s]["09:55"][3]) for s in stocks}
    candidates = []
    for s in stocks:
        other = [r[x] for x in stocks if x != s]
        peer = median(other)
        avg30vol = sum(day[s][t][4] for t in ("09:30", "09:35", "09:40",
                                             "09:45", "09:50", "09:55") if t in day[s])
        if (peer >= RULE["peer_median_30m_min_pct"] and
            peer - r[s] >= RULE["stock_vs_peer_underperformance_pct"] and
            day[s]["09:55"][3] >= RULE["min_price"] and
            avg30vol >= RULE["min_30m_shares"] and
            all(t in day[s] for t in ("09:30","09:35","09:40","09:45","09:50","09:55"))):
            candidates.append({"symbol": s, "relative_gap_pp": round(peer-r[s], 6),
                               "stock_30m_pct": round(r[s], 6), "peer_median_30m_pct": round(peer, 6),
                               "etf_30m_pct": round(etfret, 6),
                               "asof_signal_price": day[s]["09:55"][3]})
    return sorted(candidates, key=lambda c: (-c["relative_gap_pp"], c["symbol"]))

def stats(rows, metric):
    v = [r[metric] for r in rows if r.get(metric) is not None]
    if not v: return {"n": 0, "winners": 0, "win_rate": None, "mean_pct": None, "worst_pct": None}
    return {"n": len(v), "winners": sum(x > 0 for x in v), "win_rate": round(sum(x > 0 for x in v)/len(v), 4),
            "mean_pct": round(mean(v), 5), "worst_pct": round(min(v), 5)}

def sector_events(data):
    events, source_days, missing_entry = [], {}, defaultdict(int)
    for sector, (etf, names) in SECTORS.items():
        date_set = sorted(set(data[etf]).intersection(*(set(data[s]) for s in names)))
        source_days[sector] = len(date_set)
        for d in date_set:
            day = {s:data[s][d] for s in (etf,*names)}
            candidates = complete_asof(day, etf, names)
            if not candidates: continue
            c = candidates[0].copy()
            sym = c["symbol"]
            c.update({"date": d, "sector": sector, "source_complete_at_et": f"{d}T10:00:00",
                      "decision_at_et": f"{d}T10:00:00", "earliest_entry_at_et": f"{d}T10:05:00"})
            for time in ("10:05", "11:05", "14:40"):
                if time not in day[sym]: missing_entry[f"{sector}:{time}"] += 1
            for time, key in [("10:05", "entry"), ("11:05", "exit_60m"), ("14:40", "exit_flat")]:
                c[key] = day[sym][time][0] if time in day[sym] else None
            if c["entry"] is None:
                c.update({"net_60m_30bp": None, "net_flat_30bp": None,
                          "net_60m_60bp": None, "net_flat_60bp": None})
            else:
                for key, t in [("60m","exit_60m"), ("flat","exit_flat")]:
                    raw = pct(c["entry"],c[t]) if c[t] is not None else None
                    c[f"gross_{key}_pct"] = raw
                    for friction in FRICTIONS_PP:
                        c[f"net_{key}_{int(friction*100)}bp"] = round(raw-friction, 6) if raw is not None else None
            # Fair same-sector ETF / other-stock controls evaluated at same entry/exit times.
            for key, tm in [("60m","11:05"), ("flat","14:40")]:
                control = []
                for s in (etf,*[n for n in names if n!=sym]):
                    if "10:05" in day[s] and tm in day[s]:
                        control.append(pct(day[s]["10:05"][0], day[s][tm][0]))
                c[f"controls_{key}_mean_after_30bp"] = round(mean(control)-0.30,6) if len(control)==len(names) else None
            if c.get("entry") and c.get("exit_flat"):
                lows = [b[2] for t,b in day[sym].items() if "10:05"<=t<"14:40"]
                c["worst_intraday_mark_pct"] = round(pct(c["entry"],min(lows)),6) if lows else None
            events.append(c)
    return events, source_days, dict(missing_entry)

def chronological_cutoff(data):
    dates=sorted(d for d,bars in data["SOXX"].items() if "09:30" in bars and "09:55" in bars)
    return dates[int(len(dates)*.70)] if dates else None

def evaluate(events,source_days,missing,cutoff):
    dates = sorted(set(r["date"] for r in events))
    output = {"hypothesis":"Long isolated sector constituent 30-minute underperformance when sector/peers stable",
              "research_only":True,"selection_precommitted":True,"future_period_reused_historical_not_blind":True,
              "source_dates_by_sector":source_days, "rule":RULE, "total_sector_dates_with_signal":len(events),
              "total_unique_signal_dates":len(dates),"chronological_70_30_cutoff":cutoff,
              "missing_future_bar_events":missing, "cohort":{}}
    for period in ("earlier_70","later_30","full"):
        subset = [r for r in events if period=="full" or ((r["date"]<cutoff) if period=="earlier_70" else (r["date"]>=cutoff))]
        output["cohort"][period] = {}
        for sector in SECTORS:
            rows=[r for r in subset if r["sector"]==sector]
            output["cohort"][period][sector] = {"signal_days":len(rows),
                "after30bp_60m":stats(rows,"net_60m_30bp"),"after30bp_flat":stats(rows,"net_flat_30bp"),
                "after60bp_60m":stats(rows,"net_60m_60bp"),"after60bp_flat":stats(rows,"net_flat_60bp"),
                "matched_sector_controls_flat":stats(rows,"controls_flat_mean_after_30bp"),
                "adverse_price_mark":stats(rows,"worst_intraday_mark_pct")}
        output["cohort"][period]["ALL"]={"signal_events":len(subset),"after30bp_60m":stats(subset,"net_60m_30bp"),
            "after30bp_flat":stats(subset,"net_flat_30bp"),
            "after60bp_flat":stats(subset,"net_flat_60bp"),
            "matched_sector_controls_flat":stats(subset,"controls_flat_mean_after_30bp")}
    return output

def main():
    a=argparse.ArgumentParser();a.add_argument("--out",default="/tmp/v2-novel-20261111");args=a.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    data=load_bars()
    events,days,missing=sector_events(data)
    summary=evaluate(events,days,missing,chronological_cutoff(data))
    (out/"sector_neutral_dislocation_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    with (out/"sector_neutral_dislocation_events.csv").open("w",newline="") as f:
        if events:
            w=csv.DictWriter(f,fieldnames=sorted(set().union(*(set(r) for r in events))));w.writeheader();w.writerows(events)
    print(json.dumps({"events":len(events),"unique_dates":summary["total_unique_signal_dates"],
          "cutoff":summary["chronological_70_30_cutoff"],
          "cohorts":{k:{"ALL":v["ALL"]} for k,v in summary["cohort"].items()},
          "per_sector_later":{k:{"days":v["signal_days"],"flat":v["after30bp_flat"]} for k,v in summary["cohort"]["later_30"].items() if k!="ALL"}},indent=2))
if __name__=="__main__":main()