# V2 two-sided sector direction — locked later-date tests (2026-11-09)

**Research only. No PAPER or LIVE broker orders or production monitor modifications.**

## Definition and time integrity
Target = sector ETF prior *regular-session* close to target regular-session close. UP iff >0; DOWN iff <0. This is distinct from morning-open-to-close, strong-move magnitude, and from trading P&L. A model may ABSTAIN. Forecast time for the 10:00 ET five-minute bar is **10:05 ET or later**; it cannot be used at 10:00. 09:25 bars likewise cannot be used before 09:30. Data collected for this study ends November 6, 2026; the November 9 session is not a completed outcome in this test.

Data: prior existing split-adjusted 52-week Alpaca SIP five-minute trade-bar research inputs for SOXX and 8 semiconductor stocks, GDX/GLD/NEM/AEM/KGC, XLE/XOM/CVX, XLF/JPM/BAC, XLI/CAT/GE, XLV/UNH/LLY, IGV/MSFT/CRM. Gold and semis events reconstructed from individual as-of bars; the five other sectors' symmetric 10:00 signal candidates reconstructed from prior causal study's events and complete daily audit. Each sector used chronological first ~70% for selection and remaining 75–76 dates as **untouched for choosing thresholds in this analysis**. We compared multiple thresholds on the earlier sample; selection bias and repeated research on this same historical period remain significant caveats.

## Held-out accuracy: forecast after 10:05 ET

| Sector | Correct/all forecasts | UP correct | DOWN correct | Forecast coverage | Wilson 95% lower bound (overall) |
|---|---:|---:|---:|---:|---:|
| Semiconductors | 49/53 = 92.5% | 25/26 = 96.2% | 24/27 = 88.9% | 53/76 = 69.7% | 82.1% |
| Gold miners | 44/44 = 100% | 20/20 = 100% | 24/24 = 100% | 44/76 = 57.9% | 92.0% |
| Energy | 26/28 = 92.9% | 14/16 = 87.5% | 12/12 = 100% | 28/75 = 37.3% | 77.4% |
| Financials | 18/18 = 100% | 11/11 = 100% | 7/7 = 100% | 18/75 = 24.0% | 82.4% |
| Industrials | 24/27 = 88.9% | 11/12 = 91.7% | 13/15 = 86.7% | 27/75 = 36.0% | 71.9% |
| Healthcare | 22/23 = 95.7% | 14/15 = 93.3% | 8/8 = 100% | 23/75 = 30.7% | 79.0% |
| Software | 26/27 = 96.3% | 15/16 = 93.8% | 11/11 = 100% | 27/75 = 36.0% | 81.7% |

The no-signal days are excluded from accuracy but included in coverage. Small bearish samples imply wide uncertainty; the Wilson intervals are approximate, not guarantees.

## Earlier known-only benchmark
When allowed only information through the PREVIOUS session close, best earlier-selected momentum/reversal rules scored on later dates: semiconductor 53.3% overall (UP 60%, DOWN 47.5%), gold miners 42.7% (46.2%, 38.9%), energy 54.2% (57.4%, 48.0%), financials 46.7% (45.9%, 47.4%), industrials 54.8% (68.4%, 33.3%), healthcare 45.5% (39.1%, 48.8%), software 54.4% (52.8%, 56.2%). This confirms early information is not enough.

## Critically: Full-day direction correct != remaining trade profitable

Directional continuation after the signal in an ETF:
* Semiconductors: 27/53 continued favorably from 10:05 to 16:00 ET; only 20/53 had >0.30% favorable continuation before costs.
* Gold miners: 23/44 favorable continuation from 10:05 to 16:00; only 20/44 had >0.30%.
* Energy: 14/28 favorable from hypothetical 10:10 execution to 14:00, 10/28 >0.30%.
* Financials: 5/18 favorable, 2/18 >0.30%.
* Industrials: 13/27 favorable, 7/27 >0.30%.
* Healthcare: 9/23 favorable, 5/23 >0.30%.
* Software: 17/27 favorable, 11/27 >0.30%.

The later-horizon measurements differ (16:00 for SOXX/GDX, 14:00 for other ETF studies) and should not be ranked as comparable returns. These measures omit actual spread/market-impact/commissions, so a move >0.30% is NOT a verified profit. Accuracy can be inflated because moves were already underway by 10:05.

## Selected rules (training only, then locked)
* SOXX 10:05: sector ETF +/-1.0% from prior close; at least 3 of 8 semiconductor leaders same sign (threshold zero). Symmetric UP/DOWN, otherwise abstain.
* Gold miners 10:05: GDX +/-0.15%, all 3 NEM/AEM/KGC move >=0.70% same direction, and GLD >=0.10% same direction. Symmetric, otherwise abstain.
* Energy: XLE plus oil leaders 5-prior-session volatility-scaled breadth candidate.
* Financials: XLF plus JPM/BAC strong breadth.
* Industrials: XLI plus CAT/GE strong breadth.
* Healthcare: XLV plus UNH/LLY breadth.
* Software: IGV plus MSFT/CRM strong breadth.

The non-gold five-sector source evaluated its 10:00 ET candle and execution marks at 10:10; forecast is not usable at 10:00. Selected event files previously required a future 14:00 trade mark to include an event; audit completeness should be decoupled from future exit-bar availability before this can qualify as a real-time implementable predictor. The gold/semiconductor signals were evaluated directly from input bars without any future exit-price availability condition.

## Next validation before any emergency PAPER action
1. Validate a fully untouched subsequent month (not reused for strategy selection) or online forward-only shadow forecasts recorded **before** market close, separately for each sector and both directions.
2. Measure serious-move precision and lead time for sector-adjusted magnitude thresholds, including missed significant moves and false emergency signals (not merely correct daily sign).
3. For every signal store timestamp, confidence, prior-close mark, current move, and remaining close movement; evaluate reversals during the day and prior-evening predictions separately.
4. Obtain executable quotes and broker observed order states; validate contradictory exposure and existing exit safeguards. Exit opposing positions must be verified BEFORE proposing new PAPER entries; no broker activation via research.
5. Separate sector forecast (UP/DOWN/NO SIGNAL) from buy/exit timing and from position profitability. Do not turn a 10:05 direction report into a guaranteed profitable emergency trade.

## Research artifacts
Read-only result files on www3:
`/tmp/v2-direction-priorclose-run-20261109.json`,
`/tmp/v2-direction-10am-symmetric-20261109.json`,
`/tmp/v2-direction-semis-gold-intraday-20261109.json`,
`/tmp/v2-direction-followthrough-20261109.json`.

Unit-tested score module `research/v2_sector_direction_scoring.py`; `python -m unittest -v research.test_v2_sector_direction_scoring` (8 passed).
