# Version 2: 52-week early downside alerts and missing up days (2026-11-08)

## 1. Scope and correct opportunity counts

Historical Alpaca SIP split-adjusted five-minute and regular-close data across **251 sessions** Nov 7 2025 to Nov 6 2026 (250 day-to-day observations) for AMD/MU/SNDK/SOXX and five additional symbols NVDA/AVGO/WDC/TSM/INTC. The annual five-minute study does not include the 8 PM–4 AM ET BOATS venue. These are historical OHLC bars, not executable quotes.

Broad sector direction: 2 of 3 leaders AMD/MU/SNDK plus SOXX aligned. **118 positive**, **83 negative**, **49 mixed** daily close-to-close moves.

- Broad early bullish trend warning (2-of-3 positive, +0.5% versus prior close, ~+0.3% 15-minute momentum): recognized **81 of 118 positive days**, ~68.6% recall; 37 positive days missed.
- Strict trend candidate: identified **45 of 118** positive days, ~38.1% recall; most missed days were deliberately skipped because of stricter breadth.
- Current deployed V1 narrow buy strategy requires previous five COMPLETED sessions classified down and strict rebound breakout: **19 modeled signal days**, 16/19 modeled profitable without catalyst news; the specific AMD adverse earnings/guidance veto blocks Feb 5 only, leaving 18 model candidates, 16/18 modeled winning. It is NOT a model that purchases on most positive days.
- Among the 37 positive days missed even by broad early detector, **36 had complete phase-price coverage**: 15 started premarket DOWN and then regular-hours UP; 11 were premarket UP and regular-hours UP; 5 were premarket MIXED and regular-hours UP; 5 premarket UP and regular-hours MIXED. Thus **31/36** missed positive days finished with positive regular-session direction or reversal. Separate RTH recovery, gap-up and multiday continuation patterns deserve testing. One missed positive day had incomplete phase bars.

## 2. Big sector downside: early warning recall and false positives

Define a **major semiconductor loss day** as either SOXX regular-close-to-regular-close **<= −5%**, OR at least two of AMD/MU/SNDK **<= −5%** regular-close-to-close. Historical **35 of 250 days = 14.0%**. SOXX itself <=−5% on 12 days; at least two leaders <=−5% on 34 days, with overlap.

Only use completed bars from the previous afternoon 16–20 ET or same-day 04–09:15 ET; each 5-minute bar is known at its END. A signal before the regular opening is a **warning of already observed selling**, not guaranteed forecast of closing prices.

| Warning rule | Days flagged | Major-loss days caught /35 | Recall | Nonmajor alerts | Precision |
|---|---:|---:|---:|---:|---:|
| Sensitive: two leaders <=−0.3% vs prior close and <=−0.2% over 15m; SOXX <=−0.15%, SOXX momentum nonpositive | 140 | 29 | 82.9% | 111 | 20.7% |
| Confirmed: two leaders <=−0.75% and <=−0.3% over 15m; SOXX <=−0.375% | 119 | 27 | 77.1% | 92 | 22.7% |
| Strict three leaders down at confirmed thresholds | 88 | 25 | 71.4% | 63 | 28.4% |
| Severe: two leaders <=−1.5%, <=−0.7% over 15m; SOXX <=−0.75%, SOXX momentum nonpositive | 53 | 20 | 57.1% | 33 | 37.7% |

The sensitive signal **caught all 12/12 SOXX >=5% decline days**, earliest available warning on **10 preceding evenings and 2 same-day premarkets**. Both SOXX >=10% decline sessions also alerted. It had many false alarms: crucially **49 of 118 actual positive-closing sector days** also exhibited a sensitive early negative signal. Its implied probability of a later major sector loss conditional on the signal was only 20.7%, versus 14.0% unconditional baseline. **DO NOT auto-sell an entire portfolio based solely on that alert.**

Six of the 35 combined-major-loss dates missed by the sensitive warning: Nov 20 2025; Mar 30, Jul 15, Jul 27, Jul 31, Nov 2 2026. Many displayed positive/mixed premarket moves followed by regular-hours declines. A premarket-only detector cannot reliably predict a new selloff that begins AFTER open; build a separate regular-hours downside monitor.

## 3. Individual names can crash without a sector alert

Across the nine-symbol universe, **71 trading days** had >=1 symbol down >=5%. Only **35** of those were also major sector-loss dates: **36 additional dates** contain single-name/idiosyncratic severe losses that a sector-only risk detector would miss. There were **209 evaluable stock-day >=5% decline events** among 2,244 stock/day observations with complete price history.

| Single-stock as-of-time alert | Flagged stock-days | Big stock declines caught /209 | Recall | Precision |
|---|---:|---:|---:|---:|
| Stock <=−0.5% versus prior close and <=−0.2% previous 15min | 1,278 | 187 | **89.5%** | 14.6% |
| Stock <=−1.0% and <=−0.3% previous 15min | 948 | 179 | **85.6%** | 18.9% |
| Stock <=−2.0% and <=−0.5% previous 15min | 490 | 150 | **71.8%** | 30.6% |

The sensitive rule caught at least one impending large-decline ticker on **64/71** calendar dates but would have raised warnings on **205 days**. That's far too noisy for high-severity liquidation instructions. The more selective rule still flags 132 days, catches a big declining ticker on 51 days, and has ~30.6% stock-day precision. Important to split **WATCH** and **HIGH-RISK**, and prioritize specific symbols actually held.

Per-name large-down days: AMD 23, MU 32, SNDK ~50–51 (source-specific daily-close vs last 5minute close difference), SOXX 12, NVDA 4, AVGO 9, WDC 39, TSM 6, INTC 33. Historical pattern includes earnings and single-name losses; do not assume all stocks fall with SOXX.

## 4. New independent tasks

- Created **Task - Trading Strategy Research**, enabled daily **09:30 America/Chicago**, including additional V2 entry/exit tests and early downside warnings before market opening; V1 protected.
- Created **Task - Semiconductor Downside Warnings**, enabled hourly condition watch, read-only with explicit before-open / during-market risk checks and notification when high-confidence new warnings arise; **not fast enough to replace a local five-minute host alert** and does not issue orders.
- Version 1 PAPER runner, current monitors and task schedules were not modified by these analyses.

## 5. Next development priorities

1. Implement independent **notification-only, host-side** five-minute stock-specific and sector-wide risk monitor; no broker order permissions, no V1 source changes. Tiered warnings with exact ET/CT times, last 5/15/30m, prior-close changes, risk of >5%, and clear confidence that these are *observations, not guaranteed crashes*. Deduplicate and throttle high-severity notifications.
2. Historical **stock-specific earnings/guidance** first-publication cutoff, scheduled macro releases, QQQ/Nasdaq futures, S&P / global semiconductor indicators. Evaluate which increased precision of 35 sector-major and 71 any-stock-major days without losing excessive early alerts.
3. Analyze all six major-loss days *without preopen warning*; distinguish positive premarket followed by red RTH and broken support at 9:30/10:00. An intraday warning may prevent losses even when a prior-evening forecast was impossible.
4. Study what would happen if a held PAPER account actually sold on different risk severities, vs holding, considering realized spreads, back-to-back reentries, broker fills, expected cost of false signals and mandatory hard-flat requirements. **No automatic liquidation authorized from these research rules.**
5. Extend bullish detection to regular-hours gaps, first rising day, multiday follow-through and own-catalyst individual winners; score against 118 up days, not just 18 narrow V1 events.

This document and research scripts live on the *V2 research branch* `research/rebound-v2-conditional-exits`; current Version 1 remains unchanged.

## 6. Subsequent independent alert-only host deployment

Following the original exploratory study, a separate V2 warning-only sidecar was implemented and enabled on the authorized www3 host. This **did not change any V1 monitor, broker executor, PAPER trading policy or LIVE safeguards**.

- Code on V2 research branch: `research/v2_downside_watch_only.py`, and `research/test_v2_downside_watch.py` (6 tests passed).
- Host-only installation `/opt/securityprepper/semis-downside-v2/research/v2_downside_watch_only.py`; systemd `semis-downside-v2-warning.timer` active and enabled, every **five minutes** at second 25; runs as `tradingsector` with restricted service options and its own private state directory `/var/lib/semis-downside-v2`.
- **No broker-order functions**, no broker POST endpoints; only historical Alpaca market-data GET and Pushover POST, with deduplicated notification state.
- Sends one explicitly labeled low-confidence **sector DOWNSIDE WATCH** per trading date when sensitive price and breadth downturn conditions appear; sends separate escalation on severe sector deterioration or urgent individual stock symptoms (individual stock down 4% from prior close plus 1% over preceding 15 minutes). Lesser individual watch signals remain logged, not pushed. Alert text explicitly notes many historical false alarms and is **not an instruction to sell**.
- It requires aligned, completed five-minute sector bars, a recent previous completed regular close (fail closed on stale/holiday data), and rejects sparse/stale candles; usable on SIP or BOATS if the provider returns sufficient data.
- Independent host test with historical Nov 4 at 7:00 PM ET returned `DOWNSIDE_WATCH` ahead of Nov 5's severe collapse; historical Nov 5 at 7:35 AM ET returned `STOCK_URGENT` on SNDK. Both used `send=False`: they verified signals, **not actual Pushover delivery**. Sunday service returned `SESSION_CLOSED` with no orders or notifications. Provider delivery and real-session repeatable monitoring remain to be verified.
- A supplemental hourly ChatGPT automation `Task - Semiconductor Downside Warnings` was enabled; it reads this service's records/journal and current broker positions READ-ONLY. Research task `Task - Trading Strategy Research` was separately enabled daily at 09:30 Chicago time.

**Limits:** At these loose sensitive thresholds false alerts are expected; avoid alarm-based liquidation. A failure to obtain BOATS bars, official holidays, stale daily bars, or unavailable credentials blocks the warning, not the underlying potential decline. It is not a guaranteed early-warning system, and it presently has no model for the six sector-major days that first broke down after the opening bell. Extend V2 specifically for regular-hours breakdown and company-earnings overnight cases, then compare actual broker readbacks to alert issuance times.
