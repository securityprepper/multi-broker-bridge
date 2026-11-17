"""Research-only historical SPY opportunity-cost comparison; NOT an alpha rule.

Market-data GET-only, fail-closed on root holiday cache. No broker credential
or POST endpoint, no current execution code, no live orders/alerts.
This diagnostic intentionally remains descriptive, not point-in-time alpha.
"""
from __future__ import annotations

import collections,datetime as dt,json,math,random,statistics,os,stat
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
import sys
sys.path.insert(0,"/opt/securityprepper/owned-overnight-direction")
from owned_direction import batched_bars,market_json

ROOT=Path("/var/lib/securityprepper-earnings-anticipation")
DEST=Path("/tmp/v2-trading-strategy-research/research/v2_20261116_2230_preearnings_spy_opportunity_cost.json")
UTC=dt.timezone.utc
NOW=dt.datetime.now(UTC)
CT=ZoneInfo("America/Chicago")
P=Path("/var/cache/securityprepper-holiday/task-gate.json")
M=P.lstat()
G=json.loads(P.read_text())
def time(k):return dt.datetime.fromisoformat(str(G[k])).astimezone(UTC)
assert stat.S_ISREG(M.st_mode) and M.st_uid==0 and not M.st_mode&0o022 and not P.is_symlink()
assert G.get("schema_version")==1 and G.get("status_valid") is True
assert G.get("timezone")=="America/Chicago" and G.get("calendar_coverage_ok") is True
assert G.get("calendar_revision") and G.get("paused") is False
assert dt.timedelta(0)<=NOW-time("published_at")<=dt.timedelta(seconds=150)
assert NOW<time("valid_until") and NOW<time("next_check_at")

B=json.loads((ROOT/"research-20261116-broad-market-pre-earnings-3809.json").read_text())
S=json.loads((ROOT/"research-20261116-sector-98-last-earnings.json").read_text())
C=json.loads((ROOT/"latest.json").read_text())
assert len(B["pairs"])==3809
assert len({(p["symbol"],p["earnings_date"]) for p in B["pairs"]})==3809
sectors=set(S["events"]);assert len(sectors)==98
folder=Path("/etc/securityprepper/alpaca-feed/private")
keys={n:(folder/n).read_text().strip() for n in ("alpaca_data_key_id","alpaca_data_secret")}
assert all(keys.values())
start=dt.datetime(2026,7,1,tzinfo=UTC)
end=dt.datetime(2026,11,17,tzinfo=UTC)
data,failed=batched_bars(["SPY"],"1Day",start,end,"sip",keys,market_json)
assert not failed and "SPY" in data
spy={}
for b in data["SPY"]:
    d=dt.datetime.fromisoformat(b["t"].replace("Z","+00:00")).astimezone(ZoneInfo("America/New_York")).date().isoformat()
    c=float(b["c"])
    if c>0 and math.isfinite(c) and int(b.get("v",0))>0:spy[d]=c
assert len(spy)>=80

pairs=[]
missing=[]
for p in B["pairs"]:
    keys_dates=(p["prior16_day"],p["prior11_day"],p["prior6_day"],p["last_pre_earnings_close_date"])
    if any(d not in spy for d in keys_dates):
        missing.append((p["symbol"],p["earnings_date"]))
        continue
    r={}
    for horizon,begin in ((5,keys_dates[2]),(10,keys_dates[1]),(15,keys_dates[0])):
        r[f"spy{horizon}"]=100*(spy[keys_dates[3]]/spy[begin]-1)
        r[f"excess{horizon}"]=float(p[f"return{horizon}_pct"])-r[f"spy{horizon}"]
    pairs.append({"symbol":p["symbol"],"earnings_date":p["earnings_date"],"sector":p["symbol"] in sectors,
                  "week":dt.date.fromisoformat(p["earnings_date"]).isocalendar().week,
                  "month":p["earnings_date"][:7],**r})

def summary(a,h):
    if not a:return {"n":0}
    returns=[p[f"excess{h}"] for p in a]
    win=sum(v>0 for v in returns)
    return {"n":len(a),"outperform_spy":win,
            "outperform_fraction":round(win/len(a),4),
            "mean_excess_pct_points":round(statistics.mean(returns),4),
            "median_excess_pct_points":round(statistics.median(returns),4)}
groups=collections.defaultdict(list)
for p in pairs:groups[p["earnings_date"][:4]+"-W"+str(dt.date.fromisoformat(p["earnings_date"]).isocalendar().week).zfill(2)].append(p)
rng=random.Random(202611162230)
clusters=list(groups.values())
bs=[]
for _ in range(2000):
    sample=[p for g in rng.choices(clusters,k=len(clusters)) for p in g]
    bs.append(statistics.mean(p["excess5"] for p in sample))
bs.sort()
report={
 "asof_utc":NOW.isoformat(),"source_calendar_and_prices":"immutable previously collected Nasdaq retrospective calendar + paid split-adjusted SIP daily historical market-data GET",
 "market_index":"SPY","spy_price_dates":len(spy),"all_pairs":len(B["pairs"]),
 "complete_spy_pairs":len(pairs),"missing":len(missing),"n_calendar_week_clusters":len(clusters),
 "baseline_caveat":"SPY total cost/expense and dividend differences not reconciled; not an executable bid/ask price",
 "horizons":{str(h):{"all":summary(pairs,h),"tracked_98_sector":summary([p for p in pairs if p["sector"]],h),
                    "nontracked":summary([p for p in pairs if not p["sector"]],h)}
             for h in (5,10,15)},
 "cluster_week_bootstrap95_5d_mean_excess": [round(bs[int(.025*(len(bs)-1))],4),round(bs[int(.975*(len(bs)-1))],4)],
 "limitations":["Retrospective, after-event Nasdaq calendar is not original issuer release evidence",
                "Not before-entry sourced original event confirmation, prices are CLOSE not ASK/BID/noon",
                "No actual contemporaneous EPS estimate revisions, no original prior-report anchor, no trading eligibility",
                "Cluster bootstrap only controls for overlapping event weeks, not overlapping symbol or revised earnings calendar",
                "No fill/fees/SL/market order, calendar-price set suffers survivorship and missing events",
                "No forward test or held-out after-fee edge; never deploy on this"],
 "broker_calls":"NONE; Alpaca historical market-data GET-only",
 "no_orders":True,"strategy_changes":0
}
raw=json.dumps(report,indent=2,sort_keys=True)+"\n"
fd=os.open(DEST,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as f:f.write(raw)
print(json.dumps({"result":"READONLY_STORED","n":len(pairs),"missing":len(missing),
 "benchmark5":report["horizons"]["5"],"95pct_week_cluster":report["cluster_week_bootstrap95_5d_mean_excess"]},sort_keys=True))
