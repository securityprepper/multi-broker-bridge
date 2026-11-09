# V2 prior-five-session regime stress: two-sided signals — November 8, 2026

**Research only — no broker orders, streaming execution, V1 PAPER/LIVE changes, or production deployment.**

## Question

Can the **five completed sessions preceding** each market day distinguish useful
semiconductor upside entries or downside exits from expensive false alarms?

Reuse the V2 SOXX + at-least-half-of-peers confirmed 09:45–13:00 ET
five-minute signals. Two prespecified candidate families are analyzed separately:
- **Up from previous regular close**: 2.5% up, including 1 percentage point of upward movement in the latest 15 minutes.
- **Down from intraday high**: 2.5% down from the observed intraday high, including 1 percentage point in the latest 15 minutes. This is an *alternative* trigger, not a reinterpretation of the owner's original **2.5% down from previous close** alert.

At each candidate signal, completed five-minute bars and previously observed SOXX
and peer prices are the *only* live-time signal inputs. A separate cohort feature
uses **six consecutive completed daily closing observations ending yesterday**
to compute the five prior session-to-session returns. If any close is absent,
the cohort is omitted. No current-day close, next regular opening price,
or eventual >=5% outcome label is available to the signal or prior-five feature.

Prespecified buckets: prior-five SOXX **weak <=-5%**, **strong >=+5%**, else
neutral; stock versus SOXX relative return lag <=-3 percentage points, lead
>=+3 points, otherwise neutral. These buckets are diagnostic and **must not**
be retrospectively optimized into a production rule.

## Sample, scoring and missingness

The nine-symbol, split-adjusted SIP five-minute dataset covers 2025-11-07 through
2026-11-06 (AMD, AVGO, INTC, MU, NVDA, SNDK, SOXX, TSM, WDC). The original
two-sided audit covers **2,244 stock-days**, including **254 >=5% gainers** and
**209 <=-5% decliners**; previous sector-wide labels were 118 up, 83 down,
49 mixed sessions. This prior-five analysis includes **2,148** stock-days
with *complete* consecutive history, excluding 96 stock-days; eligible
cohorts contain **244 >=5% gainers and 206 <=-5% decliners**.

For each qualifying warning, the outcome is a hypothetical 30-bp bounded
limit order at the next five-minute **opening price** with 15-bp adverse
execution friction, compared with holding until the **following trading
session's 09:30 ET opening price**. An order failing that next-bar price
eligibility is treated as **not executed**, with zero modeled benefit.
Missing next-session prices are **excluded from outcome averages**, not
counted as gains. Down numbers are *percentage points saved by early sale*,
up numbers are *hypothetical overnight return percentages*.

This is not an order-book backtest: no synchronized bid/ask sizes, BOATS
quotes, real partial fills, slippage distributions, market session
restrictions, live broker execution receipts or actual V1 position matching.

## All complete-prior-five stock-days — signal coverage

| Confirmed family | Period | Major moves in cohort | Warnings | Major hits | Nonmajor warnings | Mean bounded vs next open |
|---|---|---:|---:|---:|---:|---:|
| Up from previous close | All | 244 | 409 | 196 | 213 | +0.6674% |
| Up from previous close | Through 2026-08-31 | 221 | 353 | 175 | 178 | +0.7600% |
| Up from previous close | 2026-09-01 onward | 23 | 56 | 21 | 35 | -0.0138% |
| Down from intraday high | All | 206 | 503 | 157 | 346 | -0.3261 pp |
| Down from intraday high | Through 2026-08-31 | 157 | 439 | 127 | 312 | -0.4551 pp |
| Down from intraday high | 2026-09-01 onward | 49 | 64 | 30 | 34 | +0.5590 pp |

The full-sample labels should **not** be compared directly with these
coverage rates without accounting for the 96 omitted stock-days.

## Most informative five-day sector stress

| Family and prior-five SOXX regime | Earlier warnings (major hits) | Earlier modeled result | Later warnings (major hits) | Later modeled result |
|---|---:|---:|---:|---:|
| Up entry, weak SOXX <=-5% | 105 (63) | +1.0487% | 22 (9) | **-1.3757%** |
| Up entry, SOXX not weak | 248 (112) | +0.6377% | 34 (12) | **+0.5470%** |
| Down exit, weak SOXX <=-5% | 99 (20) | **-2.3017 pp** | 23 (16) | **+2.1701 pp** |
| Down exit, SOXX not weak | 340 (107) | +0.0826 pp | 41 (14) | **-0.3448 pp** |

**Interpretation:** A simple prior-five weakness gate would have made
September–November upward entry results appear more favorable, but **nine of
that period's 23 major winners** had weak prior-five SOXX context. It would
also have **worsened earlier-period entry results** by omitting a successful
cohort. For downside protection, the weak-sector cohort's sign reversed
between periods — early sale was substantially worse than next-open holding
earlier, but better later. These switches are evidence of regime instability
and false-alarm cost, **not justification for automated trading**.

Among the 22 later upward weak-SOXX warnings, **only 14** had observable
next-session open outcomes; the -1.3757% average is based on those 14,
not all 22.

## Reproducibility and safeguards

- Program: `research/v2_prior5_cohort_stress.py`.
- Tests: `python3 -m unittest -q research.test_v2_prior5_cohort_stress`.
- Research replay: `python3 -m research.v2_prior5_cohort_stress --output /tmp/v2_prior5_cohort_results.json`.
- Expected input files: `/tmp/semis_52wk_5min_sip_adjusted.json`,
  `/tmp/semis_peers_52wk_5min_adjusted.json`,
  `/tmp/semis_52weeks_alpaca_daily.json`.
- The new six offline checks and 22 existing as-of/next-open checks
  all passed on the authorized research host. The research script
  was executed read-only against those historical inputs.
- No changes to production checkout, divergent research worktree,
  live timers, streaming feeds, V1 monitors, broker positions, or orders.

**Next research:** Independently verify the five-day feature on forward,
cross-sector samples; obtain timestamped SIP/BOATS bid/ask streams and
session-specific order-state readbacks; compare actual PAPER shadow order
eligibility and V1 matched results. Maintain day-by-day reviews of all
large upward and downward moves, including opportunities never signaled.
