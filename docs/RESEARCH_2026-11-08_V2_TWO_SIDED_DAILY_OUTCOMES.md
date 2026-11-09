# V2 two-sided 52-week daily outcome audit — November 8, 2026

**RESEARCH ONLY — no orders or changes to V1.** This extends the prior
`RESEARCH_2026-11-08_V2_STOCK_WEAKNESS_EXIT_STRESS.md` study using only the
authorized host's existing split-adjusted historical Alpaca SIP five-minute
OHLC and daily bars. Nine symbols: AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM,
INTC. **BOATS 20:00–04:00 ET history, NBBO quotes, futures, news and actual
broker executions were NOT present in these inputs.** Numbers below are
retrospective offline scoring, not achievable-fill claims.

## Complete-day coverage and separated research tracks

* **250** eligible completed semiconductor sessions Nov 10, 2025–Nov 6, 2026:
  **118 broadly positive, 83 negative, 49 mixed** (2/3 AMD/MU/SNDK with SOXX
  confirming the direction).
* **2,244** evaluable symbol-days: **254 closed +5% or higher**, **209 closed
  -5% or lower**, measured from the previous completed regular close.
* The scripts examine **every eligible session** and stock, not merely those
  triggering a rule, and output a per-day stock audit (2,244 rows) and sector
  audit (250 rows) including real closes, intraday lows/highs, first warning
  timestamps, at-trigger changes, remaining close move, and hypothetical
  next-bar/14:00 observations. Outputs are retained locally for research and
  are regenerated from licensed data instead of committing raw feed rows.

## Upside — signal available before open OR by 10:30 ET

An **upside** candidate is a completed 5-minute bar showing a +2.5% move
from previous regular close and a +1.0% increase over the most recent 15
minutes, with the 1% INCLUDED in the 2.5%. Its first possible actionable
time is the bar's START+5 minutes. The decision scans preceding calendar
evening 16:00–20:00 ET (no fictitious Friday evening preceding Monday),
same-day 04:00–09:20 and first regular hour 09:30–10:25 bar starts.
The mirrored bearish threshold is scored independently.

| Rule | Signals | +5%-close stock-days caught | Not +5%-close | Before +5% already observed | Mean hypothetical long return to 14:00 ET |
| --- | ---: | ---: | ---: | ---: | ---: |
| Up +2.5% total AND +1%/15m | 630 | 235/254 (92.5%) | 395 | 170 | **+0.053%** across 627 price-observable signals |
| Up +1.5% total AND +0.5%/15m | 1,077 | 249/254 (98.0%) | 828 | 226 | +0.013% across 1,068 |
| Down -2.5% total AND -1%/15m | 550 | 180/209 (86.1%) | 370 | 129 | **-0.349 pp** average early-exit advantage vs hold to 14:00, 548 observations |
| Down -2% total AND -0.5%/15m | 816 | 197/209 (94.3%) | 619 | 173 | **-0.299 pp** average early-exit advantage vs hold to 14:00, 805 observations |

Bullish proxy assumes BUY at first available next five-minute bar open with
15 bps unfavorable price, then SELL at the 14:00 ET bar open less 15 bps;
this is 30 bps total assumed price friction, not observed bid/ask or commissions.
**There are no verified executions.** Bearish exit proxy compares selling
at first following bar open less 15 bps versus the 14:00 bar open less 15 bps,
both as percentages of previous regular close, not an actual held portfolio.

Caution: detecting a day that eventually closes +5% is NOT synonymous with
profiting from entry at signal time; the +5% label is never an input.

### Earlier/later test, fixed thresholds (not selected on later data)

| Candidate | Through Aug 31, 2026 | Sep 1–Nov 6, 2026 |
| --- | ---: | ---: |
| Up +2.5%/+1% mean proxy trade return to 14:00 | +0.134% (546 priced alerts) | **-0.495%** (81) |
| Up +1.5%/+0.5% mean proxy trade return to 14:00 | +0.071% (899) | **-0.296%** (169) |
| Down -2.5%/-1% early-exit advantage vs hold 14:00 | -0.618 pp | +0.917 pp |
| Down -2%/-0.5% early-exit advantage vs hold 14:00 | -0.518 pp | +0.606 pp |

These earlier/later differences undermine claims of a robust automatic
buy/sell trigger. They are scenario-level equal-weight averages, not V1 actual
fills or independent randomized strategies. An unfiltered 09:35-to-14:00
SIP-bar-price proxy across 2,242 available stock-days averaged **-0.266%**;
this is a reference, **not** a same-decision or equal-exposure V1 comparison.

## Missed major upside AND downside days

The original first-hour upside rule missed **19 of 254** +5%-close symbol-days.
Scanning 10:30–13:00 ET for **the SAME fixed +2.5%/+1% rule** would recover
six of those 19, but generates **49 additional alerts**, of which **43**
do not close +5%. The 49 assumed 14:00 exits averaged **-0.126%**, with
23 positive and 26 negative results. Later-period mean on that restricted
sample was +0.335%; too small / post-hoc to approve.

Examples:
* **SNDK, April 22, 2026:** finished **+8.358%**; no before-10:30 alert,
  but the unchanged momentum rule first qualified at **11:25 ET**. This is
  a missed late-opening winner, not evidence of an executable +8.358% trade.
* **WDC, December 10, 2025:** finished **+7.313%**; first qualifying midday
  alert **11:30 ET**.
* **WDC, November 20, 2025:** finished **-8.912%** after an intraday high
  **+6.385%** versus previous close; missed the standard pre/first-hour down
  conjunction and the relaxed version. Late reversals need a different
  signal from morning drawdown.
* **AMD, November 20, 2025:** finished **-7.820%**, no standard or relaxed
  pre/first-hour alert, despite RTH high +4.791%.
* **WDC, November 13, 2025:** the first qualifying standard downside
  warning was **04:20 ET** at -3.6725%; finished **-5.388%**.
* **SNDK, November 13, 2025:** **06:25 ET** at -4.8259%;
  finished **-13.937%**.

Allowing the standard bearish rule to scan until 13:00 ET additionally
captures 17 of the 29 major down stock-days not flagged by 10:30.
This is a **same-day after-open** detection, *not* evidence those 17 losses
could have been avoided the preceding evening, and many alerts may arrive
after losses already occurred.

## First-hour sector breadth / profitable trade test

A separate 09:50–10:30 ET **sector** candidate uses only completed 5-minute
observations: at least 2/3 AMD/MU/SNDK already +1% from their respective
previous closes, SOXX >=+0.5%, and SOXX +0.3% over the last 15 minutes.

* **91** days generated a sector signal; **78** later finished broadly
  positive, **13** did not; **40** of 118 broadly positive sector sessions
  had no signal. **49 of 66** SOXX +2% close-to-close days were caught.
* The SOXX next-bar BUY to 14:00 SELL proxy was available on 90 days,
  averaged **-0.161%** after 15-bps adverse adjustment each side, with
  only **43/90** positive. Strong classification is therefore NOT proof
  of profit after buying a move already underway.
* Five completed prior sector days containing >=3 broadly positive
  days: 39 priced signals averaged **-0.100%**; 0–2 prior positive:
  50 averaged **-0.200%**. Neither regime earns a positive mean.

## Prior five COMPLETED sessions (individual momentum stratification)

Among individual-stock +2.5%/+1% alerts, counting only the previous five
completed stock-to-stock closing changes:

| Five-day context | Earlier hypothetical mean to 14:00 | Later hypothetical mean |
| --- | ---: | ---: |
| 0–2 prior up days | +0.570% (248 alerts) | **-0.395%** (50) |
| 3–5 prior up days | -0.233% (285 alerts) | **-0.657%** (31) |

The apparently profitable earlier 0–2-up-day subgroup reverses in the
later sample. Do not retune on September–November to manufacture success.
Five-session context is a potential feature, not a validated edge.

## Next research priorities and hard limits

1. Add separate **preopen, first-hour and late-reversal** decision families.
   Distinguish early alert from detection after a 5% move; assess drawdowns,
   stopped-trade reentries and whether avoiding buys hurts later winners.
2. Enrich timestamped extended-hours decisions with BOATS, actual NBBO
   spreads/depth, one-minute data, **announcements and futures available at
   the time**, and matched PAPER/V1 signal & execution timestamps. Those
   components are not currently present in this 52-week replay; do not
   fabricate performance or market-state causality.
3. Trial thresholds and context features only on earlier sample or in
   walk-forward folds; keep the later interval out-of-sample. Compare
   actual buy/sell decisions with V1 only after corresponding historical
   V1 decisions and fills can be aligned.

**Disposition: HOLD research-only.** The new tests do not support turning
either momentum warning into an automatic PAPER entry/exit and provide
no authorization to modify V1 timers, LIVE protections or broker orders.

### Reproduce on authorized www3 host research worktree

```sh
PYTHONPATH=. python3 -m research.v2_two_sided_daily_outcomes \
  --daily-csv /tmp/v2_stock_daily_audit_20261108.csv \
  --sector-csv /tmp/v2_sector_daily_audit_20261108.csv
PYTHONPATH=. python3 -m research.v2_midday_prior5_stress
PYTHONPATH=. python3 -m unittest discover -s research -p 'test_*.py'
```

Historical inputs are expected to exist locally as
`/tmp/semis_52wk_5min_sip_adjusted.json`,
`/tmp/semis_peers_52wk_5min_adjusted.json`,
`/tmp/semis_52weeks_alpaca_daily.json`. All are noncommitted temporary
data files, not guaranteed to persist. Daily results are research-scoring
outputs, not actionable trading recommendations or verified fills.
