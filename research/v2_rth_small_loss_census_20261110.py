"""Offline RTH-only Alpaca PAPER MBB filled-order churn audit. No network or orders.

Input must be an existing verified read-only broker inventory JSON. A
same-symbol quantity match is NOT sufficient evidence of strategy ownership.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
RTH_START = time(8, 30)
RTH_FLAT = time(13, 40)
D = Decimal


def timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("naive timestamp")
    return result.astimezone(CT)


def number(value) -> Decimal:
    try:
        result = D(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid numeric value") from None
    if not result.is_finite() or result <= 0:
        raise ValueError("invalid positive value")
    return result


def analyze(snapshot: dict, trading_day: str) -> dict:
    """Analyze completed RTH orders; fail closed on gaps and mismatches."""
    if not all(snapshot.get(k) is True for k in
               ("broker_verified", "recent_orders_complete", "paper_only")):
        raise ValueError("not a complete, verified PAPER snapshot")
    asof = timestamp(snapshot["asof_utc"])
    if trading_day != asof.date().isoformat():
        raise ValueError("not the requested Chicago date")
    if snapshot.get("open_orders_count") != len(snapshot.get("open_orders", [])):
        raise ValueError("open order count mismatch")
    if snapshot["open_orders_count"] != 0:
        raise ValueError("open broker orders: not safe to reconcile")
    orders = []
    other_symbols = set()
    ids = set()
    for row in snapshot.get("recent_orders", []):
        if row.get("status") != "filled":
            continue
        filled = timestamp(row.get("filled_at"))
        if filled > asof:
            raise ValueError("future fill")
        if filled.date().isoformat() != trading_day or not RTH_START <= filled.time() < RTH_FLAT:
            continue
        cid = row.get("client_order_id", "")
        if not isinstance(cid, str) or not cid:
            raise ValueError("missing client order id")
        if cid in ids:
            raise ValueError("duplicate client order id")
        ids.add(cid)
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise ValueError("bad symbol")
        qty = number(row.get("filled_qty"))
        price = number(row.get("filled_avg_price"))
        if row.get("side") not in ("buy", "sell"):
            raise ValueError("unsupported order side")
        if not cid.startswith("MBB-"):
            other_symbols.add(symbol)
            continue
        orders.append((filled, symbol, row["side"], qty, price))
    orders.sort(key=lambda r: r[0])
    lots = defaultdict(deque)
    closed = []
    for filled, symbol, side, qty, price in orders:
        if side == "buy":
            lots[symbol].append((qty, price, filled))
            continue
        remaining = qty
        pnl = D("0")
        invested = D("0")
        first_buy = None
        while remaining:
            if not lots[symbol]:
                raise ValueError("unmatched MBB sell / inherited position")
            available, entry, bought = lots[symbol][0]
            use = min(available, remaining)
            pnl += use * (price - entry)
            invested += use * entry
            first_buy = min(first_buy, bought) if first_buy else bought
            remaining -= use
            if use == available:
                lots[symbol].popleft()
            else:
                lots[symbol][0] = (available - use, entry, bought)
        ret = (pnl / invested * 100)
        closed.append({"symbol": symbol,
                       "gross_usd": float(pnl.quantize(D("0.01"))),
                       "return_pct": float(ret.quantize(D("0.0001"))),
                       "hold_minutes": round((filled - first_buy).total_seconds() / 60, 2),
                       "small_loss_under_2_5pct": D("-2.5") < ret < 0,
                       "cross_writer_ambiguous": symbol in other_symbols})
    outstanding = {symbol: sum((q for q, _, _ in line), D("0"))
                   for symbol, line in lots.items() if line}
    positions = {x["symbol"]: number(x["qty"]) for x in snapshot.get("positions", [])}
    quantity_matches = outstanding == positions
    ambiguous = bool(other_symbols & (set(outstanding) | {x["symbol"] for x in closed}))
    # Even a match does not establish exclusive share ownership.
    return {"asof_utc": snapshot["asof_utc"],
            "trading_day_chicago": trading_day,
            "orders_mbb_rth": len(orders),
            "round_trips": len(closed),
            "winning_exits": sum(x["gross_usd"] > 0 for x in closed),
            "losing_exits": sum(x["gross_usd"] < 0 for x in closed),
            "small_loss_exits": sum(x["small_loss_under_2_5pct"] for x in closed),
            "loss_exits_within_6min": sum(x["gross_usd"] < 0 and x["hold_minutes"] <= 6 for x in closed),
            "gross_realized_usd": round(sum(x["gross_usd"] for x in closed), 2),
            "open_mbb_lot_quantities": {k: str(v) for k, v in sorted(outstanding.items())},
            "broker_position_quantities_match_mbb_lots": quantity_matches,
            "cross_writer_ambiguity": ambiguous,
            "exclusive_strategy_ownership_proven": False,
            "fees_included": False,
            "exit_reasons_known": False,
            "end_of_day_outcome": False,
            "closed": closed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", help="existing GET-only broker inventory file")
    parser.add_argument("--date", required=True, help="Chicago RTH date YYYY-MM-DD")
    args = parser.parse_args()
    value = analyze(json.loads(Path(args.snapshot).read_text()), args.date)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
