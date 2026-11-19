# Nov 19 2026 — R1M scan-clock cutoff bypass at broker-submit time

**Classification:** NEW PAPER broker-entry safety implementation blocker, verified in exact installed code and isolated broker-disabled regression; **not** evidence of an actual late trade and **not** an approved production deployment.

## Fresh holiday authorization and scope

At 2026-11-19 03:35 CST, and again at 03:38 CST, the current authoritative root-owned /var/cache/securityprepper-holiday/task-gate.json on www3 independently passed schema_version 1, status_valid, America/Chicago timezone, revision/coverage, unpaused, freshness <=150 seconds, valid_until and next_check_at checks. All source inspections and simulations were read-only toward Alpaca, IBKR and other brokers. The following files are produced on the separate research branch; the deployed PAPER executor, live trading, commissions, timers and broker settings are untouched.

Installed module SHA256: `350a8646254cfd2ad1381002a43af30fe0d081ad5c99b81d2c4f9a6fbc302285` at `/opt/securityprepper/direction-paper-executor/one_minute_research.py`.

## Reproduced defect

The recently deployed positive entry predicate `r1m_entry_allowed(now)` correctly rejects the 13:15 CT deadline **for the timestamp it receives**. But `research_open(db,signal,now,...)` receives a **scan-start timestamp**, checks that once, performs broker inventory, asset verification, quote retrieval, news clearance, account/buying power and stop-arm selection, and then calls `dp.attempt_order(...,now,broker)` using the **same old timestamp**.

In `direction_paper.py`, `attempt_order` reads the actual receipt clock for its ledger but does **not** enforce a last-entry wall-clock window before `broker('POST','/v2/orders',payload)`. `quote_snapshot` correctly compares market-source quote age to the real receipt clock, but it does not enforce the entry cutoff. Therefore, after a scan begins before 13:15 CT, a legitimate fresh quote and valid clearance after 13:15 can still reach a new PAPER order intent. The cutoff itself is therefore vulnerable to **time-of-check/time-of-use drift**, independently of the now-correct 19:00 CT rejection.

Example: scan at **13:14:58 CT**, broker/source quote at **13:15:08 CT**. The initial predicate permits the old scan timestamp, while an actual 13:15:08 timestamp fails it. Nevertheless the tested code reaches a fake/mock-only PAPER POST.

## Isolated proof

`research/test_r1m_cutoff_toctou_20261119.py` contains two green no-network tests: three distinct deadline-crossing timestamps and an end-to-end call of installed `research_open` and `dp.attempt_order`, with temporary SQLite as a **test fixture only**, fake PAPER broker, mock quote/news/account, and injected receipt-clock time. It asserts that 13:15:08 would be rejected if checked directly, yet the old scan clock permits **one simulated fake POST**. This tests the current defect, not the proposed future fix.

A bounded read-only query of Percona's R1M `OPEN_CONFIRMED` order-intent ledger for November 14–19 found **49 actual PAPER POST attempts** (November 17: 20; November 18: 20; November 19: 9). None has `before_order_utc` outside the permitted weekday 03:00–13:14:59 CT window. The defect is **confirmed in code and simulations, not in realized out-of-cutoff orders**. No native trade fill or after-fee return is inferred from attempts.

## Required narrow correction — NOT released

1. At the final R1M PAPER `OPEN_CONFIRMED` submission boundary, retrieve a **fresh real current UTC clock** and re-evaluate `r1m_entry_allowed(real_receipt_now)`. Fail closed if at/after 13:15 CT or outside SIP weekday session. A short pre-cutoff safety buffer may be needed for nonzero network-submission latency, conservatively tested without loosening the original deadline.
2. Ensure the final verified quote, issuer negative-news clearance and receiving-broker conditions remain contemporaneously valid at that final boundary; do not replace them with the original scan timestamp.
3. Add deterministic mock-only tests for 13:14:58→13:15:08, normal before-cutoff admission, after-hours BOATS/weekend denial, and no duplicate reservation/order POST in boundary retries.
4. Do not modify active V1 or LIVE code, stops, hours, order permissions, Pushover or timers. No broker order should be sent from research. The separate cross-session cap carryover blocker is already known and **not a new finding**.

## Integrity status

The prior 13:15 positive eligibility gate and persistent 13:40 CT original-fill flat-deadline repair remain installed and successful in their separate earlier tests. This research does not claim a new profitable strategy or a recovered missed opportunity. Recommendation Audit is solely responsible for newly closed recommendation-linked trade notifications. No actual broker orders or production code changes were made by this investigation.
