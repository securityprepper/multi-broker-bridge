# Research-only: Alpaca PAPER recommendation readback false UNKNOWN (2026-11-19)

## New independently reproduced implementation blocker

At 22:30 America/Chicago on November 19, an account-matched, broker-verified Alpaca PAPER GET-only inventory (generated about four minutes earlier) reported **zero positions and zero working orders**. Its bounded recent-order inventory contained 155 orders with `recent_orders_complete=true`. It showed the November 19 entry for D expired with zero shares filled and the November 18 SNPS entry and exit both filled (four shares). This snapshot covers this specific PAPER account and the last three days; it does NOT prove full historical coverage or any other account is flat. Recommendation Audit remains sole notifier of closed recommendation-linked trades.

Percona `securityprepper_trading.sp_paper_rec_intents` still had both matching recommendations in `BROKER_ACCEPTED` with `broker_status=pending_new`, unchanged since their initial acceptance. Reconciliation service logs repeatedly output per-recommendation `UNKNOWN_READBACK` / `Unsafe` (511 log lines since 14:00 CT), despite the matching first-party PAPER order IDs and observed broker outcomes. This blocks the recommendation ledger's filled/unfilled/closed status and fee-audit pipeline from progressing.

## Sufficient code-level cause

The installed `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/reconcile.py` has:
```python
str(parent.get("limit_price")) != str(row["limit_price"])
```
inside the otherwise correct parent-order identity guard. It compares decimal *formatting*, not numeric prices. Verified matching examples from the broker GET inventory and Percona ledger:

| Symbol | Percona `Decimal` | Broker GET string | Actual numeric relationship |
|---|---:|---:|---|
| D | 66.130000 | 66.13 | equal |
| SNPS | 435.610000 | 435.61 | equal |

An offline test using these exact scale pairs and otherwise matching order identity, client ID, side, bracket class and limit type raised `Unsafe("PAPER parent identity or bracket parameters mismatch")` with the installed code, even though the numeric prices are exactly equal. `reconcile_one` calls that check *before* collecting actual Alpaca FILL activities; `reconcile_once` catches the `Unsafe` exception and reports `UNKNOWN_READBACK` without updating the intent. The reproduced mismatch is a sufficient rejection cause, although later downstream checks still require independent testing after a repair.

## Safe isolated repair and offline regression

- Research patch `research/reconcile_parent_price_numeric_identity_20261119.patch` changes only the limit-price identity comparison to exact `Decimal` numeric equality, requires both operands positive and finite, fails closed for malformed values, and does not tolerate any positive price difference.
- Regression `research/test_reconcile_parent_price_numeric_identity_20261119.py`: **5/5** broker-disabled test cases passed. It also confirmed the installed baseline falsely rejects numeric equivalents and preserves broker ID, client ID, symbol, side, bracket class/type identity mismatches as unsafe.
- Installed production `reconcile.py` SHA-256 **0e65c1977b35e1202b082d04d90563bad41d05f11ac70c16040456009ef802da** unchanged. Staged source SHA-256 **fea90a5c404c388078f53dae57328f5182c63bd70f736a14ee6aa0add829e27a**.
- No PAPER or LIVE broker orders, Pushover, active V1 source edits, timers, stop orders, database writes, or service changes. There is **no production release authorization** from this research. Release requires separate consent and broker-native integration regression including parent/child identity, FILL activity UUIDs, partials, stop protection, fees, and source/account matching. For the two existing recommendations, do not infer fees or after-cost P/L from an accepted order or an OHLC proxy.

The separate SRM event scan found no newly verified unreported H1/H2 at 22:27 CT. Trading Strategy Research hourly schedule and enabled state remain unchanged.
