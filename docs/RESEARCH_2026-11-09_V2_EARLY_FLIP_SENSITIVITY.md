# V2 09:35–10:30 first-hour sector reversal threshold sensitivity — 2026-11-09

**RESEARCH ONLY.** No broker connectivity, executions, V1 modifications or schedule changes.

## Question / new results
Would an earlier, lower threshold for recognizing the reversal of a strongly bullish or bearish preopen semiconductor sector warn about severe falls sooner **without** giving away too much upside or provoking excessive false warnings?

The experiment replays the existing split-adjusted, five-minute Alpaca SIP OHLC history for AMD, MU, SNDK, NVDA, AVGO, WDC, TSM, INTC and SOXX, **2025-11-10 through 2026-11-06**, covering **2,244 stock-days**, **209 >=5% close-to-close declines**, **254 >=5% advances**, and the pre-existing **250 sector sessions: 118 positive, 83 negative, 49 mixed**.

The fixed 09:15 ET setup requires SOXX +/-0.5% and at least four semiconductor peers +/-0.5% from each name's previous regular close. Only at **09:35, 09:40, ... 10:30 ET**, once that exact five-minute bar has completed, examine a sector flip in the opposite direction. The ETF and target stock must each have moved at least the chosen percentage points from the 09:15 anchored return, with at least half the *other* peers moving at least the peer threshold. The original owner's previous-close **2.5% total decline including 1.0 percentage point over the most recent 15 minutes remains unchanged**; this is a separate candidate.

| Candidate (SOXX/stock/peers reversal pp) | Down alerts | >=5% losers hit / 209 | Other down alerts | Down exit vs 14:00 proxy | Down exit vs next regular open proxy | Up alerts | >=5% gainers hit / 254 | Other up alerts | Buy vs 14:00 proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 / 0.5 / 0.25 | 392 | **29** | 363 | +0.4058 pp | +1.0412 pp | 424 | **22** | 402 | -0.1822% |
| 1.0 / 1.0 / 0.50 (existing) | 249 | 25 | 224 | +0.6945 pp | +1.0592 pp | 270 | 13 | 257 | -0.2204% |
| 1.5 / 1.5 / 0.75 | 196 | 20 | 176 | +0.6010 pp | +0.7617 pp | 170 | 9 | 161 | -0.3012% |

**Interpretation:** The lower threshold detects four additional major close-to-close decliners, but produces **139 additional warnings on nonmajor-down days**; the stricter threshold misses five more serious losers. These are overlapping variants on the same stock-days, not independent predictions. "Other alert" simply means the stock did not finish beyond +/-5%, **not** that every such trade was unprofitable. The unfiltered signal is not sufficient for a guaranteed fill or an immediate sell.

## Early warning: November 2, 2026
On the five severe closing losers AMD (-7.61%), INTC (-8.95%), MU (-5.84%), SNDK (-6.46%), WDC (-7.47%), the 0.5pp variant first flagged the opposite bullish-preopen sector turn at **09:35 ET** from the just-completed 09:30–09:35 ET bars. The existing 1pp variant flagged them at **09:40 ET**. All five are **post-open**, not previous-evening or preopen warnings. The 1.5pp variant failed to warn on any of these five by 10:30. The existing owner's prior-close conjunction warned for INTC at 09:35 and WDC at 09:50 and did not warn on AMD, MU or SNDK by 10:30.

## Later-period robustness is worse for the earliest threshold

| Model | Sept.–Nov. down warnings | Severe down hits / 49 | Modeled downside exit vs 14:00 | Sept.–Nov. up warnings | Major up hits / 23 | Modeled upside return vs 14:00 |
|---|---:|---:|---:|---:|---:|---:|
| 0.5pp | 72 | 5 | **-0.2811 pp** | 77 | 1 | **-0.9997%** |
| 1.0pp | 38 | 5 | +0.5985 pp | 40 | 1 | -0.7156% |
| 1.5pp | 17 | **0** | +0.7301 pp | 29 | 1 | -1.2127% |

Larger positive early-exit advantage means hypothetical selling at the next-bar opening was better than holding until the 14:00 mark. A negative value means early selling did worse. The 1.5pp later 14:00 result applies to 17 **nonmajor** cases because it missed **every** major later-period decline.

An early threshold that looked helpful in an individual crash weakened average later-period results. Thus, **do not convert any of these thresholds into automatic exit/buy rules.** A lower threshold can function as a *watch / no-new-buy / elevated-risk* research signal, subject to a future bid/ask and false-alarm study.

## Explicit opportunity-cost test for deferring new buys until 09:45

Among 972 stock-days with a bullish 09:15 preopen breadth setup, **32** ultimately declined >=5% and **198** rose >=5%. With an opposite flip *already observed by 09:45*, a policy of withholding a **not-yet-placed** buy would have:

| Flip threshold | Buy vetoes by 09:45 | >=5% decliners among vetoes | >=5% winners among vetoes |
|---|---:|---:|---:|
| 0.5pp | 246 | 23 | **19** |
| 1.0pp | 142 | 20 | 7 |
| 1.5pp | 77 | 12 | 0 |

This describes **classification and opportunity cost**, not realized avoidance of broker losses. A 09:45 veto cannot save a position already purchased at 09:15 or during the premarket. All three thresholds miss many crashes, especially major downs without a qualified bullish preopen. The five-day SOXX return is computed only from the five *preceding completed trading sessions*; it does not influence candidate decisions or use the target day.

## Execution / causal controls / blockers
At a completed-bar alert, a hypothetical limit envelope is 30 basis points from the observed completed closing mark, with 15 basis points adverse price allowance. The *following* five-minute bar opening print tests price eligibility; ineligible cases are scored as **no fill**, not a future invented fill. Following-session 09:30 regular opening marks and the 14:00 price are used **only as outcomes**. They are not known when the alert occurs.

This is an **exploratory, correlated nine-symbol semiconductor sample** with early/later splits (through Aug 31 vs Sept 1 onward), not a prospective walk-forward out-of-sample rule. It is not enough to compare directly to V1 account-level realized fills. The host has no complete 52-week synchronized SIP NBBO bid/ask sizes, BOATS overnight quote book, 1-minute full-year bars, futures/news arrival timestamp panels or matched V1 execution ledger accessible to this study. Five-minute eligibility must **not** be described as an actual stop-fill rate.

No new PAPER/LIVE orders, active timers, broker accounts or production modules changed.

## Reproduction
Source: `research/v2_early_flip_sensitivity.py`, tests: `research/test_v2_early_flip_sensitivity.py`, results: `docs/RESEARCH_2026-11-09_V2_EARLY_FLIP_SENSITIVITY_RESULTS.json`.

`python3 -m research.v2_early_flip_sensitivity --output /tmp/v2-early-flip.json`

**115 isolated research tests passed** when the scratch checkout included the 103 previous tests plus 12 new causality tests. The data files were only read; the divergent research checkout and dirty V1 production checkout were untouched.