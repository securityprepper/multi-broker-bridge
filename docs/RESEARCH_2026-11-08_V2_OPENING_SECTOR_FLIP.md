# V2 opening-sector-flip stress test — November 8, 2026

**RESEARCH ONLY.** No live monitoring, broker authentication, order submission,
PAPER/LIVE deployment, or alteration of V1 trading safety controls.

## New question

The earlier preopen breadth study showed a failure mode on November 2, 2026:
SOXX and multiple semiconductor leaders were strong before the opening, yet
several finished down 5% or more. Can a **completed-bar reversal immediately
after the open** warn of this situation sooner than the original previous-close
2.5%/15-minute-1% weakness rule? Investigate both directions symmetrically.

This is an **additional candidate**, not a redefinition of the original rule,
which remains previous regular-session close to current price down at least
2.5%, **including** at least 1 percentage point during the last 15 minutes.

## Data and point-in-time protocol

Reuse local split-adjusted Alpaca SIP **five-minute OHLC** files for AMD,
AVGO, INTC, MU, NVDA, SNDK, SOXX, TSM, WDC. Scored regular stock-days:
**2,244** spanning November 10, 2025 to November 6, 2026; **254**
stock-days ended +5% or higher and **209** ended -5% or lower.
The previously audited **250** sector sessions are **118 positive,
83 negative, 49 mixed** (not reclassified in this experiment).

* At **09:15 ET**, observe only the completed 09:10 bar, using the previous
  completed regular-session close as denominator. Establish an **up** preopen
  setup when SOXX is up >=0.5% and >=4 of eight peers up >=0.5%; use symmetric
  thresholds for a **down** setup. No setup -> no flip candidate.
* At each **09:35, 09:40, ... 10:30 ET** checkpoint, read only the bar
  ending at that checkpoint. Propose a **down** flip after an **up** preopen
  setup if SOXX has fallen >=1 percentage point **from its 09:15 return**,
  the target stock has also fallen >=1 percentage point, and >=half
  the other peers have fallen >=0.5 percentage point. Symmetric requirements
  define an **up** flip after a **down** preopen setup.
* Every required symbol must have the same completed-bar timestamp,
  valid prior close and valid preopen bar; otherwise fail closed.
  The target's own price and its peers are compared using **percentage point
  moves relative to their own prior regular-session closes**, not the
  target's future closing result. At most one first event per stock-day.
* Future regular-session close, next-bar open, next-session opening and
  the +/-5%-by-close outcomes are used only to **score**, not select signals.
  Five-day regime annotations use only the preceding five **completed**
  regular-session closes, never the target day.

## Full sample: early-warning coverage and false-alarm exposure

| Metric | Down flip after bullish preopen | Up flip after bearish preopen |
| --- | ---: | ---: |
| Signals | **249** | **270** |
| Same-direction eventual +/-5% closing days caught | **25 / 209** | **13 / 254** |
| Signals on nonmajor closing days | **224** | **257** |
| Major moves warned before target had moved 5% | **25** | **12** |
| Hypothetical bounded advantage to 14:00 ET | **+0.6945 pp** | **-0.2204%** |
| Hypothetical bounded advantage to following regular open | **+1.0592 pp** | **-0.2529%** |

**These averages are NOT live returns or fills.** Model a limit envelope
30 basis points away from the signal price, 15 bp adverse execution friction
per side, and only the next five-minute bar's opening print as an eligibility
scenario. A price-eligible opening print does NOT demonstrate an executable
bid/ask, size, queue priority, order acknowledgement, or partial fill.
249/249 down and 268/270 up next-bar mark scenarios were price-eligible.
An ineligible scenario is assigned zero incremental advantage, not an
imaginary later fill. Here 14:00 refers to the completed 14:00 five-minute
bar's close.

A **nonmajor** closing day is not necessarily an unprofitable trade;
the correct distinction is signal sensitivity versus realized, costed exit
outcomes. Within the 249 down alerts, 136 improved the modeled 14:00
exit and 113 worsened it. The median improvement was **+0.2788 pp**.
The 249 warnings were concentrated across **34** separate trading days
(day-equal mean **+0.5810 pp**). Excluding November 2, the signal-weighted
mean remained **+0.6084 pp**. Up flips were spread over **38** days
(day-equal mean **-0.3724 pp**).

### Earlier/later holdout stress

| Side | Earlier through Aug 31, 2026 | Sep 1 to Nov 6, 2026 |
| --- | --- | --- |
| Down flip | 211 signals, 20 major hits, **+0.7118 pp** to 14:00 | 38 signals, 5 major hits, **+0.5985 pp** |
| Up flip | 230 signals, 12 major hits, **-0.1343%** to 14:00 | 40 signals, 1 major hit, **-0.7156%** |

This is a **retrospective split**, not independent prospective validation.
The same semiconductor universe is selected across both periods.
The small later sample and correlated stock signals limit confidence.

Previous five completed sessions of SOXX declined >=5%:
74 down-flip signals averaged **-0.9423 pp** early-sell advantage to
14:00, versus **+1.3866 pp** for the other 175; 70 up-flip signals
averaged **-0.9362%** versus **+0.0301%** for the other 200.
These are descriptive, in-sample regime differences, **not** a
validated rule or a reason to auto-sell.

## Case study: Monday November 2, 2026

The prior fixed preopen snapshot found SOXX +0.92% at 08:30 ET
and +1.41% at 09:15 ET, but SOXX eventually finished -3.80%.
This new completed-bar sector-flip candidate issued **09:40 ET** down
alerts for AMD (-7.61% at close), INTC (-8.95%), MU (-5.84%),
SNDK (-6.46%), WDC (-7.47%), and also SOXX (-3.80%),
AVGO (-1.16%) and TSM (-1.85%).

Relative to the original **previous-close 2.5% total/1% in
15 minutes** premarket-or-first-hour warning, among the five
major-loss stock candidates on November 2:
* INTC's original warning was **09:35**, ahead of this 09:40 candidate.
* WDC's original warning was **09:50**, ten minutes later.
* AMD, MU and SNDK had **no original warning by 10:30**.

Across the full sample, **18 of the 25** major down-flip detections
were earlier than the original strict warning or not detected by that
rule's premarket+first-hour window; **8** of the 25 had no original
strict warning by 10:30. This experiment does **not** demonstrate
a warning before the market opened: 09:40 is an **after-open** signal.

Important missed severe decliners include INTC on October 30, 2026
(-28.50%) and SNDK on November 5 (-22.25%). This conditional reversal
candidate cannot capture every crash, including days without a qualifying
opposite premarket SOXX+peer setup.

## Independent decisions / remaining blockers

* **Downside track:** The candidate can provide some earlier first-hour
  alerts after misleading positive premarket breadth. However **224
  nonmajor alerts for just 25 eventual major-loss hits** is too broad
  to justify automatic selling. Validate with executable quotes, sizes,
  timed stop/limit fill simulation and true held-position results.
* **Upside track:** Only 13/254 major gainers were detected, and the
  later-period projected entry performance was negative. Do **not**
  automatically buy up flips. Research sector continuation and
  stock-specific catalysts separately, with independent sectors.
* **Data gap:** Only 52-week 5m SIP OHLC, not 52-week synchronized
  NBBO/SIP quotes, BOATS overnight quotes, futures/news/earnings
  arrival times, or matched V1 actual fills. Alpaca supports historical
  SIP/BOATS quote APIs, but authorization, actual records and replay
  were not established in this experiment.
* **Research integrity:** Results are exploratory and threshold selection
  is not a prospective preregistered strategy; use walk-forward and
  separate-sector validation before considering PAPER shadow trading.

## Files and reproducibility

Code: `research/v2_opening_sector_flip_stress.py`, tests:
`research/test_v2_opening_sector_flip_stress.py`, structured results:
`docs/RESEARCH_2026-11-08_V2_OPENING_SECTOR_FLIP_RESULTS.json`.

`python3 -m research.v2_opening_sector_flip_stress --output /tmp/v2_flip.json`

**94 offline research tests passed:** 84 existing tests in the previous
isolated canonical checkout plus 10 new targeted causality tests. No
production checkout, existing divergent research worktree, host timers,
broker accounts, PAPER positions, LIVE safeguards or order state changed.
