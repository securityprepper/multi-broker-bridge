# V2 precision-first semiconductor emergency thresholds and six independent sector holdouts — November 9, 2026

**RESEARCH ONLY — NOT permission to place PAPER or LIVE orders, change V1 monitors, stop exit timers or alter any broker order.** Holiday cache previously validated unpaused rev2, strictly before 2026-11-13 16:13 America/Chicago unless invalidated.

## Major new finding: the 80%-precision objective is not yet met

This run separates **recall of eventual large declines** from (a) **precision of a useful sell** and (b) **the percentage of modeled BUYs profitable after costs**. Raising absolute downside thresholds reduces alert count, but does **not** improve modeled sell precision. The cross-sector bullish momentum checks likewise have low after-cost profit precision; gold is not an exception.

### 1. Semiconductor emergency-alert experiment — actual timestamped 52-week SIP 5m bars

Existing split-adjusted Alpaca SIP five-minute OHLC files for AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM and INTC, November 2025–November 6, 2026. To compare with earlier V2 reports, the script uses a **published immutable static matched-scoring manifest** of the existing **2,244 stock-days / 209 >=5% close-to-close decliners**. The manifest and future labels are used **only in the after-the-fact score** and never as inputs for signal evaluation. Other raw parsed days are deliberately excluded from final comparative counts. Existing sector-only baseline: **118 positive, 83 negative, 49 mixed sessions** across 250 sector-labeled dates.

For each stock-day and every **completed** five-minute bar from 04:00–15:50 ET, evaluate previous completed session's RTH 15:55 bar-close reference. Momentum is the last 15 minutes in **percentage points of that same previous close**. Thus `-2.5% total INCLUDING -1.0pp in the last 15m` means two **overlapping**, not additive, conditions. Alert clock is completed-bar end, and future price is never used in the decision. Optionally require SOXX and contemporaneous peer breadth (only completed matching timestamps). Missing quotes or prior close fail closed.

| Down rule: total / last15 | Alerts (stock-days) | Serious-down hits / 209 | Warnings on non-5%-down days | Warnings before already down 5% | Useful early sell vs next RTH open, after 30bp modeled friction | Mean early-sale advantage vs holding |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2.0% / 1.0pp | 749 | 201 | 548 | 140 | 40.85% | **-0.5307pp** |
| **2.5% / 1.0pp** (original owner rule) | **658** | **199** | **459** | **136** | **39.51%** | **-0.6882pp** |
| 3.0% / 1.0pp | 572 | 199 | 373 | 135 | 38.11% | **-0.7467pp** |
| 2.5% / 1.0pp plus SOXX and peer breadth | 550 | 188 | 362 | 114 | 40.36% | **-0.8012pp** |

A `non-5%-down` warning is NOT automatically a losing trade: the primary practical false-positive test is whether a hypothetical early exit would be worse than holding through the following opening. With modeled 30bp costs, **none of these sell rules reaches even 50% useful-sell precision**, let alone 80%. The early-period averages are worse than the September–November averages, showing important regime instability. Each row is a hypothetical *next-5m-bar open* selling scenario; neither an actual quote nor a fill, and premarket signals comparing with the same morning's open cannot prevent already completed overnight gaps. Under a 60bp roundtrip-friction stress, outcomes deteriorate further.

**Earliest matched severe-loss warning:** WDC, **November 13, 2025 at 04:20 ET** for all unconfirmed 2% / 2.5% / 3% overlapping rules. Breadth confirmation delays the earliest corresponding case to 08:35 ET. The strict 2.5% case **misses 10 of 209 major decliners**, while 2% misses eight, and many warnings occur only after significant damage. These counts are distinct from earlier union alerts that trade higher recall for >1,200 warnings on nonmajor down days.

A 27-policy grid combines absolute 2.0/2.5/3.0%, last-15m 0.5/1.0/1.5pp, and no/SOXX/SOXX+peers confirmation. Selection **using earlier data alone** favored 2.0% / 0.5pp with SOXX-only at just **42.88% useful-sale precision and -0.479pp modeled average sell benefit** in training. Its later-period holdout reached only **50.31% useful-sale precision**, +0.0955pp modeled sell benefit at 30bp and **-0.2045pp at 60bp**. That is NOT a positive trading decision or reliable precision benchmark.

**Do not replace any broker-native protective stop with these V2 candidates.** Existing V1 safety/watchdog exits remain outside this research task's authority.

### 2. Gold and five other sectors — independent 52-week public *hourly* proxy study

A distinct no-credential read-only market-data study retrieved public Yahoo Finance 60-minute RTH chart observations through **November 6, 2026**, across **246 complete comparable sector ETF sessions**. **This is not Alpaca SIP, BOATS or actual NBBO**. It cannot establish the fast premarket 5m/1m limit prices, actual fills, futures/news timestamp leadership, or whether a gold move arrived early enough to buy an individual miner at an executable price. It is an independent preliminary holdout intended to reject weak hypotheses, not to authorize orders.

At 10:30 ET, after the completed 09:30–10:30 first-hour bar, compare the sector anchor and target versus their **preceding completed day's** close; for the prior-five variant use the last **six prior completed daily closes**, never today's closing price. Simulate entering the target ETF at the following 10:30 hourly opening **mark** and selling at that day's last RTH bar close, deducting 30bp or 60bp roundtrip costs. A bar-opening mark does not prove a fill. First-hour signals at 10:30 cannot capture earlier gold miner gap-up profit.

| Sector, leading anchor -> target ETF | Positive / negative / mixed target sessions (>=0.75pp / <=-0.75pp / remainder) | Dual anchor+target bullish signals | After-30bp profitable signals | Precision (all 52 weeks) |
| --- | --- | ---: | ---: | ---: |
| **Gold/precious miners: GLD -> GDX** | **107 / 89 / 50** | **88** | **30** | **34.09%** |
| Energy: XLE -> XOP | 98 / 77 / 71 | 73 | 28 | 38.36% |
| Financials: XLF -> KRE | 69 / 57 / 120 | 33 | 9 | 27.27% |
| Industrials: XLI -> ITA | 74 / 80 / 92 | 39 | 11 | 28.21% |
| Healthcare: XLV -> XBI | 87 / 68 / 91 | 38 | 20 | 52.63% |
| Software: XLK -> IGV | 86 / 87 / 73 | 47 | 19 | 40.43% |

Gold specifically: **GLD strength alone** preceded 114 eligible hypothetical GDX purchases, of which only **45/114 (39.47%)** cleared 30bp modeled costs. Requiring **both GLD and GDX** first-hour strength reduced the sample to 88 but lowered rather than improved modeled win precision to **30/88 (34.09%)**. Requiring peer miners GDXJ, NEM, AEM and KGC to confirm did not further change these 88 trades under this predeclared 0.25% peer threshold. A prior-five-session positive GDX trend reduced gold/miner entries to 40, with 30% winning overall and only **one** later-period candidate, which lost money in the price-mark scenario. **This result is negative evidence for blindly buying miners after a morning rise in GLD, not proof that gold and miners are uncorrelated.**

The Sept–Nov locked later subset for gold GLD+GDX had **14 trades / 35.71% winning / -0.1472% mean** after modeled 30bp costs. Energy's comparable later group had 12 trades / 50.0% / -0.5029%; no sector approaches a credible 80% profitable-hit objective. Even in healthcare, the later 60% result has just five independent eligible dates.

### 3. Implications and unresolved data

* **WATCH vs emergency actionable alert:** do not automatically promote 2%, 2.5% or 3% declines to SELL, and do not auto-buy rising sector ETFs based on anchor momentum alone. A 2% internal check may identify serious risk earlier but currently expands false-warning volume; choose more selective confirmations only after actual OOS and execution evidence, *without masking safety-critical alerts*.
* **Gold miners:** gold-ETF correlation is not demonstrated price leadership at a profitable lag. Prior to any PAPER orders, obtain 52-week Alpaca SIP **5m/1m and eligible BOATS quotes** for GLD, GDX, GDXJ, miners, plus timestamped spot/CME gold, USD, Treasury yields and company news/earnings. Test 5/15/30/60m and overnight lags, spread/size, opportunity costs, fills, partials, exits, and survivorship constraints; gold volatility and miners volatility differ.
* **Other sectors:** independent ETF label counts are reported above; instruments and cutoffs in this exploratory test were chosen before seeing the later subset. Wider candidate grids must train **strictly earlier** and lock policies for new holdouts; the present data does NOT validate sector PAPER auto-orders.
* **Entry quality:** 80% recall of large directional moves does not mean an 80% profitable execution rate. Preventing more than 50% harmful alerts while still trading frequently is the actual challenge. The two studies justify *reducing notification noise*, not disabling protection.
* **Missing:** complete timestamp-synchronized Alpaca SIP/BOATS NBBO and broker fills, 52-week independent sector 5m data, actual spot/futures/news/economic calendar timestamps, true bid/ask spreads, V1 matched order/position attribution, and statistically sufficient independent prospective PAPER trade outcomes. Current November 9 session is **incomplete**, and must not be used to report completed-day profits.

### 4. Code, provenance, validation

New isolated files on `research/rebound-v2-conditional-exits`:
* `research/v2_semi_emergency_precision.py`; `research/test_v2_semi_emergency_precision.py`; static cohort `research/results/v2_semis_research_cohort_2026-11-09.json`; full structured sweep `research/results/v2_semi_emergency_precision_2026-11-09.json`.
* `research/v2_sector_hourly_precision.py`; `research/test_v2_sector_hourly_precision.py`; full summary `research/results/v2_sector_hourly_precision_2026-11-09.json`.

**Eight new offline tests passed** on an isolated www3 scratch directory `/tmp/v2-run15-sector-precision-work`, including overlap-not-additive, missing 15-minute bar, fail-closed peer confirmation, strictly previous-day feature, future-close invariance, and profit-cost tests. Pre-existing divergence `/tmp/v2-trading-strategy-research` and dirty production `/opt/securityprepper/multi-broker-bridge` were not touched. Existing V1 PAPER/LIVE monitors, timers, broker orders, and holiday scheduling remain unchanged. No new automatic PAPER trading was enabled.
