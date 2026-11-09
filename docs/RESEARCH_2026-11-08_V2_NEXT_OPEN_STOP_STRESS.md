# V2 synthetic stop vs holding through next regular open — 2026-11-08

**Research only. No PAPER/LIVE orders submitted or V1 system changes.**

## Research question and method

After a sector-confirmed early down alert, would a modeled sell at the
next five-minute open outperform holding until the following trading
session's **09:30 ET regular open**? For early up alerts, would buying
at that time and exiting at the following regular open be profitable?

Use the same **2025-11-10 to 2026-11-06** nine-symbol, split-adjusted
Alpaca SIP 5-minute OHLC replay (2,244 stock-days, 254 >=5% up,
209 <=-5% down). The prior sector audit labels 250 days:
118 positive, 83 negative, 49 mixed. There are no live broker fills,
NBBO depth/quotes, or complete BOATS overnight quotes in the dataset.

Signals are only from completed 09:45–13:00 ET candles, optionally
requiring >=0.25% SOXX direction and at least half of other
semiconductor peers in the same direction. Continue monitoring until
each rule family obtains its first confirmed signal, not just its first
unconfirmed candidate. Only previous regular close and completed
contemporaneous bars are inputs.

At a signal: simulate price eligibility for a 30bp bounded limit
against the *next* five-minute opening print after 15bp adverse
execution friction. If ineligible, do not invent a fill (a modeled
nonfill has zero exit advantage relative to holding). If eligible,
compare a long stock sale at that next opening price, with 15bp
friction, to a sale at the following trading session's 09:30 opening
print, with equal friction. Upward alerts model an overnight buy
then sale at the following regular open, with 15bp on each side.
Future opening prices are evaluation outcomes **only**.

**All outcomes are hypothetical next-bar price scenarios.** A next
five-minute OHLC opening print does not establish available bid/ask,
share size, actual execution latency, exchange session restrictions or
whether a particular limit order would fill.

## Results: only first signal re-confirmed by SOXX + peer breadth

| Event family | Warnings | Next regular open observed | Next-bar limit price eligible | Mean bounded benefit compared with holding until next regular open |
| --- | ---: | ---: | ---: | ---: |
| Down from previous close | 440 | 440 | 436 | **-0.3974 pp** |
| Down from intraday high | 516 | 516 | 510 | **-0.2936 pp** |
| Up from previous close | 423 | 415 | 413 | **+0.6498%** hypothetical overnight return |
| Up from intraday low | 515 | 508 | 505 | **+0.2416%** hypothetical overnight return |

For down-from-high, the 516 warnings include 160 eventual
>=5%-decline close days and 356 other stock-days; **244**
price-eligible modeled early exits improved upon waiting until next
open, while **266** were worse. The average -0.2936pp means
**holding won overall** in this particular sample/assumption.

The unfiltered down-from-high comparison had 862 alerts,
853 scorable next regular opens and **-0.4138 pp** average early-exit
advantage. Sector confirmation reduces the modeled average loss from
premature sales but still does **not** turn the strategy profitable
as a replacement stop.

Earlier/later split for filtered **down-from-high**:
- Through August 31, 2026: 452 warnings, mean **-0.4143 pp**
  from early exit versus holding through the next regular open.
- September 1 through November 6: 64 warnings, mean **+0.5590 pp**.

Earlier/later split for confirmed **up-from-previous-close**:
- Earlier: 367 warnings, mean **+0.7366%** hypothetical overnight gain.
- Later: 56 warnings, 48 next-open outcomes, mean **-0.0138%**.

These are **not** rolling out-of-sample live profitability estimates:
the stock universe is selected retrospectively and the thresholds
have not been independently validated in different sectors. The
later-period results are unstable and cannot justify an automatic
strategy.

## Notable examples and limitations

On **2026-08-05**, WDC's confirmed down-from-high warning was
**10:35 ET**. A hypothetical eligible next-five-minute sale would
have been **22.266 percentage points** better than waiting until the
following session's regular opening, measured against prior close.
This is an extreme historical example, not a fill claim or expected
result. Many other warnings lost money by exiting before an overnight
recovery.

A fixed software stop cannot guarantee a sell when bid liquidity
disappears. A rapidly falling stock can gap beyond a limit order;
cancel/replace after partial fills introduces broker-order-state
risks. There is no direct test here of session-specific Alpaca
overnight limit eligibility or held-share position state.

**Conclusion:** Maintain the synthetic stop as a research-only
candidate. It is not presently justified as an automatic PAPER or
LIVE exit. The next decisive validation requires synchronized
timestamped SIP/BOATS NBBO quotes, open-order/fill replay, V1
position-level comparison, late-session risk, and live PAPER shadow
latency and bid/ask depth measurements.

## Reproducibility

- `python3 -m research.v2_next_open_stop_stress --output /tmp/v2_next_open_stress.json`
- `python3 -m unittest -q research.test_v2_next_open_stop_stress`

Together with previously committed V2 studies, **53 research
unit tests passed** in the isolated V2 checkout, including seven
new next-open stress tests. No production modules were modified.
