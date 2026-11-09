# V2 sector direction first — owner clarification 2026-11-09

**RESEARCH/PAPER DESIGN ONLY. No new broker orders or installed runner. V1 PAPER and LIVE must not change.**

## Success criterion
The owner's **80%** target is the percentage of correct UP/DOWN **sector-direction forecasts**, NOT profitable trades. Forecasts are scored as of explicit, timezone-aware decisions before market open and during RTH. Predefine the direction reference: previous RTH close to that day's RTH close (primary); regular open to regular close (secondary). A weak move can be labeled NEUTRAL with a training-period-selected band, not silently discarded. Record ABSTAIN for no reliable prediction; report coverage and directional precision so a tiny handpicked number of calls cannot masquerade as 80% success. Use independent rolling chronological out-of-sample dates. Both UP and DOWN precision must be reported, along with balanced recall and confusion counts, false emergency alarms, earliest time of first correct forecast, late reversals and misses. Do not use future bars, final close, or later news in signals. Uncompleted Nov 9 day is NOT an evaluated outcome yet.

Forecast checkpoints: preceding evening, 08:30, 09:25, 09:45, 10:30, 12:00 and 13:00 ET. At each checkpoint freeze only observed sector ETF, peer breadth, futures, quote liquidity and timestamped as-of news. Re-evaluate forecasts independently; changes of direction are new, timestamped forecasts, not retroactive rewrites. Compare first forecasts versus eventual direction across every day, including missed semis and gold miner rises on Nov 9 when official closes are available. Severity/emergency levels must be sector-volatility normalized and separately tested; no blanket 2% threshold for gold and semiconductors.

## PAPER emergency action workflow to validate separately
1. A sector emergency event must have independent OOS evidence for significant subsequent direction, a fresh feed and a unique idempotent event ID. A direction forecast is not itself a trading authorization.
2. Read PAPER broker account identity, available long and short inventory, working orders, fills and all existing protective orders; identify only the approved sector-specific stocks and leveraged/inverse ETFs. Reject unsupported shorts, thin liquidity, stale quotes, market-closed/untradeable instruments, unverified stop/exit coverage and duplicate cross-broker risk.
3. Prefer to cancel/reconcile conflicting **entry** orders first; then close verified opposing positions with price-bounded orders; wait for exact broker-confirmed fills/partial fills/cancellations, preserve existing protective exits until reconciled. Unknown state => STOP and escalate, do not double-submit or accidentally short.
4. Only after opposing exposure is confirmed flat and all caps pass may a **separately commissioned PAPER executor** propose the corresponding new sector direction, capped by account and sector budgets, with bounded limits, safe time exit and protective risk. For negative forecasts use permitted inverse ETF/short options only if the specific account, instrument and session support them. No naked shorts by default.
5. Record decision, evidence, predicted direction, broker request ID, fill price, remaining risk, and next-session outcome. Kill-switch and health watchdogs must remain independent and exit-capable even if new entries are disabled.

No emergency automatic buys/sells are enabled by this documentation or V2 research. Explicit isolated PAPER execution approval/review and live market data integration are required. LIVE always separate.

## Short reporting
No routine price-change/noise table. Format: `SEMIS — UP, confidence X, as of HH:MM ET, significant move: YES/NO; EMERGENCY: reason/position action (PAPER test only)`. Similarly GOLD MINERS and other independently validated sectors. If not validated or current confidence below threshold: `NO RELIABLE SECTOR DIRECTION`. Never invent 80% accuracy, certainty, or actual order success.

Code: `research/v2_direction_accuracy.py`, tests `research/test_v2_direction_accuracy.py`. This scorer measures forecast evaluation, not an empirical claim or order authorization. Prior 52-week semiconductor and gold miner outcome audits remain available, but need frozen as-of forecasts and later holdouts before claiming directional accuracy.
