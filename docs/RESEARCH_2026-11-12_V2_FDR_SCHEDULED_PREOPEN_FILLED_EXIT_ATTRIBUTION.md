# 2026-11-12 — Exact FDR scheduled-preopen exit attribution (research only)

## New independently supported finding

The nine **Alpaca PAPER FDR** buy/sell pairs from **2026-11-09 America/Chicago** had **nine actual broker-FILLED sells**, all negative, totaling **-$118.22 gross before commissions/fees**. The exact fill timestamps were reconciled to contemporaneous original `trading-five-day-rebound-paper.service` journal `PREOPEN_EXIT_REQUEST:<symbol>` actions for **9/9** symbols. The FDR source's `FIRST_EXIT=time(8,30)` **America/New_York** and `EXIT_MANAGEMENT` clock branch explain **why the FDR exit requests occurred**. This is a time-scheduled premarket liquidation cohort, **not evidence that MBB's 1% profit, -1% loss, trailing or two-down-bar triggers were responsible**.

FDR sent **seven** sell requests at **07:30:12 CST**, and their corresponding broker fills occurred **07:30:13–14 CST**. INTC and WDC initially appeared as `NO_FRESH_EXIT_QUOTE`, so FDR issued their sell requests only at **07:32:12** and **07:37:12 CST**, with verified broker fills **07:32:14** and **07:37:13**. Thus **2/9 scheduled liquidations were delayed by quote-freshness gating**, without falsely treating order acceptance as a fill.

| PAPER FDR symbol | Filled SELL CT | Gross fill P/L |
| --- | --- | ---: |
| AMD | 07:30:14 | -$17.92 |
| AVGO | 07:30:13 | -$9.72 |
| INTC | 07:32:14 | -$15.05 |
| MU | 07:30:14 | -$10.28 |
| NVDA | 07:30:13 | -$12.10 |
| SNDK | 07:30:14 | -$15.78 |
| SOXX | 07:30:13 | -$12.46 |
| TSM | 07:30:13 | -$10.00 |
| WDC | 07:37:13 | -$14.91 |

Each filled FDR exit was a limit order. Real filled holding durations ranged approximately **23–30 minutes**. No alternate execution prices or executable improvements are inferred.

## Audit method and boundaries

- Reused the **previously authenticated one-account PAPER** historical dataset with nine unique FDR filled entry/exit order-UUID pairs; source and broker fills previously reconciled separately. This run did **not** query or place orders.
- Read original `journalctl -u trading-five-day-rebound-paper.service` JSON for 2026-11-09 07:29:50–07:39:00 CST; parser requires FDR strategy, `EXIT_MANAGEMENT`, exact symbol and session and a preceding `PREOPEN_EXIT_REQUEST` no more than 20 seconds before the broker **fill**. Stale-quote actions alone are **never** counted as sell requests. All 9 matched. The journal explains FDR's **order intent**; the independent broker fill confirms the execution.
- Source branch file examined read-only: `multi_broker_bridge/paper_rebound_runner.py`. Source at investigation time confirms scheduled 08:30 ET exit; exact historical source commit/version at execution was not sealed, so classify **journal-supported scheduled exit**, not a bit-for-bit historical version attestation.
- Distinguish this 9-trade FDR cohort from the **51 MBB** filled round trips in the same prior three-session dataset. Ordinary MBB exit triggers remain **UNKNOWN** without historical per-order decision evidence. Do not combine their exits under one trigger explanation.
- The **60** previously paired PAPER round trips covered only **three distinct trading days**, so the required 20+ independent days, executable one-minute bid/ask paths, actual alternative fills, fee evidence, stop-first ambiguity checks, and forward held-out validation are still missing. All nine FDR trades were already made; no contemporaneous material-negative-news clearance is attested and none is being retrospectively labeled BUY.
- Current FDR NEW entries remain paused pending validation; this is **not a recommendation** to resume FDR, hold past its current exit window, or change any PAPER/LIVE execution. Preserve V1, 13:15 entry cutoff, 13:40 flatten/14:00 latest flat, broker protections, holiday gates and other tasks.

## Reproducibility

`research/v2_fdr_exit_clock_join_20261112.py` accepts an authorized private historical filled-pair JSON plus original journal JSONL and emits a sanitized result excluding UUIDs/account IDs. `tests/test_v2_fdr_exit_clock_join_20261112.py` has **8/8 passing** offline tests for symbol/time matching, not substituting quote skips or acceptances for fills, duplicate detection and fail-closed unknowns. The nonsecret aggregates are in `research/results/v2_fdr_scheduled_exit_attribution_20261112.json`.

**Decision: RESEARCH ONLY / NO EXIT POLICY GO.** The newly identified FDR exit trigger explains order timing, **not** whether a longer hold would have been profitable after risk and executable costs.
