# November 11, 2026 — Independent PAPER rapid-exit peak provenance audit (research only)

## New source-level finding, observed impact bounded

The installed `multi_broker_bridge/auto_paper.py` at authorized www3 was inspected read-only on November 11 after the RTH two-falling-bars correction. In the MBB PAPER executor, `tracked.entry_time` is stored as the *order-submission/acceptance clock* (`now.isoformat()`) immediately after a successful PAPER BUY submission receipt. When a broker position later appears, the program derives `updated_peak` from historical one-minute bar highs whose **bar start time is >= that submitted-at timestamp**, rather than from the time the **first share actually filled**. The high-water state is then persisted and passed as `Holding.highest_since_entry` into `TrendMonitor.scan()`. The regular-session peak-trailing rule can issue a sell candidate if an apparent peak was at least +0.5% and the current close is at least 0.5% below that peak.

**Latent correctness defect:** A delayed order can have one or more complete minute bars between its submission and its first actual FILL, when there was *no owned position*. Their highs are currently eligible to be counted as a peak of an owned position. A candle overlapping a later fill also cannot prove that the high occurred *after* the fill. This may cause a fictitious 0.5%-armed trailing reversal and an unnecessary small-loss SELL. It does not prove that any particular historical rapid exit had this cause, and it is separate from the already corrected two-falling-bars condition.

**Broker-free exact-code demonstration:** Using the installed pure `TrendMonitor.scan()` with an entry price of $100 and last completed close $100.20, passing a fictitious prefill peak $101.30 produces `trailing peak reversal` and a `SELL_LIMIT_CANDIDATE`. Passing a postfill-only high $100.35 holds the position with no exit. No broker was contacted for this demonstration.

## Bounded authenticated broker evidence

Read-only comparison used a previously authenticated, PAPER-only, complete-for-its-reported-scope recent-order snapshot, plus the already collected historical SIP one-minute bars. It covers one authenticated PAPER account, **51 filled MBB BUY orders across November 9–11**, not other accounts; FDR has separate logic. Median observed BUY submission-to-final-fill delay was **1.63 seconds**, maximum **58.695 seconds**. **3/51** delays exceeded 10 seconds; **2/51** exceeded 30 seconds; **0/51** exceeded 60 seconds. Exactly **2/51** orders had a completed one-minute-bar *start timestamp* between their submission and their final fill. **0/51** had such a prefill bar's recorded high at least +0.5% above the broker average fill price. Because the snapshot reports the *final order fill* and not necessarily the *first partial-fill activity*, this is only a potential-contamination screen, **not evidence that those two bars were entirely before first share ownership**. No actual false trailing exit was attributed to this source defect from the available broker evidence, and earlier reasons remain UNKNOWN without decision/order/fill UUID joins.

There are still only **three distinct broker-traded session dates**, not the required 20+ prospective sessions. Existing historical target/high-touch figures are not executable fill probabilities or after-fee positive edges.

## Research-only mitigation prototype

Added a pure helper `research/v2_peak_first_fill_guard.py`, with eight passing synthetic integrity tests in `tests/test_v2_peak_first_fill_guard.py`. It requires *broker-verified first FILL activity time*, not order acceptance or final filled-order time when partials exist; excludes the minute overlapping the first fill; considers only fully completed subsequent one-minute bars; rejects duplicate or missing minutes with **UNKNOWN** rather than asserting clean history. It is a bounded research comparator, **not a complete production stop system**. Missing evidence must not disable native broker protection, the existing software emergency exit or the 13:40 Chicago forced flat.

A PAPER-only release fix would need to:
1. Identify the first actual partial/full buy FILL per verified account/order UUID, reconcile with position quantity, and persist that provenance on all subsequent scans (without resetting a real high-water mark).
2. Exclude prefill and fill-overlapping candle highs from the causal trade-specific high watermark; keep trusted postfill streaming quote highs and authenticated broker readbacks, and preserve native protection and 13:40 flat.
3. Validate partial/unfilled limit orders, restarts, session boundaries, quote gaps, duplicate orders and emergency/forced exits independently before PAPER deployment.
4. Shadow-test the candidate on 20+ new distinct sessions, scoring actual broker P/L and after-cost counterfactuals by source and account; recommendation-linked completed trades remain the Recommendation Audit's notification scope.

**No V1 PAPER/LIVE active source, service, broker order, stop, timer or holiday gate was changed.** No proof exists that this defect caused the November 9 AMD sale or any of the other 60 historical paired round trips. The MBB negative-news entry clearance gap previously identified remains a separate known blocker; this finding does not authorize new PAPER BUYs or modifications.
