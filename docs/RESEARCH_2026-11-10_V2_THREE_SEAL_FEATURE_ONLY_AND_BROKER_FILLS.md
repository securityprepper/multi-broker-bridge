# November 10, 2026 — Three sealed V2 sector slots and observed MBB PAPER fills

**Research-only, independent READ-ONLY host and Alpaca PAPER GET observations; 09:29 CST bounded broker snapshot.** No broker orders or production changes were made by this research. Active V1 PAPER/LIVE, host timers, risk gates, FDR pause, holiday rules, 13:15 entry cutoff and 13:40/14:00 liquidation/verification stay intact.

## Important: these V2 files contain FEATURES, not frozen UP/DOWN forecasts

The sealed `2026-11-10/0935.json`, `0945.json`, and `1005.json` were all present on www3 and the service journal independently reported `RESEARCH_SHADOW_SEALED` at 08:35:25, 08:45:25 and 09:05:25 America/Chicago. Completed-source-bar timestamp guard passed for every populated instrument. 09:35 ET had five sectors with usable features and two abstentions (gold miners/software); 09:45 and 10:05 each had all seven sector feature groups. All **21 sector classification fields were null** (`shadow_classification: null`), even where inputs were available. A null is NOT a sealed directional forecast. There are **zero UP/DOWN predictions available to score for forward accuracy**, not 19 predictions. No retrospective classification of these features may be counted as prospective accuracy.

Observed (descriptive, **not predicted**) 09:35-to-10:05 ET ETF marks: SOXX 144.300 -> 149.075 **+3.30908%**; XLE 60.570 -> 61.845 **+2.10500%**; XLF 58.165 -> 58.0558 **-0.18774%**; XLI 168.065 -> 167.870 **-0.11603%**; XLV 188.005 -> 187.530 **-0.25265%**. GDX and IGV had no original 09:35 mark, so abstain for this horizon. These are successive completed five-minute bar price marks, not executable bid/ask fills or validation of a precommitted direction. The first 60-minute result was not yet available at the beginning of this study, and 13:40 CT end-of-day comparison is not yet complete. Never use the later seal as a signal available at the earlier seal.

**Research infrastructure correction needed (not activated):** Before claiming 30+ untouched forward forecast days, freeze and seal a versioned rule ID and actual `UP`/`DOWN`/`ABSTAIN` classifications, separate feature availability from forecast coverage, and score only after the corresponding future mark exists. A deterministic rule applied after the fact to today's feature-only seals is an exploratory replay, not a precommitted forecast.

## MBB PAPER actual fills — new negative realized result

Read-only journal inspection from 08:30–09:25 CST found **65 SCAN_COMPLETE records** and **215 repeated BUY_WATCH candidate appearances**: 193 `NO_FRESH_BID_ASK`, 15 `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY`, and seven submitted BUY orders. Four submitted SELL orders were present before 09:25. Tracking count grew from 31 to 38, so the previously established cross-session entry lockout continues to affect some candidates but did **not** block all new entries. Counts are repeated observations, not 215 independent opportunities.

An independent **GET-only** Alpaca PAPER broker order, position and FILL readback as of **09:29 CST** confirmed seven MBB-tagged **fully filled buys** in PSX (7 shares), ZS (10), COP (14), MPC (5), RPD (136), BKR (41), WMB (29); and five MBB-tagged **fully filled sells** of ZS, RPD, MPC, WMB and PSX. FILL activity has 27 partial/full execution records for those 12 distinct broker orders. There were **zero working orders**; **BKR 41 shares and COP 14 shares** remained open and were also matched to MBB buy-fill quantities. No FDR-tagged order was seen in the bounded 12-order readback. This is not an all-account, all-day origin audit.

Five completed round trips all lost money. Broker FILL price arithmetic before fees: ZS **-$5.30**, RPD **-$20.40**, MPC **-$6.25**, WMB **-$8.70**, PSX **-$19.53**, total **-$60.18 gross realized PAPER**. No unrealized P&L, final daily P&L, hypothetical hold-to-13:40 comparison, or post-fee result is asserted at this still-open point in the session. The premarket >=2% profitable-sale rule does not govern these post-09:30 ET RTH exits; those exit reasons require separate direct diagnostics before attributing them to a particular stop. Market exposure on BKR/COP should continue to be protected by the existing V1 exit system; the research placed no orders.

## Safety and next validation

Keep the low-noise V2 notification standard: no BUY/SHORT based on SOXX/XLE's already-realized move or raw extreme thresholds. The precise original Nov 9 03:18 AMD skip reason is still not recoverable from that historical log. Do not delete the 31 historical tracking records or change MBB exit ownership/first-entry gates directly: live host cross-session tracking and cross-strategy ownership/dedup findings require a safely reviewed PAPER-only repair with independently complete order/FILL attribution. Continue 20+ untouched future dates with sealed forecasts and actual NBBO/spread/fill-cost validation, and separately review each completed day for major up/down misses.

## Reproduction

- New source: `research/v2_prospective_seal_feature_only_audit.py` (reads only pre-existing JSON; no broker requests, network, or writes to original seals).
- Tests: `tests/test_v2_prospective_seal_feature_only_audit.py` — **12/12 PASS** on an isolated www3 scratch tree; as-of timestamps, incomplete bars, missing sectors, null forecasts, future scoring, tiny moves and no broker permissions.
- Structured output: `research/results/v2_first_three_sealed_sector_slots_2026-11-10.json`. This includes only market price feature marks and fail-closed scoring labels, no account identity or credentials.
- Broker order/fill verification was a separate ephemeral GET-only request to allowlisted Alpaca PAPER endpoints using existing protected host credentials; it did not write to broker or persist identities.

No V1 files, timers, broker orders, host production code or LIVE permissions were changed.


## 09:37 CST broker verification update (separate, later snapshot)

A second independent GET-only PAPER readback at **2026-11-10 09:37:38 CST** confirmed **13/13 MBB-tagged broker orders FILLED** (seven buys, six sells), **zero open broker orders**, and **COP 14 shares as the only remaining account position**. BKR 41 shares had fully sold at 09:33:47–09:33:49 CST for $47.99, after buying 41 at $48.07: **-$3.28 additional gross PAPER loss**. Thus all six completed MBB round trips were losers as of this snapshot, and the cumulative observed gross realized PAPER result increased from **-$60.18** (09:29) to **-$63.46** (09:37), before trading frictions and data costs. The source of the BKR exit rule is not proven by this readback. The open COP position's unrealized result and a final full-day result are not established. No orders were submitted by the research.
