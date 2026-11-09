# V2 gold / gold-miners leading-price precision and downside test — November 9, 2026

**RESEARCH ONLY — zero orders. Do not modify V1 PAPER, LIVE, broker orders, root timers, holiday gates or broker safety services.**

## Inputs, time boundaries and scope

Read-only actual split-adjusted **Alpaca SIP 5-minute trade bars** for GLD, GDX, GDXJ, NEM, AEM, KGC downloaded November 9, 2026 from November 3, 2025 through November 6, 2026. Companion BOATS **trade-bar** files also available. They contain **no timestamped NBBO bid/ask quote/depth records** and cannot verify executable limit fills or after-hours quotes. GLD is a traded ETF proxy for gold, **not** spot gold or futures. Gold miners can diverge from gold because of equity-market, cost, currency and issuer risks. **November 9 intraday bars were not in the downloaded sample**, so do not describe today's miner advance as a validated setup.

The study audits **1,263** completed miner stock-days, **1,243** with at least five *strictly earlier completed regular sessions* per stock (and gold). Five miner names: GDX, GDXJ, NEM, AEM, KGC. Outcome-only >=3% positive/negative daily close-to-close **or** open-to-close labels: **254 major up** and **227 major down** stock-days. 252 complete GDX+miner sector sessions: **132 positive, 114 negative, 6 mixed** (positive/negative = GDX final sign agrees with at least 3/5 miner final signs; mixed otherwise). These definitions differ from semiconductor's 118/83/49 cohort.

Signals observe only completed bars by **09:25 or 09:45 ET** and previous close/prior five *completed* dates. Four a-priori candidate conditions tested *both directions*, with a **0.25% GLD move from previous close**, **0.40% GDX move**, and/or >=2 of NEM/AEM/KGC moving >=0.40% in the same direction: GLD only, miner breadth only, GLD+GDX, GLD+GDX+miner breadth. For 09:25 decisions use **09:35 ET next-bar opening mark** for hypothetical entry/exit. For 09:45 use 09:50. Outcomes: price at 14:00 opening and subsequent regular opening with 30-bp/60-bp assumed adverse round-trip friction. Bar opening prices are **NOT demonstrated bid/ask executable fills**. No same-day outcome or future bar is used to produce a signal.

Use the pre-existing **earlier through Aug 31 / later Sep 1 through Nov 6, 2026** comparison. The hypotheses were fixed before evaluating later data, but study design itself is exploratory and does not establish independent cross-sector validation.

## Profitability — all covered miners together

| 09:25 ET long selection | Earlier: count, net 30bp win rate, mean net to 14:00 | Later: count, win rate, mean |
| --- | --- | --- |
| Unconditional miner buy at 09:35 | 1,000, **41.0%**, **-0.381%** | 240, **42.5%**, **-0.294%** |
| GLD >=+0.25% alone | 467, **41.5%**, **-0.450%** | 110, **40.9%**, **-0.335%** |
| GDX+2/3 miner breadth >=+0.40% | 425, **42.6%**, **-0.394%** | 90, **42.2%**, **-0.245%** |
| GLD AND GDX AND 2/3 miner breadth | 395, **40.5%**, **-0.437%** | 85, **38.8%**, **-0.360%** |

The strongest-looking later result from the separate **09:45 GLD-only** candidate was merely **+0.0016%** mean after the 30-bp assumed cost, with **43.5%** profitable on 85 stock-signals / 17 independent days; earlier it was **-0.554%**. No candidate demonstrated an 80% after-cost winning rate, and gold confirmation was not a reliable stand-alone miner purchase predictor. Most apparent sample size is correlated positions on the same mining day.

For the 09:25 gold+miner-breadth **UP** candidate, full-year 156/254 >=+3% final-day stock-move hits with **324 signals on nonmajor-up days**; later **22/32 major winners** detected with **63 nonmajor signals**, but the later portfolio-day buying signal still lost **-0.360%** mean by 14:00. Signal **recall is not precision or trade P&L**. Earliest qualifying major-up warning: **2025-11-10 09:25 ET**.

## Downside warnings — high recall but costly early exits

09:25 **GLD+GDX+miner breadth DOWN** warnings: **159/227** major-down stock-days and **211 nonmajor-down warnings** (370 warnings), earliest qualifying major-down warning **December 2, 2025, 09:25 ET**. In the *later* sample: **40/46** major-down days detected, **35 other warnings**. However, **30/40** severe signals were already on >=3% gap-down openings; only **10/40** were warned before the candidate miner had already declined 3% relative to previous close at the signal price.

The later signals had only **30.7% positive hypothetical early-sell benefit versus a 14:00 sale** and averaged **-0.516 percentage points** with 30bp assumed friction. Compared instead with holding until **the following regular opening**, 70 later stock-day signals across 14 independent dates showed only **28.6% positive early-sell benefit** and **-0.407 pp** mean. Earlier next-open advantage also negative (**-0.325 pp**). **No automated miner sell rule is justified.**

**Important misses across the complete cohort:** KGC closed **-11.586% on September 24, 2026**, when GLD at 09:25 was only **-0.196%** (the -0.25% gold gate failed despite miner breadth confirming weakness). On **March 13, 2026**, GDX and KGC closed about **-6%** while GLD at 09:25 was **+0.597%**; a gold-only directional model would have been misleading. Miner warnings must not be vetoed solely by gold direction. Full daily audit includes all significant winners and losers, even untriggered days, and marks which predicate failed.

## Data integrity and execution limits

BOATS **trade bars** observed: GLD 22,002; GDX 15,127; GDXJ 4,795; NEM 10,434; AEM 1,395; KGC 3,357. These do not provide a cross-market executable gold-miner NBBO history. Intraday ZIP price marks, partial fills, displayed size, overnight eligibility, routing latency, economic-calendar and timestamped issuer/futures/news inputs remain missing from this study. Do **not** interpret hypothetical bars as fills. Matched V1 PAPER fills are not present. The sampled dates end Nov 6, so no conclusion can be claimed about Nov 9 trades or P&L.

## Reproduction

Run on isolated research host (not production checkout), with SIP 5-minute inputs in the expected six `<SYMBOL>_sip.json` filenames and BOATS `<SYMBOL>_boats.json` under a sibling directory. These inputs were read-only:

```bash
python3 -m research.v2_gold_miner_preopen_lead --data-dir /tmp/v2-run15-sector-precision-work/alpaca_sip --output /tmp/gold_miner_preopen_v2.json
python3 -m research.v2_gold_miner_overlay_summary --result /tmp/gold_miner_preopen_v2.json
python3 -m unittest -v research.test_v2_gold_miner_preopen_lead
```

Results JSON includes all **16** combinations (2 decision clocks × 4 filters × 2 directions), OOS splits and next-opening comparisons. Automatically emitted `.events.json` and `.audit.json` cover each modeled event and each completed miner stock-day, respectively. **10 targeted causality tests passed**. All work is V2 research only; V1 production and divergent local research worktree untouched.

**Decision:** No gold-miner PAPER orders or emergency sell execution enabled. Next: timestamped gold futures/spot and verified SIP/BOATS bid/ask quotes, stricter quality-vs-recall scoring, actual PAPER execution readbacks, and independent rolling walk-forward sector calibration.
