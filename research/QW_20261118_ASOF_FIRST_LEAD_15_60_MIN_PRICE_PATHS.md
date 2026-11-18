# November 18, 2026 — live as-of Quality Watch early-leader field study (READ-ONLY)

**Run:** Wednesday, Nov 18, 2026, ~13:40 CT. America/Chicago root-owned holiday gate rev2 checked fresh, complete, and **unpaused** immediately before market-data access. No broker/order/stop/Pushover/session/service/timer/production code changed. No recommendation or buy authorization.

## Method and provenance

- Source: the *previously saved as-of* `/var/lib/securityprepper-quality-watch/state.sqlite3` scans, Nov 18 between **14:30 and 18:00 UTC**. Per feed, retain the **first observable scan** for each symbol; require the stored signal-bar timestamp be no more than four minutes before the scan and never after the scan. This is **first observation of a PRICE preflight event**, not authenticated first observation of a news article. Neither the source event time nor the later data GET can be substituted for the immutable issuer first-seen ledger.
- Three independent lead lists, with **overlapping symbols**, were compared: expanded preflight (188 unique names); broad S&P500 (72); basic news-preflight price leads (236). **288 unique equities across all three**, not 496 independent trades; 24 symbols appear in all three.
- Read-only historical Alpaca **SIP completed 1-minute OHLCV**, `/v2/stocks/bars`, split adjusted and paginated, from the original session; **289 covered symbols including SPY; zero failed data batches**.
- After the actual saved scan timestamp, the entry-price proxy is the NEXT minute's SIP bar **OPEN**, NOT a guaranteed broker-executable ask. The 15- or 60-minute outcome is the last completed bar CLOSE inside that horizon. Minimum actual price-bar coverage of horizon minus two minutes is required; unavailable observations are explicitly omitted, not counted as losses or wins.
- A hypothetical round-trip **0.20 percentage-point friction sensitivity** is shown only as a stress proxy; **not observed commission/spread/slippage**. Historical quotes, account/order readback at the signal timestamp, news clearance, and broker fills are unavailable for these leads; no executable after-fee P/L is established.

## Field-study outcomes: strictly AFTER signal (one market session)

| Source type | 15m eligible/up | Mean 15m close-only | 60m eligible/up | Mean 60m close-only | Mean 60m minus illustrative 0.20%-pt friction | Mean 60m price excess vs contemporaneous SPY |
|---|---:|---:|---:|---:|---:|---:|
| Expanded early individual/peer price preflight | 187 / 71 | -0.1703% | 173 / 74 | -0.1045% | -0.3045% | +0.1221 pp |
| Broad S&P500 price lead | 71 / 34 | -0.0159% | 66 / 36 | +0.0590% | -0.1410% | +0.2750 pp |
| Basic rising-price/news preflight | 229 / 107 | +0.0464% | 209 / 89 | -0.0619% | -0.2619% | +0.2113 pp |

Up/total 60m: expanded **42.8%**, broad **54.5%**, basic **42.6%**. Basic 15m up/total 107/229 (46.7%). The broad 60m direction Wilson interval **42.6%–66.0%** ignores severe same-session and common-stock dependence, so must not be called validated forward accuracy. All these price-mean results are from a **single fresh prospective day** with only 0.20%-pt illustrative friction and with **zero independent NEWS_CLEAR_ASOF**. SPY-relative direction on a falling market does not cure missing executable after-cost absolute P/L.

## Named-leader hindsight audit — discovery is not qualification

As of the contemporaneous S&P500 daily monitor, **OKTA** was approximately +11.3% from its prior RTH close later that day. Its earliest recorded basic price preflight at **14:49:57 UTC** preceded the modeled 60-minute +4.07% close-to-close path, with next-minute open already **+0.93%** from prior RTH close. But this singled-out winner is selected **after knowing later gainers**, and **issuer news, original observation, spread and trade eligibility remain unverified**; no BUY or PAPER order can be justified. **TJX**'s early basic preflight was already **+6.72%** from the previous close by the next-minute open proxy; **TTWO**'s first broad lead was already **+7.08%**. These are strong warnings against treating prominent daily-risers pages as early-entry evidence.

## Interpretation and future design

**No robust, positive, executable after-fee forward edge or release authorization.** The one-day demonstration confirms the expanded and broad lead recorders produce as-of evidence, but neither price-only selection generalizes well enough to pass owner admission tests. Zero qualified contemporaneous issuer negative-news clearances were demonstrated; no paper trading was performed. Do not compare these proxies to Recommendation Audit native fill profits or historical pre-earnings reports.

Continue without parameter tuning on **20–30 genuinely untouched forward sessions**, with immutable original source-receipt provenance, verified issuer/SEC negative-news clearance, the last five completed minute-direction bars, independently validated broker ASK/BID/spread and *real* trades for entry/exit attribution. Preserve strict 13:15 CT last-entry / 13:40 hard-flat, same-bar stop-first, broker ownership/idempotency and holiday constraints. Do not introduce executable V1/V2 changes or Pushover from this exploratory field study.

### Artifacts (on the same isolated research branch)

- `research/qw_20261118_1334_asof_forward_1min_sip.py`: exact read-only field-study code (holiday-gated and Alpaca DATA GET-only; no broker API POST).
- `research/qw_20261118_1334_first_candidates_forward_15_60.csv`: **496 feed-specific first-observed event rows**, 15/60-minute price-only paths, missing coverage, and SPY excess; rows overlap across sources and must not be counted as independent trades.
- Host-private detailed JSON: `/tmp/trading_strategy_research_20261118T1334/quality_watch_early_leads_20261118_asof.json`, SHA-256 `27f5f213de6ab1d1f6b7e04b7e4cc5090bb874c3f05f01b693ca0194f7bdb881`, may be ephemeral.
