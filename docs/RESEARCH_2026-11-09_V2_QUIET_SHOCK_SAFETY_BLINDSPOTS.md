# V2 research — Quiet sector shock thresholds must not replace position-risk alerts
**2026-11-09 America/Chicago | RESEARCH ONLY. No V1/PAPER/LIVE deployment or broker actions.**

## Critical finding
The owner's **high-precision, low-noise sector screens** deliberately catch far fewer extreme equity moves, but they are **unsuitable as a substitute for an existing held-stock downside monitor**. This distinction is important because an individual position can lose 5–10% even when its sector ETF is nowhere near the new 3–7% cutoff. Conversely, a 2.5%-total stock warning including a further 1 percentage-point drop in the preceding 15 minutes can detect many large falls, but misses gap-downs and slow declines.

Across **248 completed, strictly prior-five-eligible historical sessions per sector** and **16 sector constituent stocks** (3,968 stock-days), from split-adjusted **Alpaca SIP five-minute TRADE bars through November 6, 2026**, independently audit *both major winners and losers* on each day. A **major move** is either previous-regular-close→current-close or current-regular-open→current-close **at least ±5%**. The two-sided cohort contains **142 major-down** and **173 major-up** stock-days, not necessarily distinct trading dates. These are correlated same-session stock-day observations, not 3,968 independent experiments.

## Full-history true-major-move overlap (not forward prediction)

| Own-sector group | Major DOWN stock-days | New quiet sector DOWN screen | Old looser sector DOWN screen | Separate strict stock-risk trigger | Major UP stock-days | New quiet sector UP screen |
|---|---:|---:|---:|---:|---:|---:|
| SOXX: AMD/MU/NVDA | **66** | **19** | **53** | **58** | **92** | **4** |
| GDX: NEM/AEM/KGC | 46 | 12 | 35 | 37 | 50 | 2 |
| XLE: XOM/CVX | 2 | 0 | 0 | 1 | 1 | 0 |
| XLF: JPM/BAC | 3 | 2 | 2 | 2 | 0 | 0 |
| XLI: CAT/GE | 12 | 1 | 1 | 8 | 12 | 0 |
| XLV: UNH/LLY | 5 | 0 | 0 | 3 | 7 | 0 |
| IGV: MSFT/CRM | 8 | 2 | 7 | 7 | 11 | 3 |
| **Totals** | **142** | **36 (25.4%)** | **98 (69.0%)** | **116 (81.7%)** | **173** | **9 (5.2%)** |

The **new** sector day screen is SOXX ±5%, GDX ±5%, XLE ±3%, XLF ±3%, XLI ±3%, XLV ±3%, IGV ±4%, all from **09:30 ET regular open**. The **older comparison** is SOXX/GDX ±2%, other sectors ±3%. Both require **two consecutive completed sector ETF five-minute closes** beyond threshold, current completed bar's own-sector breadth ≥2/3 (or both of 2 peers), each peer at least one-quarter of the ETF percentage cutoff in the same direction vs the same day's opening price. First qualified report per direction/session is counted per stock-day if a corresponding severe outcome occurs. Intrabar high/low is never an alert. Night thresholds (SOXX 5.5%, GDX 7%, XLE 3.5% etc.) were **not** evaluated here and historical overnight BOATS coverage is incomplete.

Of **36** severe-down stock-days accompanied by the **new** sector alert, only **12** sector alerts occurred while the stock was still *above* −5% from the preceding close; **24** were already at least −5% when the sector alert qualified. For semis, only **4 of 19** arrived before the individual stock reached −5%; for miners **4 of 12**. A very rare signal should be described as a **factual sector shock**, not early protective sell advice or a prediction of a further profitable move.

## Preserve the independent strict stock warning — but investigate its blind spots
The existing policy is **stock total decline ≥2.5% from previous regular close AND further decline ≥1.0 percentage point in the last 15 minutes**, measured relative to that previous close. The second decline is **INCLUDED** in the first; it is NOT an additional 2.5+1=3.5% requirement. In this five-minute RTH approximation, it matched **116/142 major-down stock-days**, while triggering on 304 other stock-days that did not satisfy the **major closing-day −5% label**. Those 304 are **not necessarily erroneous factual warnings**: many are real sharp drops followed by rebounding, and being a poor automatic trading signal does not nullify position risk.

The **26 major-down stock-days missed by this strict conjunctive stock rule** break down as:
* **7 opening gaps already ≤−5%** from previous close, without later qualifying 15-minute acceleration.
* **16** with a total ≥2.5% decline at some time but no qualifying ≥1pp additional 15-minute momentum.
* **3** with a ≥5% open-to-close fall but no total −2.5% decline from previous close (e.g., after opening sharply higher).
These categories are assigned in that priority and together account for all 26 misses.

**Example:** AMD on **October 30, 2026** opened approximately **−10.14%** below its previous regular close, ended **−10.82%**, and still did **not** generate the strictly conjoined daytime 2.5%+1pp/15m alert in this completed five-minute test; a steep opening gap followed by a smaller additional drift bypasses the momentum gate. On **November 2, 2026**, MU ended **−5.84%** prior-close and **−6.45%** from regular open and was also missed by strict daytime momentum condition in this 5-minute replay. These are historical risk observations, **not new alerts**.

**Research candidate, not deployed:** An optional separate **held-position factual opening-gap ≥5% warning** can complement the existing conjunctive stock warning, with quote/data freshness, holiday/session guard, position readback, one alert per holding/session and no implied SELL order. Do **not** loosen automatic sell/stop permissions on this evidence; opening gap cannot be retroactively avoided by an after-open alert.

## Does even the strict stock signal predict the *next hour*?
For **420** first strict downside stock warnings across the 52-week sample, only **412** had an exactly aligned completed 60-minute future price mark; missing horizons remain unscored. On the chronological later ~30% **95** were scorable; only **39/95 (41.1%)** subsequently fell by **more than 0.30%** over the next hour. By sector in the later sample: SOXX peers **20/41**, gold miners **7/20**, energy **0/0**, financials **2/3**, industrials **9/15**, healthcare **1/6**, software **0/10**. These are gross mark-to-mark **avoided-decline proxies**, not historical executable SELL fills or an estimate of actual protective stop benefit. Costs are an illustrative 0.30 percentage-point hurdle only; prior period and later periods were already repeatedly studied, so no untouched holdout exists. Do not enable automatic liquidation solely from this low-precision prospective statistic.

## Controls / next work
- The report explicitly separates a **descriptive, observed shock** (a factual threshold cross) from **post-signal predictive performance**, measured against the signal's completed close, NEVER from yesterday's close or any move already seen.
- Historical gold, semiconductors and the five other sectors use their independently sourced Alpaca split-adjusted SIP bars, without incorporating Nov 9 outcomes. Only complete regular sessions with **five earlier complete regular sessions for each ETF/peer** were included. This qualification uses prior-day completeness, not later intraday prices.
- No full synchronized NBBO/BOATS, broker-order fills, fee schedules, or untouched live 20-day prospective test is available here. Early-day and overnight warnings require their own causal data and separate execution eligibility. Nonmajor stock-day warnings are not automatically “false” warnings.
- New research scripts: `research/v2_sector_alert_severe_stock_recall_20261109.py` and `research/v2_stock_weakness_future_60m_20261109.py`. Repeat from the authorized host's research inputs; daily audit of all 3,968 stock-days and triggered 420 events saved privately under `/tmp/` and **aggregate results/missed-case summaries** published in `research/results/v2_sector_shock_safety_severe_stock_summary_20261109.json`.
- **13 offline no-order/no-lookahead/60m-outcome tests passed** (including a finding/fix for source-cache ID reuse and no hypothetical exit at exactly the 13:40 CT flat).
- The live low-noise V2 threshold configuration and all seven task prompts were **left unchanged**. V1 PAPER/LIVE, Alpaca/IBKR broker orders, existing monitors, IBKR gateway and timers **untouched**. No automatic buys/sells, new Pushover publisher or PAPER GO. Existing factual position/order/stop/data-integrity safety warnings must remain available even when low-noise predictive alerts are suppressed.
