"""Offline, GET-export-only MBB PAPER cutoff and FIFO audit; research only.

Inputs are existing broker inventory JSON and journalctl JSON lines. There are no
broker connections, trades, credentials, writes, notifications, or production imports.
"""
from __future__ import annotations
import argparse
import collections
from datetime import datetime, time
from decimal import Decimal
import json
import subprocess
from zoneinfo import ZoneInfo

CHI = ZoneInfo("America/Chicago")
CUTOFF = time(13, 15)

def stamp(s):
    if not isinstance(s, str) or not s:
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("naive timestamp")
    return dt.astimezone(CHI)

def is_mbb(o, day):
    return isinstance(o, dict) and str(o.get("client_order_id", "")).startswith(
        "MBB-" + day.replace("-", "") + "-"
    )

def broker_audit(snapshot, day, asof):
    if snapshot.get("broker_verified") is not True or snapshot.get("recent_orders_complete") is not True:
        raise ValueError("unverified or incomplete broker export")
    if stamp(snapshot["asof_utc"]) > asof:
        raise ValueError("snapshot later than research observation")
    orders = [o for o in snapshot.get("recent_orders", []) if is_mbb(o, day)]
    seen = set()
    buys_after_cutoff = []
    missing_submits = []
    filled = []
    for o in orders:
        cid = o["client_order_id"]
        if cid in seen:
            raise ValueError("duplicate MBB client order identifier")
        seen.add(cid)
        if o.get("side") == "buy":
            try:
                t = stamp(o.get("submitted_at"))
                if t.date().isoformat() == day and t.time() >= CUTOFF:
                    buys_after_cutoff.append(o.get("symbol"))
            except ValueError:
                missing_submits.append(o.get("symbol"))
        if o.get("status") != "filled" or not o.get("filled_at"):
            continue
        t = stamp(o["filled_at"])
        if t.date().isoformat() != day or t > asof:
            continue
        q = Decimal(str(o.get("filled_qty")))
        price = Decimal(str(o.get("filled_avg_price")))
        if q <= 0 or price <= 0 or not q.is_finite() or not price.is_finite():
            raise ValueError("bad broker fill")
        filled.append((t, str(o["symbol"]), str(o["side"]), q, price))
    filled.sort()
    queues = collections.defaultdict(collections.deque)
    pnl = Decimal(0)
    per_symbol = collections.defaultdict(lambda: Decimal(0))
    lots = winners = losers = 0
    unmatched_sells = []
    for _, symbol, side, qty, price in filled:
        if side == "buy":
            queues[symbol].append([qty, price])
        elif side == "sell":
            rem = qty
            while rem:
                if not queues[symbol]:
                    unmatched_sells.append(symbol)
                    break
                prior_qty, prior_price = queues[symbol][0]
                matched = min(rem, prior_qty)
                gross = matched * (price - prior_price)
                pnl += gross
                per_symbol[symbol] += gross
                winners += gross > 0
                losers += gross < 0
                lots += 1
                rem -= matched
                queues[symbol][0][0] -= matched
                if queues[symbol][0][0] == 0:
                    queues[symbol].popleft()
        else:
            raise ValueError("unknown side")
    still_open = {sym: str(sum(q for q, _ in dq)) for sym, dq in queues.items() if dq}
    broker_positions = {str(p["symbol"]): str(p.get("qty")) for p in snapshot.get("positions", [])}
    # A matching broker balance is NOT proof of strategy-specific ownership.
    return {
        "asof_utc": snapshot["asof_utc"], "broker_verified": True,
        "orders_in_session": len(orders), "filled_buys": sum(x[2] == "buy" for x in filled),
        "filled_sells": sum(x[2] == "sell" for x in filled),
        "matched_lots": lots, "winning_lots": winners, "losing_lots": losers,
        "gross_realized_paper_usd": str(pnl.quantize(Decimal(".01"))),
        "pnl_by_symbol_usd": {k: str(v.quantize(Decimal(".01"))) for k,v in sorted(per_symbol.items())},
        "remaining_mbb_fill_lots": still_open,
        "broker_position_quantities": broker_positions,
        "unmatched_sells": unmatched_sells,
        "buy_submissions_after_1315_CT": buys_after_cutoff,
        "buy_submissions_with_missing_timestamp": missing_submits,
        "open_broker_orders": snapshot.get("open_orders_count"),
        "strategy_ownership_proven": False,
        "after_fee_pnl_known": False,
    }

def journal_audit(lines, day, start, end):
    groups = {"before_entry_cutoff": collections.Counter(), "after_entry_cutoff": collections.Counter()}
    for line in lines:
        try:
            outer = json.loads(line)
            t = datetime.fromtimestamp(int(outer["__REALTIME_TIMESTAMP"]) / 1_000_000, CHI)
            d = json.loads(outer["MESSAGE"])
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            continue
        if t.date().isoformat() != day or not (start <= t <= end) or d.get("status") != "SCAN_COMPLETE":
            continue
        group = groups["before_entry_cutoff" if t.time() < CUTOFF else "after_entry_cutoff"]
        group["scans"] += 1
        group["candidate_appearances"] += int(d.get("candidate_count", 0))
        group["buy_watch_appearances"] += len(d.get("buy_watch_symbols") or [])
        for reason in d.get("skipped_buy_reasons") or []:
            label = reason.get("reason", "UNKNOWN") if isinstance(reason, dict) else str(reason)
            group["skip_" + label] += 1
        for o in d.get("orders") or []:
            if isinstance(o, dict) and o.get("side") == "buy":
                group["buy_order_reports"] += 1
        # This flag is the HOLIDAY gate, not the 13:15 time cutoff.
        if d.get("gate_allows_new_entries") is True:
            group["holiday_gate_true_scans"] += 1
    return {k: dict(v) for k, v in groups.items()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()
    start, end = stamp(args.start), stamp(args.end)
    if end <= start or end.date().isoformat() != args.date:
        raise ValueError("invalid audit window")
    with open(args.inventory, encoding="utf-8") as f:
        inv = json.load(f)
    audit = broker_audit(inv, args.date, end)
    result = subprocess.run(
        ["journalctl", "-u", "trading-sector-paper-executor.service",
         "--since", start.strftime("%Y-%m-%d %H:%M:%S"),
         "--until", end.strftime("%Y-%m-%d %H:%M:%S"),
         "-o", "json", "--no-pager"], capture_output=True, text=True, check=True)
    audit["journal"] = journal_audit(result.stdout.splitlines(), args.date, start, end)
    audit["cutoff_policy"] = "13:15 America/Chicago by submission time, not fill time"
    audit["orders_submitted_by_research"] = 0
    print(json.dumps(audit, sort_keys=True))
if __name__ == "__main__":
    main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]
