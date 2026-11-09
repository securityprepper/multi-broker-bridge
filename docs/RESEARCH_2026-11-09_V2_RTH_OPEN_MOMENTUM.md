# V2 rising-sector regular-session momentum, two-sided daily outcomes — 2026-11-09

**Research only. No PAPER or LIVE orders, broker connections, V1 modules, host timers, or strategy activation.**

## Research question
Can we detect and capture substantial *regular-session* semiconductor gains using information observable **after the 09:30 ET open**, independent of previous-close or premarket trend? Does waiting for a 15-minute confirmation reduce false buys? How do stricter estimated execution costs change modeled profits?

Use the same previously audited split-adjusted **52-week Alpaca SIP 5-minute OHLC** history, AMD/MU/SNDK/NVDA/AVGO/WDC/TSM/INTC/SOXX, **2025-11-10–2026-11-06**, **2,244 stock-days**, **254 >=5% close-to-close gainers**, **209 >=5% decliners**, and the pre-existing 250 sector sessions (**118 positive, 83 negative, 49 mixed**).

At **each** completed five-minute bar, compare completed target stock and SOXX closing marks with each respective 09:30 regular-session opening print. Require **SOXX >=+0.5%, stock >=+1.0%, and >=half other semiconductor peers >=+0.25%** relative to their own regular-session opening prints. The three variants differ only in the last eligible checkpoint or additional completed 15-minute momentum:

* `early_1030`: 09:35–10:30 ET.
* `through_1300`: 09:35–13:00 ET.
* `recent15_1300`: 09:50–13:00 ET, additionally SOXX +0.2% and stock +0.4% versus completed bars 15 minutes earlier.

No end-of-day +/-5% labels, future closes, following opening, next bar or target-day prior-five data influence the signal. The preceding five completed sector close-to-close steps are descriptive context only.

## New gain-side coverage and measured costs

| Model | Signals / >=5% gainers detected out of 254 | Nonmajor-up signals | >=5% down days also signaled | Mean next-bar-to-14:00 modeled return, 15 bp friction/side | Mean same proxy, 30 bp friction/side |
|---|---:|---:|---:|---:|---:|
| Through 10:30 | **697 / 150** | 547 | 40 | **+0.1344%** | **-0.0643%** |
| Through 13:00 | **899 / 188** | 711 | 42 | +0.0508% | -0.1148% |
| 15-minute momentum through 13:00 | **757 / 175** | 582 | 34 | -0.1303% | -0.1759% |

Extending coverage to 13:00 found **38 additional >=5% close-to-close winners** compared with the 10:30 cutoff, but issued **164 additional nonmajor-gainer signals**. A 15-minute momentum requirement removed some warnings and excluded some losing days, but **did not improve mean modeled same-day profit**.

These numbers are stock-day classification and next-five-minute **opening-mark eligibility scenarios**, NOT verified paper fills or actual trading returns. A 30 bp limit-buy envelope measured from the observed completed close is used; if a costed next-bar mark exceeds the limit, the strategy is scored as **no entry**, not a future fictitious fill. Of 697 early signals, **688** were price-eligible under 15 bp and only **377** under 30 bp adverse per-side price allowance. This is a sensitivity stress test, *not a real execution probability*. Securities with earnings, news or sparse liquidity may have much worse actual fills.

## Crucial later-period failure

| Model | Early period modeled mean to 14:00 | Sep.–Nov. 2026 mean to 14:00 | Later major winners caught / 23 | Later signals |
|---|---:|---:|---:|---:|
| Through 10:30 | +0.2461% | **-0.4818%** | 11 | 107 |
| Through 13:00 | +0.1586% | **-0.4657%** | 15 | 155 |
| 15-minute momentum | -0.0377% | **-0.5845%** | 13 | 128 |

**No version is reliably profitable in the later period** even before verified quote spreads, queue priority, order rejections or partial fills. Applying the 15-minute filter retrospectively does not cure the failed opportunity-side exit.

The modeled mean for the 10:30 setup across independent **signal days** is **-0.0410%**, compared with the +0.1344% signal-weighted mean. Related stocks frequently alert together; independent-trade assumptions would overstate confidence. Early/later is a retrospective period split, **not prospective out-of-sample validation**. Also, extending 13:00 signals can leave too little time before a 14:00 sell, making postentry friction material.

## Opportunity versus risk; research implication
The opening-to-current continuation signal detects rising stocks that premarket breadth alone can miss, including stocks recovering from preopen weakness. However, **40** early-to-10:30 continuation buys occurred on stock-days that later finished >=5% down, and its later-sample result was negative. Do **not** treat a rising sector as proof an individual stock will rise until the 14:00 exit.

We should test earlier profits/exit timing rather than simply tighten the entry, and use independent sectors plus contemporaneous catalysts rather than selecting thresholds to fit the observed historical winners. Compare to matched V1 PAPER executions only after obtaining actual V1 fill data.

The previous-five-completed-session SOXX history (<=-5% versus others) did not rescue the 10:30 candidate: 185 complete-history signals on weak-sector histories averaged **+0.0601%**, versus **+0.1384%** on other histories, modeled to 14:00; those are in-sample regime descriptions, not live filters.

## Replication and blockers
Script `research/v2_rth_open_momentum.py`, tests `research/test_v2_rth_open_momentum.py`, structured data `docs/RESEARCH_2026-11-09_V2_RTH_OPEN_MOMENTUM_RESULTS.json`.

`python3 -m research.v2_rth_open_momentum --output /tmp/v2-rth-momentum.json`

**126 isolated V2 research tests passed** in the run8 scratch checkout (103 previous + 12 first-hour sensitivity + 11 current). No production or divergent research checkout was touched; input datasets only read.

The historical files still do not provide complete 52-week synchronized SIP NBBO/bid-ask sizes, overnight BOATS quote history, 1-minute full-year bars, timestamped futures, news/earnings, true broker order depth, or V1 matched fills. Therefore, **no confident conclusion about real fills, trading profitability, crash prevention or live V1 superiority is possible**.

## Action
Keep both strategy tracks in research. Do **not** auto-buy the signal. For the next study, add actual timestamped executable quote evidence and broaden to independently sourced non-semiconductor sectors, then compare causal first-hour trend exits and missed big winners versus a locked earlier-period baseline.