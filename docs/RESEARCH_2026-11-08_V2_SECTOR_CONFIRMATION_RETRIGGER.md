# V2 two-sided sector/peer confirmation with rolling re-trigger — November 8, 2026

**Research only. No streaming executor, broker orders, V1 changes, or LIVE authorization.**

## Scope, provenance, and leakage controls

Reuse the 52-week split-adjusted Alpaca SIP five-minute historical files: nine
symbols (AMD, AVGO, INTC, MU, NVDA, SNDK, SOXX, TSM, WDC),
**2025-11-10 through 2026-11-06**. The existing audit contains
**2,244 stock-days**, including **254 close-to-close gains >=5%** and
**209 close-to-close losses >=5%**. The prior 250-sector-session labels
are **118 positive, 83 negative, 49 mixed**.

This experiment evaluates candidate alerts from the completed **09:45–13:00 ET**
five-minute bars. It does not replace premarket/evening research.
The alert families are the existing overlapping 2.5%/1%-in-15-minutes
rules from previous regular close or observed intraday extrema (the intraday
reversal is a distinct candidate, NOT a reinterpretation of the owner's
original previous-close 2.5% rule).

At **each completed bar**, a proposed alert can be confirmed by:
* **SOXX direction:** SOXX >=+0.25% from its prior regular close for upside
  (<=-0.25% for downside).
* **Peer breadth:** at least half of the *other* semiconductor names have
  moved >=+0.25% (<=-0.25%) versus their prior close. Exclude the stock
  being traded; for SOXX evaluate all eight peers.
* An optional stricter filter requires SOXX's last completed 15-minute
  change in the signal direction of at least 0.20%.

Missing prior close, completed five-minute bar, or 15-minute reference
fails closed. Same-bar prices are only read once the bar has completed.
No future regular close or >=5% outcome label influences the signal.
No more than the immediately preceding completed trading day is used
as a decision-time daily historical reference.

**Critical correction:** Unlike a filter applied only to the first
unconfirmed alert, the full replay continues evaluating every new
completed bar. Confirmation arriving later can qualify. The replay
cross-checks the 2,802 original first-signal timestamps for exact
agreement with the existing baseline.

## Full-year results: earliest completed-bar signal vs later confirmation

Counts are individual **stock-days**, separately by candidate family.
Do not add family rows together (one stock-day can appear in multiple
families). A "nonmajor signal" denotes a day not closing +/-5%, not
necessarily a bad trade.

| Candidate | Unfiltered: alerts / major hits / nonmajor | SOXX+breadth: alerts / major hits / nonmajor | Hypothetical mean advantage to 14:00 ET, baseline -> filtered |
| --- | --- | --- | --- |
| Up, previous close | 514 / 225 / 289 | **423 / 203 / 220** | +0.0172% -> **+0.0873%** |
| Up, intraday low | 895 / 212 / 683 | **515 / 190 / 325** | -0.1580% -> **-0.0945%** |
| Down, previous close | 531 / 187 / 344 | **440 / 172 / 268** | -0.0575 pp -> **+0.0340 pp** |
| Down, intraday high | 862 / 176 / 686 | **516 / 160 / 356** | -0.0501 pp -> **+0.1357 pp** |

**Sensitivity/false alarms:** Down-from-high confirmation detected
**160 of 209** >=5% decliners (76.6%), vs 176/209 (84.2%) unfiltered,
while reducing signals on non-5%-down stock-days from 686 to 356
(48.1% fewer). Up-from-close confirmation detected **203 of 254**
>=5% gainers (79.9%), vs 225/254 (88.6%) unfiltered, while reducing
non-5%-up signals from 289 to 220 (23.9% fewer).

**Warning timeliness:** Of 516 confirmed down-from-high warnings, 86
occurred *after* the first unfiltered warning, with an average delay
across all confirmed signals of **5.53 minutes**; 75 confirmed warnings
were on eventual >=5% loss days **before the stock itself fell 5% from
the previous close**. For previous-close upside, 32 confirmations were
later than the original; average delay 3.72 minutes and 73 eventual
>=5% up days detected before the stock had risen 5%.

**No fill claims:** Price-proxy eligibility for down-from-high was
510/516 modeled next-bar opens with a 30-bp limit envelope.
For up-from-close it was 420/422 scorable next-bar opens. Neither
ratio is an exchange fill rate. No contemporaneous NBBO, displayed
size, order-routing latency, or partial fill data were evaluated.

## Rolling earlier versus later period

Use the pre-existing research split: **through 2026-08-31** (earlier)
versus **2026-09-01 onward** (later). Thresholds above were defined
a priori in this experiment, not chosen by tuning later outcomes.

| Confirmed family | Earlier major hits; mean proxy advantage | Later major hits; mean proxy advantage |
| --- | --- | --- |
| Up from close | 182/231; +0.1827% | **21/23; -0.5358%** |
| Down from high | 130/160; +0.0603 pp | 30/49; +0.6683 pp |

A positive all-year modeled result is **not** sufficient evidence
for an automatic entry/exit: the later-period long entries are still
negative, and many declines remain undetected or detected too late.
An unconfirmed alert may also be useful for an isolated stock-specific
catalyst; a strict sector veto has substantial missed-move cost.

## What the model measures — and what it does not

Modeled next-five-minute OPEN is a price scenario, not an executable
bid or ask. The prior replay assumes 15 bp adverse execution and a
30 bp bounded limit. For a limit ineligible by this one next-open
scenario, the trade is treated as unfilled, rather than assuming a
future bar high/low would fill it. Results compare exits with a
hypothetical 14:00 mark, not actual broker fills or next-open risk.

The historical files lack full 52-week BOATS bid/ask depth, reliable
synchronized futures/news/earnings timestamps, venue trading hours and
V1 matched fills. Those are explicit blockers for real execution
comparisons, verified stop replacement and premarket/evening alert
causality; no claims of those results are made here.

## Validation and next research

The replay matched the existing baseline on **2,802 first-event
timestamps**. **46 targeted plus existing offline research tests
passed** at research checkout, including new tests for missing
quotes/closes, no next-bar leakage, cross-family up/down signals,
correct half-of-peers threshold and later re-confirmation.
Continue with timestamped SIP/BOATS NBBO quote replay, held-stock
PAPER shadow measurements and paired comparisons of early exits,
holding and regained upside. No order-routing changes to V1.
