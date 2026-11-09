# 2026-11-09 V2 precision-first threshold stress — 52-week semiconductor SIP 5-minute replay

**Research only — no broker orders, no V1, Alpaca PAPER or LIVE configuration changes.** Canonical branch: `research/rebound-v2-conditional-exits`.

## Inputs and causal definitions

Read-only split-adjusted five-minute SIP datasets `/tmp/semis_52wk_5min_sip_adjusted.json` and `/tmp/semis_peers_52wk_5min_adjusted.json`, nine tickers (AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM, INTC). This replay has **2,281 valid stock-days across 254 dates** after its own full-RTH-history gate, with **248 major declines** and **297 major advances** defined by EITHER previous regular close-to-close >=5% magnitude or open-to-close >=5%. In this cohort 213/258 are >=5% previous-close-to-close alone, and 123/143 are >=5% RTH-only. This is a **different inclusion/outcome definition** from the earlier 2,244-row, 209-down, 254-up study; do not combine denominators. Prior full 250-session SOXX baseline remains 118 positive/83 negative/49 mixed and is not recomputed here.

For each day, the detector uses only the previous COMPLETED regular-session close; first completed five-minute bar satisfying BOTH absolute previous-close threshold (2.0, 2.5 or 3.0%) AND >=1.0 percentage point movement in the SAME direction over the most recent 15 minutes. The 15-minute change is **included** in the total; not additive. Optional sector confirmation requires SOXX >=0.5% directional and >=half of at least five contemporaneously available OTHER semiconductor peers >=0.5% directional, using only candles completed by the decision time. A quote from the upcoming five-minute bar, today's final close, the later low and the next opening are NEVER signal features.

## Strong movement recognition vs false alerts

With **sector confirmation**, all-day first-warning comparisons:

| Threshold and direction | Severe-day hits | Other-day warnings | Precision of warning as a >=5% final-day outcome | Hits before already +/-5% | Before 9:30 ET |
|---|---:|---:|---:|---:|---:|
| 2.0% DOWN / >=1pp in 15m | 209/248 | 417 | 33.4% | 135 | 74 |
| 2.5% DOWN / >=1pp in 15m | 207/248 | 360 | 36.5% | 132 | 66 |
| 3.0% DOWN / >=1pp in 15m | 203/248 | 297 | 40.6% | 128 | 61 |
| 2.0% UP / >=1pp in 15m | 239/297 | 419 | 36.3% | 146 | 77 |
| 2.5% UP / >=1pp in 15m | 236/297 | 344 | 40.7% | 143 | 74 |
| 3.0% UP / >=1pp in 15m | 235/297 | 271 | 46.4% | 138 | 63 |

*Precision here = proportion of warning stock-days that ultimately had a >=5% closing-day or RTH move in the signalled direction. This is NOT profitable-trade precision or early-warning sensitivity. At least 80% major-move recall may be attained while the majority of alerts are false/nonsevere.* A 3% threshold yields fewer alerts than 2% but still **297 nonmajor DOWN warnings** and reduces both early and preopen detection. Do not activate a 2/2.5/3% automatic emergency sell based on this evidence alone.

The earliest severe-case first warning in THIS alternative-rule sample was SNDK on **2025-11-04 at 09:15 ET**, with the sector-linked two-percent through three-percent DOWN variants. This does not replace the earlier distinct V2 preopen union study's 2025-11-13 04:20 ET WDC earliest signal.

## Execution and earlier/later results

For marked trades, take the **OPEN of the next five-minute candle** after the signal, then the 16:00 regular close or the NEXT regular-session opening, minus assumed **0.30% round-trip friction**. This is a scenario, NOT executable SIP/BOATS bid/ask or a broker-confirmed fill. Extended hours limit eligibility, spreads, partial fills, delayed orders and risk of no fill remain unmeasured.

With sector confirmation, the earlier (<Sep 1) vs later (Sep-Nov 2026) results were:

| Threshold | Earlier AFTER-cost success rate through same close | Later AFTER-cost success rate through same close | Earlier modeled early SELL vs next open | Later modeled early SELL vs next open |
|---|---:|---:|---:|---:|
| Down 2.0% | 45.9% | 51.9% | -1.284 pp | +0.957 pp |
| Down 2.5% | 45.1% | 50.5% | -1.504 pp | +0.677 pp |
| Down 3.0% | 43.6% | 51.2% | -1.614 pp | +0.408 pp |

On **upside BUY** variants, the later same-close AFTER-cost success rates were 43.3% (2%), 42.5% (2.5%), and 37.3% (3%), with later mean modeled returns respectively -0.462%, -0.343%, -0.454%. Even these overly favorable bar-open proxies do NOT reach the target 80% profitable purchases. The statistical 95% Wilson lower bound for later 2.5% DOWN same-close win rate was only 40.7%; independently correlated trading days and news regimes could make uncertainty still wider. These thresholds are NOT a validated walk-forward deployment selection.

## Decision and blockers

**No trading GO.** 2.5% total including 1pp in 15m should remain a research baseline/watch criterion; 2% is more sensitive and noisier, 3% is less noisy but still not precise and slower. Avoiding false alerts requires independently validated additional information, not simply hiding warnings; keep hard broker safety exceptions intact. Gold/miners, energy, financials, industrials, software and healthcare are *not* evaluated by these semiconductor files. The required 52-week sector-specific as-of SIP/BOATS/1m/futures/news data and V1 matched fill records are not available in this replay; no reliable gold-to-miner lead/lag or sector-specific BUY threshold can yet be claimed.

Last-24-hour read-only www3 inspection confirmed active Alpaca PAPER sector and five-day-rebound entry loops and IBKR BUY fills; entry strategy/account-level matching remains incomplete. This V2 research does not modify, disable, or place/cancel any broker orders, and existing V1 PAPER and LIVE timers/exit safeguards remain untouched. A separately reviewed entry-only PAPER permission gate is necessary if future authorized strategy deployment is requested.

**Reproduce:** `python3 -m unittest -v research.test_v2_reliability_threshold_grid`; then `python3 -m research.v2_reliability_threshold_grid --out grid.json` on the isolated research host holding the read-only inputs. Machine-readable summary: `research/results/v2_reliability_threshold_grid_results_20261109.json`. Fifteen offline regression tests passed, including no-future-bar and previous-completed-session guards. No news labels or next-bar prices were used as detector inputs.
