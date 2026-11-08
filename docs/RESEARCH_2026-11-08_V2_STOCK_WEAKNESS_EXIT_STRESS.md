# V2 stock-weakness timing, conditional exits, and five-session context — 2026-11-08

**Research only.** No V1 timers, PAPER/LIVE broker accounts, orders, or execution policy changed. This document reports offline tests using historical Alpaca SIP **split-adjusted** five-minute and daily bars, not fills or live predictions.

## Fixed rule and causal timing

A V2 individual-stock urgent alert requires **both**:

- latest completed five-minute bar close at least **2.5% below** the previous completed regular-session close; and
- latest completed bar close at least **1.0% below** the bar close 15 minutes earlier.

The last-15-minute drop is INCLUDED within the 2.5% cumulative drop. This is **not** a 3.5% total-loss threshold.

A five-minute bar timestamp denotes its **start**; the signal can first be issued at timestamp +5 minutes. No alert may use a future candle. Only the preceding calendar evening 16:00–20:00 ET, current premarket 04:00–09:20 ET, and (separately) current first regular hour through 10:30 ET are tested. Friday is NOT misrepresented as the immediately preceding evening of Monday; BOATS 20:00–04:00 ET is NOT available in this 52-week SIP replay. First regular-hour alerts can use a completed premarket price from 15 minutes earlier.

The current trigger is frozen across earlier (through Aug 31) and later (Sept 1–Nov 6, 2026) samples; this report does not optimize a threshold on the later interval.

## Reproduced baseline

250 evaluable close-to-close sessions from 251 daily sessions, Nov 7, 2025 to Nov 6, 2026. Nine symbols: AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM, INTC. Across **2,244 stock-days**, **209 stock-days** ended at least 5% below the previous completed regular close. Broad sector daily classifications: **118 positive / 83 negative / 49 mixed**.

Preopening 2.5%/1.0% rule: **208 stock-day alerts**, **81/209 severe stock-days detected (38.76% recall)**, **81/208 precision (38.94%)**, **127 alerts on nonsevere stock-days**. Of 81 severe events, **23** first alerted during preceding evening and **58** during same-day premarket. **50** of the 81 warnings were issued while observed price was still less than 5% down, but the other **31** were first detected only after the price was already at least 5% down. **128 severe stock-days** were missed before open.

Earlier period: 63/160 severe stock-days warned; later period: 18/49 severe stock-days warned. These are raw conditional rates, not an independent pristine validation of threshold choice.

One actual timestamp from the study: **WDC, Nov 13, 2025, 04:20 ET**, was first signaled at -3.672% since prior regular close, ahead of its >=5% regular-close decline. Other example: **SNDK, Nov 13, 2025, 06:25 ET**, at -4.826%. These are historical signals reconstructed from completed bars.

## Added first regular-hour warning window

| Metric | Before RTH open | Before open OR through 10:30 ET |
| --- | ---: | ---: |
| Flagged stock-days | 208 | 550 |
| Severe stock-days caught | 81 / 209 | 180 / 209 |
| Severe-event recall | 38.8% | 86.1% |
| Precision against >=5% close-to-close drop | 38.9% | 32.7% |
| Flags on nonsevere stock-days | 127 | 370 |
| Severe events first flagged *before price reached -5%* | 50 | 129 |

The first regular hour adds **99** previously missed severe events but **243** additional nonsevere alerts. Only **79** of those 99 new detections arrived while the stock was still less than 5% down; 20 were already at/under -5%. This is why the morning monitor should separately label *early warning* vs *already severe selloff* rather than present its 86.1% recall as pre-open prediction.

## Next-bar hypothetical exit versus holding

For **206/208** preopen stock-day warnings with both a contiguous next five-minute bar and a same-day 09:30 ET opening price, compare a **hypothetical immediate exit at the next bar open less a price buffer** to holding the share until the 09:30 open. All results are **percentage points of previous regular-close price, per flagged stock-day**, equal-weighted, not dollars or actual broker portfolio P/L. Two warnings lacked those price observations. Every executable fill is unverified.

| Assumed exit price discount | All 206 versus holding to 09:30 | Severe-loss subset | Nonsevere subset | All 206 versus same-day regular close |
| --- | ---: | ---: | ---: | ---: |
| 0 bps | -0.455 pp | +1.351 pp | -1.624 pp | -0.604 pp |
| 15 bps | **-0.599 pp** | **+1.208 pp** | **-1.769 pp** | **-0.748 pp** |
| 30 bps | -0.742 pp | +1.065 pp | -1.914 pp | -0.892 pp |
| 50 bps | -0.934 pp | +0.874 pp | -2.107 pp | -1.084 pp |

At 15 bps, hypothetical early exits beat holding to the next opening price on **92** flagged stock-days but were worse on **114**. The >=5% eventual-decline subset benefited on average, yet that label is not available at decision time. Selling every warning **lost** on average in this idealized counterfactual, and actual overnight illiquidity/spreads/queue misses might be worse. **Do not enable automatic liquidation on this signal alone.** Earnings/news/bid-ask confirmation and actual PAPER order readback are necessary.

## Upside coverage / prior five completed sessions

Using only earlier **five completed trading sessions** of broad semiconductor classifications (2 of 3 AMD/MU/SNDK aligned with SOXX), then labeling the *next* day retrospectively:

| Five completed-session history | Next evaluable sessions | Next broadly positive |
| --- | ---: | ---: |
| Five consecutive broad negative sessions | 3 | 1 |
| Three or four negatives | 49 | 28 |
| At least three broad positives | 121 | 55 |
| Other combinations | 72 | 32 |

Of 250 daily sessions, first sessions without five fully completed prior sector labels were excluded. **This is not the identical per-stock V1 five-down filter** and is not a buy signal: it demonstrates that a *pure five-consecutive-broad-negative-sector-days requirement* could cover at most 1 of the 116 scored positive sessions in this context. Uptrend continuation and opening reversal must be researched independently. A pre-open urgent alert on at least one AMD/MU/SNDK leader occurred on **19 of 118 actual broadly positive sector days** (and **35 of 83 negative sector days**). An unqualified sector-wide buy veto would skip genuine upward days.

## Limits and next test

- Historical five-minute OHLC cannot establish quote availability, actual extended-hours fills, broker queue position, slippage, partial fills, stop-order availability, or early-warning value beyond the observed price drawdown. A next-bar open **is not a guaranteed executable sale**.
- No prior-five future information enters the signal. >=5% final-close labels and next-day opening prices are scoring outcomes only. This test uses SIP, not full-year BOATS 20:00–04:00 ET, does not include synchronized earnings/guidance, calendar releases, futures, 1-minute microstructure, or actual PAPER holdings.
- Keep the alert informational. For future experiments, combine symbol-specific held-position exposure with earnings/guidance timing and actual bid/ask spreads; score the 09:45–10:30 ET first-hour extension distinctly, then validate on new sessions without retuning.
- Reevaluate profit-day coverage separately with causal bullish breakout/continuation entry models and actual broker fill/readback; the prior-five context table does **not** claim a profitable new strategy.

**Reproduce:** `python -m research.v2_stock_risk_dayphase --primary <52w SIP leaders JSON> --peers <52w SIP peers JSON> --daily <split-adjusted daily JSON>`. Local authorized inputs on www3 were `/tmp/semis_52wk_5min_sip_adjusted.json`, `/tmp/semis_peers_52wk_5min_adjusted.json`, and `/tmp/semis_52weeks_alpaca_daily.json`. Inputs are not committed and might be ephemeral. Tests: `PYTHONPATH=. python -m unittest research.test_v2_stock_risk_dayphase` (5/5 passed). No broker-order code is imported or called.
