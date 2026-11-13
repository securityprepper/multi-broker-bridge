"""Read-only MBB tracked-ledger age diagnostic. No broker calls or state writes."""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import quote


def diagnose(rows: list[dict], asof_session: str) -> dict:
    """Classify ages only; never equate an old row with a broker-verified fill."""
    today = date.fromisoformat(asof_session)
    by_session: Counter[str] = Counter()
    old_symbols: set[str] = set()
    current = unknown = 0
    for row in rows:
        session = row.get("trade_date")
        if not session:
            unknown += 1
            continue
        entry_day = date.fromisoformat(session)
        if entry_day > today:
            raise ValueError("Future entry-session date")
        by_session[session] += 1
        if entry_day == today:
            current += 1
        else:
            old_symbols.add(row["symbol"])
    return {
        "asof_session": asof_session,
        "tracked_count": len(rows),
        "prior_session_tracked_count": len(old_symbols),
        "same_session_tracked_count": current,
        "unmatched_entry_ref_count": unknown,
        "by_entry_session": dict(sorted(by_session.items())),
        "broker_exit_fill_verified_by_this_script": False,
        "diagnostic_only": True,
    }


def read_snapshot(path: str) -> list[dict]:
    """SQLite mode=ro only. Never invoke production state initializer."""
    database = Path(path).resolve(strict=True)
    uri = "file:" + quote(str(database), safe="/") + "?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        result = db.execute(
            "SELECT t.symbol,t.entry_ref,t.entry_time,a.trade_date "
            "FROM tracked AS t LEFT JOIN attempts AS a "
            "ON a.client_id=t.entry_ref AND a.side='buy' "
            "ORDER BY t.symbol"
        ).fetchall()
        return [
            {"symbol": symbol, "entry_ref": ref,
             "entry_time": when, "trade_date": session}
            for symbol, ref, when, session in result
        ]
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite-readonly", required=True)
    parser.add_argument("--asof-session", required=True)
    args = parser.parse_args()
    print(json.dumps(diagnose(read_snapshot(args.sqlite_readonly),
                              args.asof_session), sort_keys=True))


if __name__ == "__main__":
    main()
