# November 13, 2026 — Distinct, non-price-only stock-market opportunity research

**Status: RESEARCH ONLY / NO NEW PAPER GO.** The goal is to find mechanisms independent of retired loss-making price-only momentum/chase, five-day rebound, GLD/miner lag, generic earnings/upgrade opening gap, routine reentry, or synthetic-trailing ideas. All work ran after validation of the authorized Chicago holiday rev2 cache as unpaused strictly before 2026-11-13 16:13 CST. No new broker orders, active V1/PAPER/LIVE execution rules, timers, alerts, or account states were changed.

## 1. Scheduled macroeconomic surprises: measured opportunity budget, not a prediction

Hypothesis: **actual official numbers relative to pre-release, independently time-stamped consensus expectations**, together with independently observed Fed funds/rates surprise, might predict further ETF movement. This differs fundamentally from chasing previous-close or intraday sector momentum. **Neither immutable consensus vintages nor original first-observed actual surprise data are available in these backtest inputs; a directional strategy has NOT been tested or cleared.**

Reproducible new pure-read-only research:
- `research/v2_macro_event_opportunity_budget_20261113.py`
- `tests/test_v2_macro_event_opportunity_budget_20261113.py` — **11 synthetic integrity tests passed** on authorized www3, including DST, completed-bar event clocks, missing bars, calendar/control separation, no broker calls and no future outcome used as a signal.
- `research/results/v2_macro_event_opportunity_budget_20261113.json` — sanitized aggregate ETF/event/control results, **no licensed raw historical bars, broker IDs, keys, orders or account data**.

Source: already retained split-adjusted historical Alpaca SIP 5-minute trade bars for SOXX, GDX, XLE, XLF, IGV, approximately Nov 3 2025–Nov 6 2026. Official calendar **CPI and Employment Situation released at 08:30 ET**, FOMC policy statement at **14:00 ET**. For CPI/jobs, future movement measured from the **completed 09:30–09:35 ET bar available at 09:35**, to the completed **14:35–14:40 ET bar** (the hard 13:40 Chicago flatten). For FOMC, from the completed **14:00–14:05 ET bar** to 14:40 ET. Thus none of the price movement before each observation is credited as a predictive success. A 5-minute trade close is **not** a broker-executable quote.

### Highest observed *absolute* future movement opportunities

| ETF / event and observation window ET | Event days | Absolute future move >0.30% | Non-event control, same window | Mean event absolute future move | Mean ordinary absolute future move |
|---|---:|---:|---:|---:|---:|
| SOXX / FOMC, 14:05–14:40 | 8 | **6/8** | 72/223 | **0.597%** | 0.257% |
| GDX / FOMC, 14:05–14:40 | 8 | **6/8** | 78/224 | **0.534%** | 0.280% |
| IGV / FOMC, 14:05–14:40 | 8 | **6/8** | 59/223 | **0.388%** | 0.235% |
| SOXX / employment, 09:35–14:40 | 11 | 10/11 | 188/223 | **1.794%** | 1.406% |
| IGV / CPI, 09:35–14:40 | 11 | 10/11 | 188/223 | **1.463%** | 1.148% |
| XLF / FOMC, 14:05–14:40 | 8 | only **1/8** | 16/223 | 0.168% | 0.111% |

These numbers are **absolute realized movement in either direction**: perfect hindsight sign selection would be required to capture them. For example, SOXX rose 6/8 and fell 2/8 after the 14:05 FOMC observation, but this does **not** imply a reliable forward BUY signal. The FOMC Chair press conference starts 14:30 ET and the hard flat arrives 14:40, creating significant intra-window reversal and timing risk. A future release surprise must be **independent of price movement**, timestamped as originally received, with genuine contemporary consensus and current market bid/ask depth. **No after-cost executable profitability or trade precision was proved.**

Coverage: 11/12 CPI scheduled dates before the bars' last available 2026-11-06 session (2026-11-10 lies after the historic data end); 11/12 employment dates with market bars (the 2026-04-03 release occurred on **Good Friday, NYSE closed**, thus no RTH test); eight of eight FOMC statement days. Non-event controls exclude all three event types and use the same forecast horizon. This is exploratory archive material, **not untouched blind validation**.

### Exact blockers / next valid experiment

- **PRE-RELEASE consensus vintage** for CPI core/headline, payrolls/unemployment/wages, and monetary-policy rate expectations, including original observed timestamp and revision evidence. A retrospective actual minus later-revised forecast would be lookahead. Without it, status `MACRO_SURPRISE_UNKNOWN`, NO SIGNAL/ORDER.
- First-observed and publication clock for official release plus durable original contents/hash; no inference from market move to invented "surprise".
- Executable Alpaca SIP/BOATS NBBO and intended-order latency at each eligibility timestamp, spread, size, partial fills, price extension, mandatory 13:15 latest entry and 13:40 flatten, protective stop; inverse ETF/short eligibility if directional down. Only the RECEIVING BROKER'S own fresh risk state may gate it.
- New **precommitted** event/surprise-to-direction policy with no data leakage, measured **forward from the actual signal** over at least 20 independent announcement sessions, separated by CPI/jobs/FOMC and sector. Assess after-fee hit precision, missed large moves, true/false alerts, drawdown, loss tails, and no-trade baseline; do not invent reliable 80% accuracy.
- The 14:40 ET hard flat allows only 35 minutes after 14:05 ET FOMC observation; these approximately eight annual FOMC events cannot independently generate daily $100 profits.

Official source calendar references:
https://www.bls.gov/schedule/news_release/cpi.htm
https://www.bls.gov/schedule/news_release/empsit.htm
https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
https://www.federalreserve.gov/newsevents/pressreleases/monetary20240809a.htm
https://www.nyse.com/trade/hours-calendars
External event-volume evidence: https://www.cmegroup.com/insights/economic-research/2025/how-fx-equities-trade-economic-data-sets.html

## 2. Genuine economic customer–supplier information transfer

Research the **first public issuer release of a quantified, material customer demand/guidance change** transmitted to suppliers with independently documented preceding revenue dependence, rather than co-moving sector peer prices. Ground relationship/CIK and material sales concentration in an original pre-event SEC 10-K/10-Q. Corroborate original first-seen 8-K/company filing and a reliable news source, current independent negative-news veto for the supplier, tradable NBBO, and nonextended ask. Compare linked suppliers with unrelated or sector-matched controls, 13:40 flat and realistic fills. Contrary literature exists: older work suggests supplier underreaction, while newer work questions the general financial-reporting information-spillover story; this cannot be treated as proven edge. See:
https://www.sciencedirect.com/science/article/pii/S1062976914000167
https://onlinelibrary.wiley.com/doi/pdf/10.1111/1475-679X.12562

**Blocker:** the existing 3-year news archive's 3,141 articles lack original first-observed times, durable original issuer guidance versions, and verified as-of supply-chain links. Thus neither hindsight event study nor automated trade is justified yet. Prospective original receipt and relationship attestation, then >20 untouched sessions, is required. Stock-specific negative guidance matters in any case as a **BUY exclusion**, even without a predictive long.

## 3. Other ways to earn returns with a different time horizon, separately authorized

A **low-turnover, broad diversified index-fund core** avoids depending on intraday alpha from the same tiny edge being consumed by spreads and early exits. In S&P SPIVA's mid-year 2026 report about **90.49%** of active U.S. large-cap funds underperformed the S&P 500 over 15 years; this is not a promise of future gains or a reason to switch unilaterally from cash or change any broker account. Source: https://www.spglobal.com/spdji/en/research-insights/spiva/.

Holding interest-bearing short-duration Treasury instruments for a cash allocation can produce yield rather than speculative trading returns but has interest-rate/liquidity risk and cannot guarantee daily profit. Any long-term account allocation or trade requires **separate explicit authorization**; do not confuse the intraday owner's "all triggered positions flat by 13:40 CT" protection with authority to buy and hold elsewhere.

**Decision:** Research priority is genuine macro **SURPRISE** events, then customer–supplier quantified first-seen information, then optional separately authorized long-term diversified core. Do not place a signal or PAPER order on calendar/time/absolute realized movement alone. Do not resume retired losing strategies. No new after-cost profitable automated strategy was found in this run.
