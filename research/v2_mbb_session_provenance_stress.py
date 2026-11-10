"""Research-only reproductions of MBB session-key and stale-provenance risks.

NO live broker API, network, host state mutation or trading authorization.
Uses in-memory SQLite and a fake broker method to exercise installed code.
"""
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import sqlite3

from multi_broker_bridge.auto_paper import STATE_SCHEMA, _reserve
from multi_broker_bridge.paper_time_exit import timed_flatten
from multi_broker_bridge.premarket_policy import trading_session_day

CT = ZoneInfo("America/Chicago")
NY = ZoneInfo("America/New_York")


def when(local_iso: str) -> datetime:
    return datetime.fromisoformat(local_iso).replace(tzinfo=CT)


def historical_wall_key(at: datetime) -> str:
    """As currently installed: NY wall calendar date, not trading session."""
    return at.astimezone(NY).date().isoformat()


def in_memory_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.executescript(STATE_SCHEMA)
    return db


def session_key_discontinuity() -> dict:
    before = when("2026-11-09T21:30:00")
    after = when("2026-11-09T23:30:00")
    assert trading_session_day(before) == trading_session_day(after)
    db = in_memory_db()
    first = _reserve(db, historical_wall_key(before), "AMD", "buy", "MOCK-1")
    second = _reserve(db, historical_wall_key(after), "AMD", "buy", "MOCK-2")
    keys = [r[0] for r in db.execute(
        "SELECT trade_date FROM attempts WHERE symbol='AMD' ORDER BY trade_date"
    )]
    db.close()
    db2 = in_memory_db()
    normalized = trading_session_day(before).isoformat()
    normalized_first = _reserve(db2, normalized, "AMD", "buy", "MOCK-3")
    normalized_second = _reserve(db2, normalized, "AMD", "buy", "MOCK-4")
    db2.close()
    return {
        "same_trading_session": normalized,
        "wall_date_keys": keys,
        "legacy_both_reservations_accepted": bool(first and second),
        "session_key_only_first_accepted": bool(normalized_first and not normalized_second),
        "note": "Second acceptance is a reservation-only demonstration. Existing tracked-row "
                "logic normally provides an additional guard; a terminal zero-fill cleanup "
                "or other tracking reconciliation could expose this gap."
    }


def fake_cross_strategy_flatten(*, old_qty: int = 4, new_qty: int | None = 2,
                                manual_open_order: bool = False) -> dict:
    """Simulate a *different* owner holding same symbol after stale MBB row.

    This is a WHAT-IF, not evidence that another strategy currently owns AMD.
    The only broker is a local closure capturing intended payload dictionaries.
    """
    db = in_memory_db()
    db.execute(
        "INSERT INTO tracked(symbol,entry_ref,highest,entry_time,entry_qty) "
        "VALUES(?,?,?,?,?)",
        ("AMD", "MBB-20261109-B-AMD", "466.70",
         when("2026-11-09T07:35:42").isoformat(), old_qty)
    )
    db.commit()
    posts = []
    def broker(method, path, body=None):
        if method == "GET" and path == "/v2/clock":
            return {"is_open": True}
        if method == "POST" and path == "/v2/orders":
            posts.append(dict(body))
            return {"id": "FAKE-ONLY-RECEIPT", "client_order_id": body["client_order_id"],
                    "status": "accepted"}
        raise AssertionError(f"unexpected fake broker action {method} {path}")

    positions = ([] if new_qty is None else
        [{"symbol": "AMD", "side": "long", "qty": str(new_qty),
          "qty_available": str(new_qty)}])
    orders = ([{"symbol": "AMD", "side": "sell", "status": "new",
               "id": "FAKE-MANUAL-ORDER", "client_order_id": "OTHER-STRATEGY-AMD"}]
              if manual_open_order else [])
    try:
        result = timed_flatten(when("2026-11-10T13:40:00"),
                               positions, orders, db, broker)
        status = result["status"]
    except Exception as exc:
        status = type(exc).__name__
    finally:
        db.close()
    return {
        "status": status,
        "fake_sell_count": len(posts),
        "fake_sell_quantities": [p["qty"] for p in posts],
        "fake_sell_order_types": [p["type"] for p in posts],
        "warning": "Synthetic replacement-position provenance is not proven by broker "
                   "aggregate symbol/quantity alone. No actual order was sent."
    }


def main() -> None:
    print(json.dumps({
        "scenario": "SOURCE_LOGIC_ONLY_NO_BROKER_ACTIONS",
        "session_key": session_key_discontinuity(),
        "stale_row_other_strategy_same_symbol": fake_cross_strategy_flatten(),
        "stale_row_no_position": fake_cross_strategy_flatten(new_qty=None),
        "unmanaged_open_order": fake_cross_strategy_flatten(manual_open_order=True),
        "manual_exceeds_prior_quantity": fake_cross_strategy_flatten(new_qty=5),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
