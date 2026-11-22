# Recognizable overnight and opening-session patterns — forward-only audit
**Research as of:** November 22, 2026, Chicago local time. **Historical period:** November 20, 2024–November 20, 2026. **Status:** research-only, no broker orders or production changes.

## Answer

The most distinctive **exploratory** pattern is unusually strong **sector peer breadth followed by a stock's own early upward confirmation**. This is recognizable after eight completed regular-session minutes (8:38 a.m. CT or later), not necessarily overnight. It is **not** a validated general BUY trigger. Simple overnight gaps and an otherwise apparently encouraging alignment with SPY and an ETF have not produced a stable forward edge on the date-separated tests. No new order or trailing-stop percentage is justified.

### Historical peer-breadth pattern

The UP rule first fires at or after eight completed one-minute regular bars when all are true *as of the minute*:
- At least 80% of independently counted, self-excluded sector peers have risen ≥0.10% **since that day's regular open**.
- SPY is ≥+0.10% and the assigned sector ETF ≥+0.20% since the same open.
- The ordinary stock is ≥+0.20% since the open and ≥+0.05% during the preceding five minutes.
- The assigned sector ETF has moved ≥+0.10% during the preceding five minutes.
- Original source one-minute completed trade bars and peer/ETF data exist, the last recent bars are not missing, and the event-time stock trade close is ≥$5. This is **NOT** an original issuer-specific news clearance or broker quote eligibility test.

For **SNDK only**, applying the exact UP rule and taking **only the first qualifying minute per date** yielded:

| Chronological sample | Distinct event days | Mean signed stock return from signal to 13:40 CT, less an assumed 0.25% roundtrip cost |
|---|---:|---:|
| Training | 35 | +0.2426% |
| Later validation | 34 | +0.3613% |
| Later check | 30 | +0.8840% |

The independent **later test** had **17/30** events exceed the 0.25% assumed cost threshold. Its estimated 95% mean interval using its 3.8877 percentage-point sample standard deviation is about **−0.51% to +2.28%**, *before multiple-testing correction or broker spread uncertainty*. Therefore there is **no proven statistically secure forward edge**, even though the means are positive in all three periods.

In the later 30 events, the **actual split-adjusted one-minute completed-trade closes after the original signal** averaged +0.62% at +5m, +0.61% at +10m, +0.27% at +30m, +0.68% at +60m, +1.10% at +120m (when historical bars existed), and +1.134% to the required 13:40 CT simulated flat. These are quote/bar returns, not executable bid/ask fills or after-fee broker P/L. [Underlying 99 historical rows](SNDK_EARLY_PEER_BREADTH_FORWARD_HORIZONS_HISTORICAL.csv) contain exact per-date event minute, source signal price, forward periods and missingness. Historically the ordinary stock's last regular-session completed price on November 20 was $79.28; this is **not a fresh live recommendation price**.

**Caution:** This is **one** train-selected symbol from **227** symbol-specific models considered across eight rule families, with validation dates already exposed to other exploratory strategy research. The historical membership universe is not point-in-time historical membership. Even this positive proxy may be a multiple-testing artifact, and trading remains **NO GO** until a new prospective cohort with real as-of news, broker spread, order, fill, stops and complete risk limits is independently verified.

### Wider results and failure to generalize

For **the broad semiconductor sector**, the less selective stock+SPY+sector ETF+peer continuation UP pattern had mean **hypothetical remaining returns after a 0.25% cost allowance** of **+0.2115%** (training, 3,085 observations), **+0.0469%** (validation, 1,904), **+0.0219%** (later, 2,125). Only **48.52%** of later cases cleared the hypothetical cost allowance; the mean is not economically meaningful after genuine fills/spreads. Therefore the positive result above cannot be generalized to semiconductors.

In AI infrastructure, the UP rule opposing an earlier negative gap had +1.0165%/+0.2682%/+0.2246% proxy means on 252/101/144 observations, but only 45.83% of the 144 later cases exceeded the assumed cost and these observations were clustered across just 31 dates; that also **fails a durable execution edge**.

The overnight **gap-rejection** DOWN pattern is recognizable before the 8:30 a.m. CT RTH open: a prior-close **upward** gap of ≥2% by the snapshot, followed by a **≥0.5% decline over the last 30 verified premarket minutes** while the sector ETF also declines ≥0.15% over those 30 minutes. As a hypothetical short from the *later open* to the intraday flat, its cost-adjusted directional proxy varied dramatically: **−0.3925%** (97 training events), **−0.7462%** (193 validation events), then **+1.0137%** (303 later events). *The later favorable number is a regime reversal, not a stable rule.* Borrowability/spread are unverified; no short is authorized.

### Distinguishing full-day labels from actual future

Historical full-day UP/DOWN/MIXED labels can include a move that occurred **before** the theoretical signal. **These newly computed outcomes do not:** the opening-session pattern measures signed price change strictly from the completed signal-time minute to the required 13:40 CT (or official early-close adjusted time). The overnight rules measure the movement after the future 8:30 CT regular open to flat; they do not count the preceding overnight gap as a profit. Every symbol-date and rule-side uses only its first qualifying detection to avoid re-counting repeated consecutive minutes. Split-adjusted Alpaca SIP/BOATS one-minute bars are not guaranteed executable NBBO bids/offers. Calculated mean proxies subtract 0.25% roundtrip only, not actual verified broker costs. Multiple symbols on one day are correlated and should not be counted as independent market regimes.

A **research-only lookahead correction** was made before finalizing this audit: the $5 price floor is applied at the historical **detection time**, and subsequent drops below $5 are kept as valid negative outcomes rather than discarded as if known in advance. No active scanner, news veto, broker orders, stop process, schedule, or timer was modified.

## Source artifacts

- [Reproducible early-session 8-pattern source](subsequent_direction_8pattern_20261122.py), [normalized 48-row early-session aggregate](SUBSEQUENT_DIRECTION_NORMALIZED_FORWARD_ONLY_BY_PERIOD.csv), [early-session sector breakdown](SUBSEQUENT_DIRECTION_NORMALIZED_FORWARD_ONLY_BY_SECTOR.csv).
- [Reproducible overnight six-pattern source](overnight_6pattern_following_day_20261122.py), [36-row overnight segment aggregate](OVERNIGHT_PATTERN_AGGREGATE_BY_PERIOD.csv).
- [Reproducible first-matching SNDK lead](sndk_peer_followthrough_20261122.py), [99 per-event period outcomes](SNDK_EARLY_PEER_BREADTH_FORWARD_HORIZONS_HISTORICAL.csv).
- Source archive: /var/lib/securityprepper-two-year-sector-backtest, /var/lib/securityprepper-two-year-early-session-research, /var/lib/securityprepper-two-year-intraday-research on authorized www3 (local root-owned detailed archives); retained history remains separate from user-facing under-$5 filters.

**Decision:** research-only; no new BUY or SHORT instruction, no change to protective stops or existing live/paper execution.
