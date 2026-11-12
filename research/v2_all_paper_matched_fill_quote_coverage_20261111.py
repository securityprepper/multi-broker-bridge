"""Research-only audit of filled Alpaca PAPER round trips vs prior SIP quotes.

No network, broker order, position modification, or credential use. Expects
already independently retrieved private broker-fill and GET-only quote caches.
Price/quote matching is descriptive; it cannot prove a hypothetical exit fill.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median

PRIVATE_TRADES = Path("/tmp/v2-rapid-exit-run6-20261111/raw_research_private.json")
PRIVATE_QUOTES = Path("/tmp/v2-rapid-exit-run6-20261111/actual_fill_quotes_private.json")
FRESH = "FRESH_ASOF_QUOTE"


def D(v) -> Decimal:
    return Decimal(str(v))


def audit(trades: list[dict], quotes: dict[str, dict]) -> dict:
    if not trades:
        raise ValueError("No broker-confirmed trades")
    seen = set()
    by_source = defaultdict(lambda: {"trades": 0, "gross": Decimal(0), "wins": 0,
                                     "losses": 0, "paired_fresh": 0})
    status = Counter()
    quote_source = defaultdict(Counter)
    durations = Counter()
    paired_cost = Decimal(0)
    paired_notional = Decimal(0)
    paired_gross = Decimal(0)
    paired_trades = 0
    paired_wins = paired_losses = 0
    entry_above_ask = exit_below_bid = 0
    paired_bps = []
    observed_keys = set()

    for row in trades:
        source = row["source"]
        if source not in ("MBB", "FDR", "SECTOR_EXECUTOR", "REBOUND", "OTHER"):
            raise ValueError("Unrecognized source: fail closed")
        key = f'{row["day"]}|{source}|{row["symbol"]}'
        if key in seen:
            raise ValueError("Ambiguous repeated symbol/source/day lot; do not coalesce")
        seen.add(key)
        ekey, xkey = key + "|entry", key + "|exit"
        if ekey not in quotes or xkey not in quotes:
            raise ValueError("Missing quote status for broker fill leg")
        observed_keys.update((ekey, xkey))
        q0, q1 = quotes[ekey], quotes[xkey]
        entry, exitp, qty = D(row["entry"]), D(row["exit"]), D(row["qty"])
        if min(entry, exitp, qty) <= 0:
            raise ValueError("Invalid filled quantity/price")
        gross = qty * (exitp - entry)
        b = by_source[source]
        b["trades"] += 1
        b["gross"] += gross
        b["wins"] += gross > 0
        b["losses"] += gross < 0
        dt = (datetime.fromisoformat(row["exit_at"]) -
              datetime.fromisoformat(row["entry_at"])).total_seconds()
        if dt < 0:
            raise ValueError("Sell filled before buy")
        bucket = "<=2m" if dt <= 120 else "<=5m" if dt <= 300 else "<=10m" if dt <= 600 else "<=30m" if dt <= 1800 else ">30m"
        durations[bucket] += 1
        for side, q in (("entry", q0), ("exit", q1)):
            status[q["status"]] += 1
            quote_source[(source, side)][q["status"]] += 1
        if q0["status"] == FRESH and q1["status"] == FRESH:
            # These quoted midpoint differences are *descriptive* and
            # do not stand in for post-entry executable exit quotes.
            for q in (q0, q1):
                if not (0 <= D(q["quote_age_seconds"]) <= D("1.5")
                        and D(q["ask"]) >= D(q["bid"]) > 0
                        and q["size_at_best_at_least_order_quantity"]):
                    raise ValueError("Invalid fresh quote provenance/size")
            e_mid = (D(q0["bid"]) + D(q0["ask"])) / 2
            x_mid = (D(q1["bid"]) + D(q1["ask"])) / 2
            cost = qty * ((entry - e_mid) + (x_mid - exitp))
            paired_cost += cost
            paired_notional += qty * entry
            paired_gross += gross
            paired_bps.append(float(D(10000) * cost / (qty * entry)))
            paired_trades += 1
            paired_wins += gross > 0
            paired_losses += gross < 0
            b["paired_fresh"] += 1
            entry_above_ask += entry > D(q0["ask"])
            exit_below_bid += exitp < D(q1["bid"])
    if observed_keys != set(quotes):
        raise ValueError("Unmatched quotes; fail closed rather than count extras")

    return {
        "scope": "ONE_AUTHENTICATED_ALPACA_PAPER_ACCOUNT_ID_NOT_IN_SANITIZED_CACHE",
        "research_only": True, "orders_submitted": 0,
        "distinct_days": len({t["day"] for t in trades}),
        "distinct_filled_round_trips": len(trades),
        "filled_leg_quote_status": dict(sorted(status.items())),
        "by_source": {
            src: {"trades": v["trades"], "gross_usd": round(float(v["gross"]), 2),
                  "gross_wins": v["wins"], "gross_losses": v["losses"],
                  "both_legs_fresh_quote": v["paired_fresh"]}
            for src, v in sorted(by_source.items())
        },
        "by_source_side_quote_status": {
            f"{s}|{side}": dict(sorted(c.items()))
            for (s, side), c in sorted(quote_source.items())
        },
        "hold_time_bins": dict(sorted(durations.items())),
        "two_sided_fresh_quote_pairs": paired_trades,
        "paired_actual_gross_usd": round(float(paired_gross), 2),
        "paired_actual_gross_winners": paired_wins,
        "paired_actual_gross_losers": paired_losses,
        "midpoint_cost_descriptive_usd": round(float(paired_cost), 2),
        "midpoint_cost_weighted_bp": round(float(D(10000) * paired_cost / paired_notional), 2)
            if paired_notional else None,
        "midpoint_cost_median_per_trade_bp": round(median(paired_bps), 2)
            if paired_bps else None,
        "paired_entry_fill_above_prior_ask": entry_above_ask,
        "paired_exit_fill_below_prior_bid": exit_below_bid,
        "commission_status": "UNKNOWN",
        "actual_exit_trigger_status": "UNKNOWN_WITHOUT_REASON_ORDER_UUID_JOIN",
        "hypothetical_executable_quote_and_fill_result": "NOT_ESTABLISHED",
        "trade_news_asof": "NEWS_UNKNOWN_HISTORICAL_OUTCOME_CONTROL_ONLY",
        "holdout_requirement": "AT_LEAST_20_INDEPENDENT_DAYS_NOT_MET",
    }


def main() -> None:
    raw = json.loads(PRIVATE_TRADES.read_text())
    quote = json.loads(PRIVATE_QUOTES.read_text())
    if not (raw["research_only"] and quote["research_only"]
            and raw["broker_orders_submitted"] == quote["orders_submitted"] == 0):
        raise ValueError("Read-only evidence only")
    result = audit(raw["trades"], quote["quotes"])
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
