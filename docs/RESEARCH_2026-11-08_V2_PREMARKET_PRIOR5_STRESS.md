# V2 premarket weakness warnings by completed prior-five SOXX context — 2026-11-08

**Research only. No broker orders, production or V1 changes.**

## Method and causal boundaries

Extend the existing previous-regular-close **2.5% total decline INCLUDING at
least 1% decline over 15 minutes** early-warning replay. Evaluate only completed
five-minute Alpaca split-adjusted SIP bars in eligible previous-evening
(16:00–20:00 ET on the adjacent day) or same-day premarket
(04:00–09:15 ET) windows. An overnight weekend is not mistaken for the
preceding evening. A first-hour regular-session warning is **not** a preopen
warning.

At each event, the signal sees only the prior regular close and completed
bar observations available by that time; no eventual close-to-close loss,
following regular opening price, or later price bar is a decision input.
A five-day SOXX context is calculated from **six consecutive completed
regular-session closes ending yesterday**, never today's closing price.
Missing or nonfinite closes fail closed. Weak means SOXX's prior five
session-to-session returns totaled **at most -5%**; all else is "not weak."

Outcome metrics compare a hypothetical *next five-minute opening price*
after the warning (15 bp adverse markdown) with the same day's regular
09:30 ET opening price. This measures a **price-mark difference**, not
a price at which an eligible limit sell could actually have filled.
Unknown execution size/depth, overnight spreads, broker order state and
partial fills can reverse the apparent difference. No automatic sell
recommendation follows.

## Sample and preopen warning coverage

Across the nine semiconductor symbols, the original audit had 2,244
stock-days. **2,148** have complete prior-five SOXX history and **206** of
those close at least **5% lower** than their previous regular close.

| Group | Stock-days | Severe down days | Preopen warnings | Severe down hits | Nonmajor warnings | Severe caught before already down 5% | Average price-mark benefit vs waiting to 09:30 |
|---|---:|---:|---:|---:|---:|---:|---:|
| All with complete prior five | 2,148 | 206 | 201 | **79** | 122 | **48** | **-0.4403 pp** |
| SOXX prior five <=-5% | 423 | 44 | 62 | 15 | 47 | 14 | **-2.3674 pp** |
| SOXX prior five >-5% | 1,725 | 162 | 139 | 64 | 75 | 34 | **+0.4255 pp** |

Thus **127 of 206** major-loss stock-days had no qualifying preopen
warning. Suppressing weak-SOXX context would exclude **47 warnings on
nonmajor days**, but also remove **15 warnings on actual major-loss
days**, including **14** warnings occurring before a 5% decline.

### Earlier/later sensitivity — price-mark benefit, not fills

| Prior-five SOXX group | Through August 31, 2026: warnings / severe hits / mean mark benefit | Sept. 1–Nov. 6, 2026: warnings / severe hits / mean mark benefit |
|---|---|---|
| Weak (<=-5%) | 43 / 7 / **-3.2559 pp** | 19 / 8 / **-0.3567 pp** |
| Not weak | 121 / 54 / **+0.2758 pp** | 18 / 10 / **+1.4238 pp** |

The weak-context premarket warning was costly in both periods on this
price-mark measure, unlike the **intraday high-reversal** model where
weak-context performance reversed later. Those are **different
alert families and different exit time horizons**, and they must not
be merged into one rule.

The first preopen warning in this **complete-prior-five subset** was
2025-11-18 at 08:00 ET. This is not the earliest historical alert in
the full sample: initial days were excluded by design.

## Conclusion and next checks

Premarket warning recall is materially incomplete (**79/206 = 38.3%**
of major-loss stock-days; only 48 early enough to precede a 5% loss).
The simple prior-five SOXX filter is promising as a **research
stratifier**, not as an unconditional veto: ignoring it would sacrifice
warnings on genuine major losses. Confirmed early exits still require
actual executable SIP/BOATS bid/ask quotes, limit eligibility, venue
hours, realistic partial fills, matched V1 holdings and independent
cross-sector forward testing. Synchronized timestamped news/futures
and complete BOATS overnight data remain unavailable in this replay.

### Reproduce

- `python3 -m research.v2_premarket_prior5_stress --output /tmp/v2_premarket_prior5.json`
- `python3 -m unittest -q research.test_v2_premarket_prior5_stress`
- Input files: `/tmp/semis_52wk_5min_sip_adjusted.json`,
  `/tmp/semis_peers_52wk_5min_adjusted.json`, and
  `/tmp/semis_52weeks_alpaca_daily.json`.
- 37 combined targeted checks (two new modules plus relevant existing
  as-of/next-open/phase tests) passed on the authorized research host.
- Structured outputs committed at
  `docs/RESEARCH_2026-11-08_V2_PREMARKET_PRIOR5_RESULTS.json`.

The analysis only read historical datasets and wrote new isolated
research files. The production checkout and divergent local V2 checkout
were not modified, and no broker orders were sent.
