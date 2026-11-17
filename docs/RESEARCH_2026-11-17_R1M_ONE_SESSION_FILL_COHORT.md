# R1M one-session filled PAPER cohort — Nov 17, 2026 (research only)

As-of: approximately 08:39 America/Chicago, Nov 17, 2026. This is a **one-trading-day descriptive readback**, NOT a forward profitability/alpha validation and NOT a release proposal. The trusted root-owned holiday cache was validated unpaused within 150s freshness before any research or broker GET.

## Scope and provenance

Read-only Percona `securityprepper_r1m_paper` rows: source `R1M`, filled `OPEN_CONFIRMED` orders on Nov 17, with matching R1M exit order roles, broker order fill-price and timestamp readback, and closed-lot realized gross P/L. Exact verified receiving Alpaca PAPER account was checked before a separate GET-only activity inventory. That one account returned **66 DISTINCT FILL activity IDs** across all sources on date Nov 17, but these IDs are **not yet exhaustively linked to Percona order UUIDs**; do not call them 66 round trips or claim multi-account coverage. A later attempt to combine them programmatically was unavailable; no alternate credential path or POST was used. Fee attribution is unavailable; aggregate below is **GROSS**, not after-fee.

## One R1M session only

- Filled R1M entry order records: **20**.
- Fully closed R1M entries at readback: **20** (no open R1M lot according to the strategy ledger at that time; other-source accounts and positions are separate).
- Recorded gross realized P/L: **-$121.67**; **3 winners, 17 losers, 0 breakeven**; median observed hold **31.88 minutes**.
- Exits within strictly less than 2 / 5 / 10 / 30 minutes: **0 / 1 / 6 / 9**, respectively.
- Verified R1M exit intent-role ledger classifications: **7** `RESEARCH_CLOSE_CONFIRMED_TURN`, **5** `STOP_LOSS_0P50PCT`, **5** `STOP_LOSS_0P75PCT`, **2** `STOP_LOSS_1P00PCT`, **1** `DOLLAR_GAIN_MOMENTUM_FADING`. Intent roles identify the deployed journal branch; they do not independently verify the reason a specific broker fill occurred without a fill/order and contemporaneous strategy-version join.

The fresh broker GET at ~08:35 CST showed two short positions, NOW/R1M and SNDK/V2, with **zero broker working orders**. NOW subsequently had a native broker FILL activity for a two-share BUY at 08:38:10 CST, after which its Percona lot was marked closed. Do not mistake its earlier open status for a currently held position. The independently reported V2 SNDK signed-short software-stop defect is prior-known; it is not a new discovery from this snapshot. The R1M `broker_owned_position` source now uses absolute broker short quantity and may support software risk checks despite no broker-native stop; do not confuse R1M and V2 code paths.

## Analysis decision

**NO PARAMETER CHANGE / NO FORWARD EDGE / NO PUBLIC RESEARCH UPDATE.** Single-day losses are descriptive and not independently robust. No evidence of 20 distinct broker trading days, untouched forward holdout, verified fee/slippage, independently validated exit attribution for all source orders or profitable after-fee forward BUY. Do not launch another strategy, enable orders, change existing PAPER/LIVE stops, modify V1 settings or add alert noise. Carry forward exact activity ID/order UUID join, per-source and per-account coverage, genuine after-fee closed-lot reconstruction, and independent holdout as the next read-only investigation. Recommendation Audit alone notifies newly closed recommendation-linked trades.

No broker orders, stops, service schedules, timers, permissions, news clearances or V1 production code were changed.
