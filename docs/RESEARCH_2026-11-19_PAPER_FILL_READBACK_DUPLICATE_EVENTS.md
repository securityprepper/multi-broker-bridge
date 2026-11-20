# November 19, 2026 23:30 CT — read-only PAPER reconciliation duplicate-event audit

## Newly observed, source-verified data-quality implementation defect

The November 19 23:00 CT owner-approved, numeric-price reconciliation repair successfully resolved two previously blocked PAPER recommendation statuses. The surviving `CLOSED_NEEDS_FEE_RECON` state is intentionally revisited by the **every-minute read-only reconciliation timer** until fees can be verified. However, its production `reconcile_once` unconditionally calls `event(..., "BROKER_FILL_READBACK", result)` on each poll, even if the exact broker evidence is unchanged.

At the 23:30 CT hourly research check, read-only Percona aggregation of `sp_paper_rec_events` verified:

- One closed recommendation: **32 BROKER_FILL_READBACK rows with only ONE distinct SHA-256 of `evidence_json`**. Each repeats the same **4 actual distinct broker FILL activity IDs**, same 4 BUY shares and 4 SELL shares, same **-$16.04 broker-derived gross**, `fees_verified=false` and `net_pnl=null`. The extra 31 rows are **duplicate *readback receipts*, not additional fills or trades**. Another distinct unfilled recommendation correctly has one `UNFILLED_TERMINAL` event.
- The installed code's selected-status set includes `CLOSED_NEEDS_FEE_RECON`, so the duplicate receipts will grow by approximately one per minute while after-fee reconciliation is outstanding. This wastes durable audit storage and can corrupt a downstream report **if** it counts event rows instead of distinct fill activity UUIDs. No observed monetary double-counting was established; do not assert it.
- This is a **new, independently verified source/data correctness issue** discovered after the earlier price fix. It must not cause a recommendation-linked trade alert from Trading Strategy Research; Recommendation Audit remains the sole closed-trade notifier.

## Narrow research-only correction

Research patch `research/reconcile_readback_event_exact_evidence_dedup_20261119.patch` adds `record_readback_if_changed` and changes only the unconditional readback event insert:

1. Read back the most recent `BROKER_FILL_READBACK` JSON for the *same recommendation ID* within the current transaction.
2. Append a new event only if the canonical parsed JSON evidence materially differs or there was no prior event. Distinct actual FILL UUIDs, changed stop/protection or state produce a new event.
3. Malformed prior evidence fails closed; no fabricated fills, tolerance, order permission, canceled protection or broker writes.
4. Continue updating the recommendation's `last_checked_utc` each timer pass and leave broker GET, state, account, fee and protective checks unchanged. Do not delete/modify historical append-only rows.

**Offline broker- and DB-disabled unit tests: 8/8 passed** for identical evidence suppression, first new event, new FILL activity, changed protection, JSON key-order variation, malformed prior records, numeric parent price guards, and absence of broker order mutation. Existing reconciliation fixture suite remains **17/19 passed, 2 identical known failures** on omitted synthetic protective-leg quantities, matching installed production; no weakening of the installed protective fail-closed behavior was made.

Production `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/reconcile.py` remains SHA-256 `fea90a5c404c388078f53dae57328f5182c63bd70f736a14ee6aa0add829e27a`. **Not deployed, no broker POST/PAPER/LIVE orders, timer/service/V1/Pushover changes, DB writes or production code edits.** A separately authorized PAPER-safe reconciliation-only release, fresh holiday validation and broker-native readback integration test are required. This repair addresses event-level dedup, not fee verification itself; the outstanding after-fee net remains unknown.

At this same hourly run the root-owned fresh Chicago holiday gate was verified unpaused (revision `3300`, future boundary Nov 20 16:07 CT); the SRM native source journal had **11 unique H1 receipts, all previously sent**, and its durable ChatGPT sent-key ledger had **12 previously emitted exact episode-hour keys**. There were zero new verified SRM hours. No current sub-$5 ticker was recommended, displayed or ordered. The hour schedule and enabled state remain unchanged.
