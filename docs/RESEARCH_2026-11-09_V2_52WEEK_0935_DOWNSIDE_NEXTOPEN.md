# V2 research: 09:35 ET severe-down warning and next-open opportunity-cost audit — November 9, 2026

**Research only.** This is a new 52-week, seven-sector follow-up to `docs/RESEARCH_2026-11-09_V2_52WEEK_EARLY_SECTOR_ANTI_CHURN.md`. No PAPER or LIVE broker orders, production monitors, protective exits, timers, or 2pm Chicago latest-flat objective were altered.

## Question

For an as-of-09:35 ET **DOWN** forecast derived solely from the completed 09:30–09:35 ET SIP five-minute candle plus the previous five **completed** RTH closes, was this an early warning for a stock that later closed **at least 5% below the preceding close**? Or was it a false alarm? If someone hypothetically sold at the **09:40 ET next-next-bar open** instead of carrying a long position through the **following REGULAR-session opening price**, would the sale have been economically beneficial after an illustrative 0.30 percentage-point round-trip friction? This latter comparison is *only a counterfactual overnight risk measure*; V1's owner-approved latest flat is 2pm Chicago and must **not** be replaced with overnight holding.

Used split-adjusted 52-week Alpaca SIP five-minute trade bars to November 6, 2026, exact next ETF regular-session date (missing stock opening mark => unavailable, not silently skipping to later dates). Short/bearish signals follow the same sector and peer breadth as the companion seven-sector anti-churn replay. The score uses the **final closing price only as an outcome**, never in the warning. No futures/news lookahead, broker quote/fill simulation, or bid/ask execution evidence.

## Full 248 eligible stock-session days per peer (52-week period)

| Sector | Closing <=−5% stock-days | Detected at 09:35 | Other DOWN warnings (nonmajor) | Major hits already <=−5% at signal | Early sale >30bp better than next open | Mean early-sale advantage vs next open after 30bp |
|---|---:|---:|---:|---:|---:|---:|
| Semiconductors | **106** | **74 (69.8%)** | **148** | **32/74** | **108/222 (48.6%)** | **−0.2076 pp** |
| Gold miners | 43 | 38 (88.4%) | 196 | 17/38 | 96/232 (41.4%) | −0.2937 pp |
| Energy | 1 | 1 | 157 | 0 | 40/156 | −0.6182 pp |
| Financials | 1 | 0 | 96 | 0 | 32/94 | −0.6399 pp |
| Industrials | 12 | 5 | 85 | 0 | 32/90 | −0.6435 pp |
| Healthcare | 3 | 0 | 90 | 0 | 39/88 | −0.4875 pp |
| Software | 7 | 6 | 102 | 3 | 53/108 | +0.0462 pp |

Interpretation: Semiconductor 09:35 breadth alerts missed **32/106** severe losses; gold missed **5/43**. Semiconductor's earliest qualifying historical severe-loss warning was **SNDK on November 13, 2025 at 09:35 ET**. Earliest other genuine severe-loss alerts: gold **AEM Dec 29, 2025 09:35 ET**, energy **XOM Apr 1, 2026 09:35 ET**, industrials **GE Mar 12, 2026 09:35 ET**, software **CRM Jan 29, 2026 09:35 ET**. Financials and healthcare generated no such major warnings in this sample. Warning time is **not** a preceding-evening or premarket forecast. Counting warnings after a stock has already lost 5% materially exaggerates early protective sensitivity.

Across all recorded semiconductor DOWN warnings, only **108/222** hypothetical early sales improved the subsequent regular-opening outcome by more than 0.30 pp; the mean assumed benefit was **negative**. In the last chronological 30% of dates the semis mean changed sign to **+0.2183 pp**, compared with **−0.2076 pp overall**, showing unstable regimes; no training-locked release inference. Gold later remained adverse **−0.5288 pp**. Software's slight positive average lacks stable breadth or sufficient serious-loss sample and is not approval.

The 09:35 breadth candidate does **not** implement the separate owner-required individual stock strict rule of **total decline ≥2.5% INCLUDING ≥1 percentage point in the last 15 minutes**. Those conjunctive synthetic-trigger tests already exist and should remain separately scored; combining the event universes without distinction would be misleading.

## Critical remaining limits

* Actual *broker-executable* NBBO/BOATS quotes, spreads, slippage, short eligibility, borrow, partial fills, and stop/limit queue behavior remain unavailable in these replay inputs.
* Overnight price gaps that occur **before** 09:35 cannot be prevented by this same-morning warning; even 09:40 exits can arrive after a major selloff.
* A beneficial sale in this counterfactual does not imply an overnight position was authorized, and does not establish that the 2pm CT flat exit should change.
* No synchronized preceding-evening futures, news, earnings/guidance, QQQ/market-calendar as-of evidence was incorporated, so preceding-evening detection remains blocked.
* The full sample has been repeatedly researched; no truly untouched forward-live shadow results or matched full Alpaca FILL UUID ledger. Nov 9 is not scored as a fully completed trading session.

## New research artifacts

* `research/v2_52week_0935_downside_nextopen.py` — causal time-ordered warning, exact following ETF RTH opening day and quote-missing fail-safe.
* `research/test_v2_52week_0935_downside_nextopen.py` — four targeted tests covering true/false warning counts, unobserved next open, already-gap-lost cases and earliest timestamps; total run for 3 new test suites **16 passing**.
* `research/results/v2_52week_0935_downside_nextopen_2026-11-09.json` — all seven sector summaries with earlier/later date splits, false alarms, missed serious crashes and next-open benefit.
* Read-only full 3,968 peer stock-day rows in isolated host scratch `/tmp/v2-run23-full-year-anti-churn/nextopen-warning-daily.json`.

**Decision: no automatic sell/avoid-buys GO from the 09:35 breadth warning.** First improve *preceding-evening/very early* warning lead time without inflating false alarms, then validate post-signal price movement with executable quotes and genuinely untouched forward outcomes. V1 PAPER/LIVE and current broker orders unchanged.
