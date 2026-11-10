"""Research-only Alpaca PAPER order-snapshot FIFO audit. No network/broker writes.

A fully filled broker ORDER is not a FILL activity. For these snapshots, the
broker's filled_qty/filled_avg_price is the bounded price arithmetic source.
The audit never prints client order IDs, account identifiers or cash.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
FINAL = {"filled", "canceled", "expired", "rejected", "done_for_day"}


class AuditError(ValueError):
    pass


def as_time(value: str) -> datetime:
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise AuditError("invalid timestamp") from exc
    if when.tzinfo is None:
        raise AuditError("timezone-naive timestamp")
    return when.astimezone(timezone.utc)


def number(value: object, label: str) -> Decimal:
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AuditError("invalid " + label) from exc
    if not x.is_finite() or x <= 0:
        raise AuditError("nonpositive/nonfinite " + label)
    return x


def whole(value: object, label: str) -> Decimal:
    x = number(value, label)
    if x != x.to_integral_value():
        raise AuditError("non-whole " + label)
    return x


def audit(snapshot: dict, session_day: str, owner_prefix: str = "MBB-") -> dict:
    if not snapshot.get("paper_only") or snapshot.get("broker_verified") is not True:
        raise AuditError("broker-verified PAPER snapshot required")
    if snapshot.get("recent_orders_complete") is not True:
        raise AuditError("complete broker recent-order readback required")
    asof = as_time(snapshot["asof_utc"])
    session = date.fromisoformat(session_day)
    start = datetime.combine(session, time.min, CHICAGO).astimezone(timezone.utc)
    if as_time(snapshot["recent_orders_since_utc"]) > start:
        raise AuditError("recent-order range does not cover the Chicago session")
    if not start <= asof < datetime.combine(session, time.max, CHICAGO).astimezone(timezone.utc):
        raise AuditError("snapshot not from requested Chicago session")
    orders = snapshot.get("recent_orders")
    if not isinstance(orders, list) or not isinstance(snapshot.get("positions"), list):
        raise AuditError("invalid broker inventory shape")
    if snapshot.get("open_orders_count") != len(snapshot.get("open_orders", [])):
        raise AuditError("open-order count disagreement")
    if snapshot.get("positions_count") != len(snapshot["positions"]):
        raise AuditError("position count disagreement")
    if snapshot.get("orders_submitted_by_exporter") != 0:
        raise AuditError("read-only exporter unexpectedly submitted orders")

    observed = []
    seen_ids = set()
    all_today_count = 0
    other_writers = 0
    for o in orders:
        if not isinstance(o, dict):
            raise AuditError("invalid order record")
        cid = o.get("client_order_id")
        if not isinstance(cid, str) or not cid:
            raise AuditError("missing order client ID")
        if cid in seen_ids:
            raise AuditError("duplicate client-order ID")
        seen_ids.add(cid)
        created = as_time(o["created_at"])
        if created > asof:
            raise AuditError("order created after snapshot")
        if created.astimezone(CHICAGO).date() != session:
            continue
        all_today_count += 1
        if not cid.startswith(owner_prefix):
            other_writers += 1
            continue
        qty_str = o.get("filled_qty")
        if str(qty_str) in ("0", "0.0"):
            # An unfilled canceled/rejected order is not an execution.
            if o.get("status") not in FINAL:
                raise AuditError("nonfinal zero-fill owner order needs reconciliation")
            continue
        if qty_str is None:
            raise AuditError("missing filled quantity")
        number(qty_str, "filled quantity")
        if o.get("status") != "filled":
            # Partial orders cannot be treated as fully settled matched lots.
            raise AuditError("partial/nonfinal owner fill needs activity-level reconciliation")
        qty = whole(qty_str, "filled shares")
        asked = whole(o["qty"], "order shares")
        if qty != asked:
            raise AuditError("order claims filled but quantity differs")
        filled = as_time(o["filled_at"])
        if not created <= filled <= asof:
            raise AuditError("invalid fill chronology")
        price = number(o["filled_avg_price"], "filled average price")
        if o.get("side") not in ("buy", "sell"):
            raise AuditError("invalid order side")
        observed.append((filled, o["symbol"], o["side"], qty, price, cid))
    observed.sort(key=lambda row: (row[0], 0 if row[2] == "buy" else 1, row[5]))

    fifo = defaultdict(deque)
    closes = []
    buys = 0
    sells = 0
    for filled, symbol, side, qty, price, _ in observed:
        if side == "buy":
            buys += 1
            fifo[symbol].append([qty, price, filled])
            continue
        sells += 1
        remain = qty
        profit = Decimal("0")
        holding_minutes = []
        while remain > 0:
            if not fifo[symbol]:
                raise AuditError("owner sell cannot be matched to owner bought lots")
            lot = fifo[symbol][0]
            match = min(remain, lot[0])
            profit += match * (price - lot[1])
            holding_minutes.append(round((filled - lot[2]).total_seconds() / 60, 3))
            remain -= match
            lot[0] -= match
            if lot[0] == 0:
                fifo[symbol].popleft()
        closes.append({"symbol": symbol, "filled_qty": int(qty),
                       "gross_pnl_usd": round(float(profit), 4),
                       "holding_minutes": max(holding_minutes)})

    open_lots = {sym: int(sum(row[0] for row in q))
                 for sym, q in sorted(fifo.items()) if q}
    broker_positions = {}
    for p in snapshot["positions"]:
        sym = p["symbol"]
        if sym in broker_positions:
            raise AuditError("duplicate position symbol")
        if p.get("side") != "long":
            raise AuditError("short/inherited position requires independent audit")
        broker_positions[sym] = int(whole(p["qty"], "position quantity"))
    if open_lots != broker_positions:
        # Equality of quantities is necessary, but not sufficient, for
        # writer ownership. Only the full fill-UUID ledger can prove origin.
        raise AuditError("owner open lots do not reconcile to broker positions")

    gross = sum((Decimal(str(row["gross_pnl_usd"])) for row in closes), Decimal("0"))
    return {
        "session_chicago": session_day,
        "asof_utc": asof.isoformat(),
        "paper_only": True,
        "broker_verified_snapshot": True,
        "complete_recent_order_window": True,
        "owner_prefix_classification": owner_prefix.rstrip("-"),
        "orders_today_total": all_today_count,
        "other_writer_orders_today": other_writers,
        "owner_filled_buys": buys,
        "owner_filled_sells": sells,
        "owner_closed_winners": sum(x["gross_pnl_usd"] > 0 for x in closes),
        "owner_closed_losers": sum(x["gross_pnl_usd"] < 0 for x in closes),
        "owner_closed_flat": sum(x["gross_pnl_usd"] == 0 for x in closes),
        "gross_realized_usd_before_fees": round(float(gross), 4),
        "open_positions_by_symbol": open_lots,
        "broker_open_orders": snapshot["open_orders_count"],
        "closed_lots": closes,
        "after_fees_pnl_verified": False,
        "fill_uuid_origin_chain_verified": False,
        "exact_exit_reasons_verified": False,
        "orders_sent_by_research": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--session", required=True)
    args = parser.parse_args()
    result = audit(json.loads(args.snapshot.read_text()), args.session)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
