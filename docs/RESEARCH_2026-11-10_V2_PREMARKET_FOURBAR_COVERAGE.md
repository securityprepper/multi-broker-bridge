# November 10, 2026 — premarket four-candle data-availability audit (V2 research only)

## New quantitative finding: simultaneous one-minute bars substantially overstate four-candle readiness

A previous seven-session report found **1,869 / 2,310 (80.91%)** exact-minute joint SIP trade-bar availability for SOXX, AMD, MU, SNDK in 04:00–09:30 ET. That is not equivalent to having four *completed, consecutive* one-minute candles ready for a trend qualification.

New offline reconstruction on **October 29–November 6, 2026** uses each intended decision at HH:MM:**40** ET, accepting only candle start timestamps HH:MM−4 through HH:MM−1, whose ending timestamps precede the decision by at least an illustrative 15-second publication allowance. First four minutes are excluded because data prior to 04:00 are unavailable. This leaves **2,282** candidate decision minutes (326 × 7 dates).

| Minimum required observed bars | Eligible decision minutes / 2,282 | Fraction |
|---|---:|---:|
| Four completed consecutive AMD bars | 1,786 | 78.26% |
| Four AMD bars and four for at least one of MU/SNDK | **1,785** | **78.22%** |
| Four consecutive bars for all AMD/MU/SNDK | **1,731** | **75.85%** |
| Four consecutive bars for SOXX and all three peers | **1,433** | **62.80%** |

The final 62.80% is a **strict four-symbol research requirement**, not the historical MBB's exact anchor gate; SOXX was not a substitute for its own-sector rising-shape stock anchors. The 78.22% AMD-plus-one number is a **necessary price-data availability condition**, not sufficient signal eligibility. MBB also requires actual rising highs/lows, absence of excessive single-bar leaps, valid sector state, quote freshness, broker position/open-order/account checks and permissible session/execution rules.

**Critical causal distinction:** a SIP row timestamped 04:18:00 ET represents the 04:18–04:19 minute and is *not* completed at 04:18:40. A broker or simulated strategy deciding at 04:18:40 may use the completed 04:17–04:18 row, not the 04:18–04:19 row. The historical November 9 03:18 CT ($457.95 at 03:18:40) opportunity must be reconciled to exact source-bar START/END and actual available quotes before any earlier-entry claim. This seven-session file **does not contain November 9**, so the exact 03:18 AMD skip reason remains **undetermined**; no claim is made that it was caused by missing bars.

This is a coverage/availability quality study, **not** a forecast-hit rate, BUY_WATCH count, safe order recommendation, expected profit, or executable bid/ask fill analysis. The source is historical split-adjusted SIP 1Min *trade OHLC*, not synchronized NBBO/BOATS, futures, news or contemporaneous broker evidence. It was previously examined, so **not** an untouched prospective holdout. A bounded new read-only Alpaca GET attempt from the isolated research shell returned `OrderRejected: Alpaca PAPER credentials unavailable`, without exposing keys or requesting any order; no additional bars were fabricated.

## Reproducible isolated code and safety

The source `research/v2_premarket_fourbar_availability_20261110.py`, ten offline tests, and full seven-day counts in `research/results/v2_premarket_fourbar_availability_20261110.json` were exercised in a separate www3 scratch directory (`/tmp/v2-run30-multibar`). **10 / 10 tests passed**, including future-bar exclusion, missing/invalid OHLC, missing SOXX versus actual peer gates, DST offsets, and the four-candle decision window. No user-facing trading signals or orders were generated.

The prospective GET-only sector recorder remains separate and begins at 09:35:25 ET; it does not provide premarket four-candle evidence. No V1 PAPER/LIVE service, broker positions/orders, production dirty worktree, divergent local research checkout, scheduled timers, 13:15 entry cutoff, 13:40 mandatory flat, 14:00 verification, or holiday cache was modified. Cached unpaused revision 2 remains valid strictly before Nov 13, 2026 at 16:13 Chicago absent a known calendar edit.

**Next:** collect independently time-stamped premarket SIP/BOATS candles and NBBO; inspect future MBB `buy_watch_symbols` and `skipped_buy_reasons` with contemporaneous read-only broker state; then measure 30+ untouched prospectively sealed signal dates and true after-spread forward outcomes. Retain the final low-false-alert thresholds. No new PAPER trading strategy GO.
