"""GET-only, research-only MBB PAPER cross-session BUY lockout audit.
Reads local SQLite in query_only mode and read-only systemd journals.
Never accesses broker credentials, submits orders, or changes live state.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import json
import sqlite3
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

CHI = ZoneInfo("America/Chicago")
PRIOR = "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"
EXTENDED = "ENTRY_EXTENSION_BLOCKED_"
UNIT = "trading-sector-paper-executor.service"

def summarize(day, tracked_dates, scans, source_text):
    if not isinstance(day, str) or len(day) != 10:
        raise ValueError("invalid Chicago day")
    if not isinstance(scans, list) or not isinstance(tracked_dates, dict):
        raise ValueError("invalid evidence")
    watched = collections.Counter()
    skipped = collections.Counter()
    prior_by_date = collections.Counter()
    unique_prior = set()
    orders = []
    for event in scans:
        if event.get("status") != "SCAN_COMPLETE":
            continue
        watched.update(event.get("buy_watch_symbols") or [])
        for x in event.get("skipped_buy_reasons") or []:
            sym, reason = x.get("symbol"), x.get("reason", "")
            if not sym or not isinstance(reason, str):
                continue
            skipped[reason.split("_+")[0] if reason.startswith(EXTENDED) else reason] += 1
            if reason == PRIOR and sym in tracked_dates and tracked_dates[sym] < day:
                unique_prior.add(sym)
                prior_by_date[tracked_dates[sym]] += 1
        for o in event.get("orders") or []:
            orders.append((o.get("symbol"), o.get("side"), o.get("status")))
    direct_news_clear = ("NEWS_CLEAR_ASOF" in source_text or
                         "negative_news" in source_text or
                         "adverse_news" in source_text)
    cross_session_branch = ("if symbol in tracked:" in source_text and
                            "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY" in source_text)
    terminal_zero_fill_cleanup_only = (
        'DELETE FROM tracked WHERE symbol=?' in source_text and
        'Decimal(str(status.get("filled_qty",0)))==0' in source_text
    )
    return {
        "observed_chicago_day": day,
        "completed_scans": sum(x.get("status") == "SCAN_COMPLETE" for x in scans),
        "buy_watch_appearances": sum(watched.values()),
        "unique_buy_watch_symbols": len(watched),
        "skip_reasons": dict(skipped),
        "cross_session_prior_entry_skip_appearances": sum(prior_by_date.values()),
        "cross_session_prior_entry_unique_symbols": len(unique_prior),
        "cross_session_prior_entry_dates": dict(sorted(prior_by_date.items())),
        "tracked_records": len(tracked_dates),
        "tracked_older_than_chicago_day": sum(v < day for v in tracked_dates.values()),
        "logged_order_replies_by_side_status": {
            f"{side}:{status}":count for (side,status),count in
            collections.Counter((s,st) for _,s,st in orders).items()
        },
        "static_source_cross_session_branch": cross_session_branch,
        "static_source_only_terminal_zero_fill_removes_tracking": terminal_zero_fill_cleanup_only,
        "static_source_direct_news_clearance_found": direct_news_clear,
        "conclusion": ("CROSS_SESSION_ENTRY_LOCKOUT_CONFIRMED"
                       if cross_session_branch and unique_prior else "INSUFFICIENT_EVIDENCE"),
        "scope": "journal acceptance/skip evidence, NOT missed profitable broker fills",
        "orders_placed_by_audit": 0
    }

def collect(db_path, source_path, day, since):
    if not Path(db_path).is_file() or not Path(source_path).is_file():
        raise ValueError("trusted paths missing")
    db = sqlite3.connect(Path(db_path).as_uri() + "?mode=ro", uri=True)
    db.execute("PRAGMA query_only=ON")
    try:
        dates = {symbol: ts[:10] for symbol,ts in
                 db.execute("SELECT symbol,entry_time FROM tracked")}
    finally:
        db.close()
    cmd = ["journalctl","-u",UNIT,"--since",since,"-o","cat","--no-pager"]
    raw = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    scans = []
    for line in raw.splitlines():
        try:
            x = json.loads(line)
            if isinstance(x,dict) and x.get("status")=="SCAN_COMPLETE":
                scans.append(x)
        except (TypeError, ValueError):
            continue
    return summarize(day,dates,scans,Path(source_path).read_text())

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--state",default="/var/lib/multi-broker-paper/strategy.sqlite3")
    p.add_argument("--source",default="/opt/securityprepper/multi-broker-bridge/multi_broker_bridge/auto_paper.py")
    p.add_argument("--day",default=dt.datetime.now(CHI).date().isoformat())
    p.add_argument("--since",default=dt.datetime.now(CHI).strftime("%Y-%m-%d 00:00:00"))
    args=p.parse_args()
    print(json.dumps(collect(args.state,args.source,args.day,args.since),indent=2,sort_keys=True))