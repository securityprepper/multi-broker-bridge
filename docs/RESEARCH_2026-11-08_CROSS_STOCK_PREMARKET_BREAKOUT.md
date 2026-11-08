# 52-week semiconductor breakout continuation — additional tests November 8, 2026

**RESEARCH / PROPOSED PAPER OBSERVATION ONLY. No automatic-trading rules or orders were changed. No strategy is validated to earn profits consistently.**

## Source and test split

- Authenticated Alpaca split-adjusted SIP five-minute historical bars for AMD, MU, SNDK, SOXX covering November 2025–November 2026 (~189,000 bars total); five additional semiconductor symbols NVDA, AVGO, WDC, TSM, INTC (~237,000 five-minute bars). These bars do not cover overnight BOATS 8 PM–4 AM ET; actual broker quotes/orders not available. SOXX split-adjusted.
- Model holds no more than $2,000 per symbol *per order*, not portfolio-wide; all entry and exit fills are OHLC-derived hypotheticals with a per-side allowance. Pre-market exits are not guaranteed.
- Parameter search: 384 variations of the previous 52-week setup: strict/broad breadth, 15/30-minute lookback, +0.3% or +0.7% momentum, +0.5% or +1.5% price vs prior close, instant/pullback/breakout/volume confirmation, proposed morning limits 8:30–9:25 AM ET. Ranked on training through 2026-08-31; later checks 2026-09-01 through 2026-11-06. **The date November 6 and some prior results were examined before this research, so this is not independent untouched holdout.**
- Corrected chronological simulation: buy at next five-minute bar after completed signal; entry must precede morning exit by at least ten minutes. Seven invalid same-bar 8:30 entries/exits were excluded from the early candidate; the first uncorrected result of +$1,289.53 training was revised to **+$1,325.46**. See `/tmp/semis_year_intraday_chronological.py` on www3. The later P/L of +$469.90 was unchanged.

## Best comparatively robust candidate, not universally profitable

At least two of three AMD, MU, SNDK >+1.5% relative to prior close, SOXX >+0.75%, two leaders +0.7% over preceding 15 minutes, SOXX nonnegative momentum, and two leaders showing a recent five-minute **close above the preceding bar's high**. Entry uses next five-minute bar's low reaching a limit 0.15% above completed signal close; exit places a hypothesized premarket SELL limit at 8:30 AM ET based on the 8:25 5-minute close less 0.15%. If the limit was not reached, reference simulator has a regular-open exit fallback, not guaranteed execution. Entry allowed in SIP 4–8 PM ET or 4–8:20 AM ET, not 8 PM–4 AM where the SIP feed has no observations.

Original four symbols (AMD, MU, SNDK, SOXX):
- Train <=Aug31: 125 hypothetical fills, **+$1,325.46** (chronology corrected).
- Later Sept–Nov6: 16 hypothetical fills, **+$469.90**, including Nov6 **+$318.74**. Later excluding Nov6 **+$151.16**.
- Across 38 active sessions: **25 winning and 13 losing days** at 0.15% allowance; **February −$268.07**; worst single day −$343.34. No September trades.
- Captured positive simulated exits on Oct21 +$64.80, Oct27 +$9.96, Nov3 +$76.40, Nov6 +$318.74. Missed Oct19, Oct26, Oct28.
- Execution allowance 0.30% per side: approximate training +$601.72 before chronology correction (corrected amount needs separate validation); later +$389.18, excluding Nov6 +$90.64. At 0.50%, training turns negative. **Do not treat the 0.30% training number as chronology-corrected.**

## Same rule applied WITHOUT retuning to 5 additional semiconductor stocks

NVDA, AVGO, WDC, TSM, INTC 52-week five-minute SIP split-adjusted bars. Entry at the SAME sector signal timestamp as the original four, identical limits/sizing and 8:30 AM ET exit behavior (if sell not reached, conservative 9:30 open reference). This was an out-of-selection-stock test; correlated sector exposure means it is not independent future performance.

| Per-side execution allowance | Train P/L | Later P/L | Later ex-Nov6 | Trades |
|---|---:|---:|---:|---:|
| 0.05% | +$1,597.19 | +$522.08 | +$180.85 | 166 |
| 0.15% | **+$1,204.85** | **+$532.06** | **+$125.70** | 173 |
| 0.30% | +$418.55 | +$421.61 | +$43.77 | 175 |
| 0.50% | **−$722.69** | +$270.80 | **−$66.94** | 175 |

At 0.15%: 36 active sector-signal days across the year; 25 winning and 11 losing peer portfolios; by symbol annual sums NVDA +$149.89, AVGO +$277.45, WDC +$477.28, TSM +$261.21, INTC +$571.08. One single peer-sector day (Feb 5) lost −$415.32. There were only four later active days (Oct21, Oct27, Nov3, Nov6), hence very limited later evidence.

## Overnight/premarket loss guard sensitivity

A historical 5-minute OHLC-based synthetic premarket stop for positions at threshold 2%, 3%, 4%, 5%, 7.5% below entry, applied starting the *next* 5-min bar, conservatively assumed fills at min(bar open, stop level) less the 0.15% buffer. It ignores BOATS 8 PM–4 AM and is NOT a broker-confirmed stop. At the 0.15% buffer:

| Model loss trigger | 4 original train | 5 peers train |
|---|---:|---:|
| No extra stop | +$1,325.46 | +$1,204.85 |
| 2% | +$410.74 | +$269.00 |
| 3% | +$424.51 | +$619.89 |
| 4% | +$798.55 | +$696.17 |
| 5% | +$917.30 | +$972.23 |
| 7.5% | +$1,309.89 | +$1,040.16 |

These exits cut some downturns but also destroy profits from later recoveries. A model trade in SNDK experienced an observed **−8.65% intraposition price excursion** before the morning exit, MU −7.44%; among original 148 trades 7 had >5% observed adverse excursion. This is a serious *capital risk* and cannot be ignored because the backtest later shows a profit.

## Why this does not establish a reliably working strategy

- Results are strongly sensitive to execution buffer (and assumptions about five-minute OHLC touch and queue priority). No actual executable bid/ask tape or paper fill IDs were measured.
- At best the strict regime catches only some positive sessions; it's not possible to guarantee a buy or profitable exit on every up day. Multi-day uptrend trades on Oct26/Oct28 were missed; Oct27 only modestly profitable.
- Selecting 8:30 AM ET and breakout threshold after reviewing Friday and other dates contaminates the later test. Other symbols have correlated returns. Sept–Nov had only four trading days under the candidate.
- Data includes after-hours but excludes overnight BOATS in annual study, and market quality varies substantially. Broker-native trailing stops usually do not operate in extended hours; stop-limit orders can fail to fill.
- Never activate live strategy or more automatic PAPER buys from these research figures alone. **Proposed next measurement:** forward PAPER shadow signals, executable 1-minute bid/ask, broker-confirmed buy/cancel/sell fill and missed-limit records; include maximum adverse excursion and stale-feed safeguards. Compare at least 20-30 independent signal events including weak days.

**Outcome:** A candidate is more repeatable in historical *simulations* than previous rules, and transfers across five withheld semiconductor symbols, but it's **not yet validated for reliable profitable execution**.
