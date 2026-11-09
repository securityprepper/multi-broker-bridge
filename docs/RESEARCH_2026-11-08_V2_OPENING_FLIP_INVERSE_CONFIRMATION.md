# V2 SOXS / SOXL leveraged ETF confirmation stress — November 8, 2026

**Research only. No V1 changes, PAPER or LIVE orders, feeds, timers, or broker requests.**

## Question and causality

Would using inverse SOXS together with leveraged-long SOXL as a
synchronized **completed-bar** confirmation improve the V2 first-hour
sector-flip warnings? The underlying warning is distinct from the
owner's unchanged previous-close **2.5% total decline including 1%
over the last 15 minutes** rule.

Start from the isolated preopen SOXX+peer setup at **09:15 ET**, then
evaluate each completed five-minute bar from **09:35 through 10:30 ET**.
The base flip requires SOXX and stock opposite moves of >=1 percentage
point from 09:15, plus half of other semiconductor peers moving
>=0.5 percentage point. Optional independent price-feed checks require:

* **SOXS-only 2pp:** SOXS moves >=2 percentage points from its 09:15
  return in the direction opposite the previous SOXX preopen trend.
* **SOXS+SOXL 2pp, 4pp or 6pp:** In addition to SOXS, SOXL moves
  in the opposite direction by the same threshold.
* Always **re-evaluate** the base flip and the leveraged ETF gates at
  each new completed bar; a late qualifying confirmation is allowed.
  Requiring confirmation only at the first unconfirmed bar would
  create a misleading number of misses.

Both ETFs are leveraged products tracking related semiconductor exposure:
their agreement is **not independent fundamental evidence** of a future
crash or of executable liquidity. These are deliberately exploratory
fixed sensitivity checks, not a live-selected optimized rule.

Historical data: separate split-adjusted Alpaca SIP five-minute OHLC
series for SOXS (48,762 bars) and SOXL (48,887 bars), plus the previously
audited nine semiconductor symbols. Covered dates November 10, 2025
through November 6, 2026: 2,244 stock-days, 209 >=5% declines,
254 >=5% advances. The existing sector audit has 118 positive,
83 negative and 49 mixed sessions.

## Downside: warning to sell after a bullish preopen reversal

| Confirmation | Signals | Severe declines detected | Other warnings | Mean alert delay vs base | Hypothetical bounded advantage to 14:00 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base SOXX+peer flip | 249 | 25/209 | 224 | 0 min | +0.6945 pp |
| SOXS >=2pp | **249** | **25** | **224** | **0 min** | **+0.6945 pp** |
| SOXS and SOXL >=2pp | **249** | **25** | **224** | **0 min** | **+0.6945 pp** |
| SOXS and SOXL >=4pp | 219 | **25** | 194 | **5.09 min** | +0.7130 pp |
| SOXS and SOXL >=6pp | 155 | **19** | 136 | **11.84 min** | +0.7678 pp |

The 2pp inverse filter is **completely redundant** on the observed
first qualifying bars: **not one** of 249 warnings is removed,
delayed or added. This is unsurprising because SOXS and SOXL are
leveraged semiconductor products and tend to amplify SOXX moves.

The 4pp pair gate removes 30 nonmajor warnings without losing any
of the 25 eventual major closing-loss detections, **but** those 219
remaining warnings still include 194 nonmajor events. It delays
confirmation on average five minutes; its mean hypothetical benefit
versus **the following regular open** was **+0.8900 pp**, lower than
the base candidate's **+1.0592 pp**. Reducing nonmajor warnings does
not automatically improve an exit strategy.

A 6pp gate removes more nonmajor warnings **but misses six major
decliners**, including all five November 2 example stocks, and
delays remaining alerts by nearly 12 minutes. It is a poor
stand-alone crash-protection candidate.

## Upside: warning to buy after bearish preopen reversal

| Confirmation | Signals | Eventual >=5% gainers detected | Other warnings | Mean delay | Hypothetical bounded return to 14:00 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 270 | 13/254 | 257 | 0 min | -0.2204% |
| Pair >=2pp | 270 | 13 | 257 | 0 min | -0.2204% |
| Pair >=4pp | 205 | 12 | 193 | 4.46 min | -0.1986% |
| Pair >=6pp | 111 | 5 | 106 | 9.41 min | -0.2781% |

The full-year buy-side results remain negative in these same-day
scenarios. In the September–November later segment, pair-4pp
upside signals averaged **-1.0228%** to 14:00. No tested variant
supports automatically buying upward reversals.

## Important November 2, 2026 counterexample

At 09:15 ET SOXX had advanced +1.41% from the previous regular
close. The first unfiltered postopen reversal warned at **09:40 ET**
for AMD, INTC, MU, SNDK and WDC, all of which finished down >=5%.
The SOXS >=2pp and dual >=2pp checks were already confirmed at
**09:40** and contributed **zero additional discrimination**.

The 4pp dual leveraged ETF confirmation did not arrive until **09:55**
for those five stocks, 15 minutes *later* than the initial warning;
the 6pp gate failed to qualify them by 10:30. Neither is an
early-morning or previous-evening prediction.

## Execution and validation limits

All outcome numbers are **hypothetical next-five-minute opening-price
eligibility marks**, with 30bp allowable limit distance and 15bp
adverse per-side price friction. They do not establish actual NBBO
quotes, fill quantities, latency, order queue, overnight execution,
paper-position P&L or whether held positions should be sold.
The 4pp down filter was price-eligible on 218 of 219
next-bar opening scenarios, not on 218 actual orders.

Comparisons are in-sample exploratory parameter stress tests;
the later September–November 2026 segment is only a retrospective
holdout, not a forward-trading evaluation. No longer-term gain
strategy or independently observed other-sector confirmation was
established here. The lack of full historical SOXS/SOXL bid/ask
depth, synchronized 52-week BOATS quotes, news/futures timestamps
and matched V1 fills prevents actual order-execution claims.

Files:
`research/v2_opening_flip_inverse_confirmation.py`,
`research/test_v2_opening_flip_inverse_confirmation.py`,
`docs/RESEARCH_2026-11-08_V2_OPENING_FLIP_INVERSE_CONFIRMATION_RESULTS.json`.

Run:
`python3 -m research.v2_opening_flip_inverse_confirmation --output /tmp/v2_inverse.json`

**Nine new isolated tests passed** for alignment, both directions,
missing bars, late retrigger, future-leakage refusal and numerical
thresholds, in addition to the ten new first-hour flip tests and
84 earlier research tests. **103 total isolated tests passed.**
No production or divergent research worktree changes.
