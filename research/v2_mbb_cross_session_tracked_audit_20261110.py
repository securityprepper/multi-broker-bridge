"""Read-only MBB cross-session tracked-state diagnostic. RESEARCH ONLY.

No Alpaca broker API, no credentials, no orders, no SQLite writes. A previous
session's tracked row is *not* by itself proof that the broker is flat.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
CROSS_SESSION_SKIP = "PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY"


def session_day(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timezone-aware timestamp required")
    local = value.astimezone(CHICAGO)
    day = local.date()
    if local.timetz().replace(tzinfo=None) >= time(19):
        day += timedelta(days=1)
    return day.isoformat()


def tracked_state(rows, as_of: datetime) -> dict:
    current = session_day(as_of)
    old, same, future, bad = set(), set(), set(), set()
    for symbol, stamp in rows:
        if not isinstance(symbol, str) or not symbol:
            bad.add(str(symbol))
            continue
        try:
            dt = datetime.fromisoformat(stamp)
            day = session_day(dt)
        except (TypeError, ValueError):
            bad.add(symbol)
            continue
        if day < current:
            old.add(symbol)
        elif day == current:
            same.add(symbol)
        else:
            future.add(symbol)
    return {
        "current_session": current,
        "tracked_total": len(rows),
        "previous_session_symbols": sorted(old),
        "same_session_symbols": sorted(same),
        "future_or_invalid_count": len(future) + len(bad),
        "prior_session_count": len(old),
        "same_session_count": len(same),
        "broker_flatness_verified": False,
    }


def read_state_readonly(path: str, as_of: datetime) -> dict:
    absolute = Path(path).resolve(strict=True)
    # uri mode=ro and query_only prevent accidental writes to production state
    from urllib.parse import quote
    con = sqlite3.connect("file:" + quote(str(absolute)) + "?mode=ro", uri=True)
    try:
        con.execute("PRAGMA query_only=ON")
        rows = con.execute("SELECT symbol,entry_time FROM tracked").fetchall()
        result = tracked_state(rows, as_of)
        result["current_session_attempts"] = con.execute(
            "SELECT COUNT(*) FROM attempts WHERE trade_date=?",
            (result["current_session"],)
        ).fetchone()[0]
        return result
    finally:
        con.close()


def observed_skips(records: list[dict], state: dict) -> dict:
    """Only specific, recorded skip reasons count as confirmed broker-gate skips."""
    old = set(state["previous_session_symbols"])
    hits = set()
    other = Counter()
    scans = 0
    for record in records:
        if not isinstance(record, dict) or "candidate_count" not in record:
            continue
        scans += 1
        for item in record.get("skipped_buy_reasons", []):
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol")
            reason = item.get("reason")
            if not isinstance(symbol, str) or not isinstance(reason, str):
                continue
            if reason == CROSS_SESSION_SKIP and symbol in old:
                hits.add(symbol)
            else:
                other[reason] += 1
    return {
        "scans_examined": scans,
        "observed_prior_session_lockout_symbols": sorted(hits),
        "observed_prior_session_lockout_count": len(hits),
        "other_skip_reason_counts": dict(sorted(other.items())),
        "safe_to_clear_tracking_without_broker_readback": False,
        "places_orders": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-db", required=True)
    parser.add_argument("--as-of", required=True, help="ISO offset-aware datetime")
    parser.add_argument("--sanitized-events-json", help="JSON list of selected scan fields")
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of)
    state = read_state_readonly(args.state_db, as_of)
    if args.sanitized_events_json:
        records = json.loads(Path(args.sanitized_events_json).read_text())
        state.update(observed_skips(records, state))
    # Do not emit tracked entry references, amounts, account IDs or credentials.
    state.pop("same_session_symbols")
    state.pop("previous_session_symbols")
    print(json.dumps(state, sort_keys=True))


if __name__ == "__main__":
    main()
