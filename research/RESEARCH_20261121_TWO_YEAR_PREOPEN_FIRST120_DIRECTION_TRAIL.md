# Two years of tracked-stock early-session direction and trailing-stop research
**Frozen research date:** November 21, 2026. **Price sample:** November 20, 2024 through November 20, 2026. **Time zone:** America/Chicago. **READ-ONLY. No broker orders, no V1 changes, no deployment.**

## Main answer: NO new buy/short order or new trailing-stop setting is justified

The two-year archive contains 275 configured tracked/related symbols across 15 sector groups and priority semiconductor, storage, cybersecurity and AI names, with 502 NYSE market days. **126,352 symbol-days** have sufficient one-minute regular-session data to receive a day label. Market data were independently collected from Alpaca historical SIP regular/premarket and BOATS overnight feeds, split-adjusted. Newly retrieved premarket/overnight/missing-stock records: **16,464,645** minute bars, 876 read-only download jobs, no download failures. Missing daily history and absent near-midnight prints are NOT assumed flat or successful.

**Primary day definition (fixed before strategy selection):** UP = open→regular close ≥+0.75% AND close in top 30% of the trading day's range; DOWN = ≤−0.75% AND close in bottom 30%; otherwise MIXED. Exchange early closing at 12:00 p.m. Chicago time was handled from the broker calendar (five historical shortened days). The normal close is 3:00 p.m. Chicago. A **separate** prior-close→current-close classification captures overnight gap effects, without conflating a price increase before the open with an increase that was tradable after a signal.

| Day characterization | Symbol-days | Share |
|---|---:|---:|
| Sustained UP | 29,612 | 23.44% |
| Sustained DOWN | 27,957 | 22.13% |
| MIXED | 68,783 | 54.43% |
| **Total** | **126,352** | **100%** |

On the separate previous-close basis, of 123,728 events with a verified prior regular close, **42,668** finished ≥+0.75%, **39,036** finished ≤−0.75%, and **42,024** ended within ±0.75%. This is a different descriptive label from the intraday-trend-quality label above.

## Every minute before and after the opening bell

**Premarket:** Evaluated actual completed 1-minute prices at every minute from 12:00 a.m. to 8:30 a.m. CT (510 pre-open minute boundaries), comparing the stock, SPY and an assigned sector ETF to previous *split-adjusted* regular closes; a separate rule compares actual, time-stamped near-midnight prints. A price bar is eligible only after completion and within a two-minute freshness bound, with no synthetic fill across gaps. Of **105,658** qualifying premarket symbol-days, only **26,648** have an actual stock trade close within ten minutes of midnight, and just **9,554** have near-midnight reference prints for the stock, SPY and sector ETF. The per-symbol best minute was selected using TRAIN only, then tested on later dates. **0** per-symbol premarket minute/side models qualified simultaneously across train, validation and holdout under even an optimistic simple cost proxy.

**First 120 market minutes:** Examined completed one-minute paths from 8:30–10:30 a.m. CT for each symbol against SPY, its sector ETF and contemporaneous, self-excluded sector peer breadth. Tested the sign of stock/market/sector momentum; 5/15/30/60-minute alignment; ≥80% peer breadth; verified opening-ten-minute-range breakout; opposite-gap rebound; late overnight plus opening confirmation; and the owner-proposed SPY/sector both ≥1% and ≥75% peer agreement. Capped hypothetical entry extension at ±6% from the previous close and excluded price observations below $5. **234,929 earliest-per-rule/side/day historical signal instances** were found across **256** symbols (113,082 train, 60,110 validation, 61,737 untouched holdout). The simple per-symbol training-selected minute from the stock/ETF/SPY/peer model had **0** independent train/validation/holdout successes. This does not assert that every possible strategy is unprofitable.

**Classification versus forward return:** In the untouched holdout, the baseline UP/DOWN intraday labels occurred 22.63% / 25.29% of observed days. After 30-minute qualifying bullish alignment, 1,187/2,764 (42.9%) eventually met the UP-day label; after 30-minute bearish alignment, 1,047/2,291 (45.7%) met DOWN. At two hours those matched labels were 50.8% bullish / 51.9% bearish. **But remaining price movement from the *signal minute* to the mandated 13:40 CT flat was negative on average after a fixed 0.25% roundtrip cost allowance:** approximately −0.23% bullish and −0.28% bearish at minute 30; −0.26% and −0.20% at minute 120. The day label includes the earlier movement, so its apparent accuracy is NOT proof of a profitable future signal.

## Trailing-stop sensitivity, actual matched comparison

Used next completed minute's bar OPEN as a **hypothetical entry proxy**, conservative prior-stop-first minute OHLC exit, adverse opening gap at the worse price, update trail only after each bar, no bar-gap fill fabrication, and mandatory flat at 13:40 CT (11:40 CT on scheduled early-close dates). Short scenarios are **research only** and do not verify borrowability or fees. Assumed a **0.10% execution-cost proxy on each side** (roughly 0.20% roundtrip), which is NOT an independently verified historical spread, broker fill, after-fee result, or real stop execution.

Six candidate trailing stops: **0.5%, 0.75%, 1.0%, 1.5%, 2.0%, 2.5%**. The raw replay produced **1,055,129** scenario results; **354,445** candidate-stop attempts were excluded due to invalid entry or incomplete bar paths. Because different stop widths can terminate at different times, comparisons on unmatched observations are biased. We therefore retained only **148,743 identical fully observed event paths**, each tested at all six stops (892,458 comparable scenarios), excluding 60,426 event paths without the entire six-width cohort. In the common final holdout set, each row on the same side compares *exactly the same events*:

| Stop | LONG n=20,153, mean net proxy | SHORT-only hypothetical n=21,911, mean net proxy |
|---:|---:|---:|
| 0.50% | −0.1815% | −0.1765% |
| 0.75% | −0.1814% | −0.1624% |
| 1.00% | −0.1996% | −0.1480% |
| 1.50% | −0.2049% | −0.1282% |
| 2.00% | −0.2237% | −0.1343% |
| 2.50% | −0.2767% | −0.1671% |
| Hold to flat without trail | −0.2817% | −0.2242% |

The marginally *least negative* historical LONG means at 0.50–0.75% are essentially tied and have **very low positive-trade frequency** (about 27–31%); the 1.50% SHORT hypothetical is also negative, and borrow / market-order execution is unverified. Higher trailing percentages produced longer holding times and larger adverse tails. Do not interpret these pooled, correlated simulations as a tradable portfolio or a forecast.

**Training-only per-symbol parameter selection:** 137 symbols had enough matched-path training observations to select a rule, side and trailing stop. **0 of 137** then passed minimum 15 validation events, 20 untouched holdout events, positive net proxies in both later periods, ≥55% positive cases in both periods, and a mean advantage over holding to flat in both. Consequently **no stock-specific order type, direction, or trailing-stop percentage has a validated GO.** The user-facing 249-symbol historical summary CSV labels all such parameters as *TRAIN-SELECTED / RESEARCH ONLY* and includes the actual holdout denominator and result rather than describing them as recommendations.

## Example per-symbol day classification (historical, not trade/watch recommendations)

| Symbol | Eligible days | UP | DOWN | MIXED |
|---|---:|---:|---:|---:|
| AMD | 502 | 143 | 117 | 242 |
| MU | 502 | 141 | 117 | 244 |
| NVDA | 502 | 127 | 126 | 249 |
| WDC | 502 | 126 | 110 | 266 |
| PANW | 502 | 152 | 108 | 242 |
| CRWD | 502 | 148 | 110 | 244 |
| SNDK | 437 | 124 | 105 | 208 |

The full permanent internal daily ledger contains all 126,352 day labels (including source availability) and the 275-symbol aggregate audit; the public derived summary contains only 249 ordinary-stock research rows with a verified Nov 20 regular-session historical price ≥$5, leaving 19 ETF/fund references and seven symbols without a verified Nov 20 RTH price out of the ordinary-stock public table. A Friday closing trade is **historical evidence, not a fresh live actionable quote**.

## Explicit implementation and risk verdict

**New order: NONE** from this research. **Winning trailing stop: NOT ESTABLISHED.** Do not change the existing V1 broker, software stop, daily flat, order routing or alert settings. To commission any future PAPER-only candidate, independently obtain current receiving-broker bid/ask, spreads, order book and buying power; genuine point-in-time issuer-specific yesterday/today news clearance; original issuer identity/fundamental checks; actual fills; market and sector/peer confirmation; and verified after-cost performance on disjoint, prospective sessions. No real broker orders, IBKR changes, Pushover changes or active trading service edits were made here.

**Limitations:** Historical universe primarily uses later/current tracked membership (survivorship bias); venue-specific overnight liquidity is incomplete; the one-minute OHLC path is not a guaranteed executable stop/limit price; model proxy spread is not verified by contemporaneous NBBO or actual fills; short interest/borrow costs are unknown; calendar and issuer point-in-time changes may vary; many correlated symbol-days are not independent evidence. Multiple rule/stop comparisons can overfit; selection uses only the training period, with chronologically separate validation and holdout. No robust, verified after-fee forward edge has been demonstrated.

## Data and reproducibility

- Source dataset, downloads, immutable evidence, per-session day labels and modeled receipts: root-owned isolated /var/lib/securityprepper-two-year-sector-backtest, /var/lib/securityprepper-two-year-early-session-research and /var/lib/securityprepper-two-year-intraday-research on authorized www3; no broker credentials exported.
- Read-only scripts: [seven reproducible research stages](https://github.com/securityprepper/multi-broker-bridge/tree/research/rebound-v2-conditional-exits/research/two_year_early_session_20261121).
- Companion derived [per-symbol summary](PUBLIC_ORDINARY_STOCK_LAST_SESSION_OVER5_HISTORICAL_RESEARCH.csv), [same-event stop grid](MATCHED_STOP_SENSITIVITY_BY_PERIOD_AND_SIDE.csv) and [same-event rule sensitivity](MATCHED_STOP_EACH_RULE_OOS.csv), all no-trading historical research.
