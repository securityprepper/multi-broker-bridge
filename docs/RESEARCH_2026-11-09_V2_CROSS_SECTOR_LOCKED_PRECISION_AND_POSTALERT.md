# V2 research: cross-sector precision-first walk-forward and semiconductor 30-minute follow-through
**2026-11-09 (America/Chicago)** — RESEARCH ONLY; zero orders. V1 PAPER/LIVE, production checkouts, broker orders and safety gates unchanged.

## Scope and controls
Official Alpaca read-only GET of 52-week split-adjusted SIP **5-minute trade bars** for XLE/XOM/CVX, XLF/JPM/BAC, XLI/CAT/GE, XLV/UNH/LLY and IGV/MSFT/CRM, through **November 6, 2026**. Gold comparison uses earlier downloaded GLD/GDX/GDXJ/NEM/AEM/KGC 52-week SIP bars. Signals use latest **COMPLETED** 5-minute bars only: 09:25 and 10:00 ET, with modeled entry at 09:35 and 10:10 respectively; rank at most one ETF or strongest as-of peer per sector-day. Five prior **completed RTH sessions** are used for directional regime and volatility scaling, never the current-day close. The later period (**September 1–November 6**) is an untouched evaluation for candidate selection: choose by **earlier** mean net return, subject to at least 30 independent trading days, >0 after-cost mean, >=80% after-cost win rate and Wilson 95% lower bound >=60%. **Cash/no-trade is a legitimate candidate.** Report rejected earlier-best policies as *shadow* policies, not recommendations.

Modeled results use next eligible opening PRICE MARK, 14:00 price mark and 15/30/60bp assumed round-trip costs; **these are not broker fills, executable NBBO/BOATS quotes, overnight limit fill evidence or short-borrow feasibility.** Outcomes and next-open prices are labels only, never inputs to signal eligibility. Full day-by-day event, stock and sector audits generated on isolated www3 scratch; the reproducible scripts and compact all-candidate result JSON are committed here.

## Track 1 — gold/miner entry admission
252 fully evaluated gold-miner sector sessions: **132 positive / 114 negative / 6 mixed** by GDX+peer direction. Tested 48 predeclared one-position-per-day combinations (42 emitted trades), including gold alone, miners alone, gold+miners, recent 15-minute acceleration, prior-five trends, relative strength and 10:00 regular-opening continuation. **No model earned an earlier-period positive net mean AND 80% win rate.** Accordingly the *train-locked deployable choice was NO TRADE*, not the statistically best of bad policies.

The **rejected** best earlier-model shadow, **10:00 miner breadth -> strongest producer**, had **85 earlier independent days**, after-30bp win rate **43.53%** and modeled mean **-0.2907%**. On the **17** later trade days it won **6/17 = 35.29%**, Wilson lower bound **17.31%**, modeled mean **-0.0994%** to 14:00 and **-0.1049%** to the next opening. It happened to catch **6/7** later GDX major-up dates (>=3% outcome), but this recall did NOT make the purchases profitable. The superficially favorable **posthoc** 10:00 gold-only best-producer variant had a later **+0.0549% mean on 17 days** while earlier mean was **-0.5498%**—not a valid out-of-sample selection. No miner PAPER order GO.

## Track 1 extension — five independent additional sectors
Complete comparison cohort: **248 dates per sector**, with **3,725 daily individual-stock/ETF outcomes**, including no-signal days and **585 dynamically defined major rises / 520 major declines** among all 15 symbols. Dynamic *OUTCOME LABEL* for each instrument: absolute prior-close-to-close **or** RTH open-close move at least max(1%, 1.5 × mean of the four fully completed day-to-day returns across five prior RTH closes). Not comparable with the >=5% semiconductor or >=3% miner outcome definitions. For sector status, *positive* requires ETF and both peers to finish positive; *negative* all negative; otherwise mixed.

| Sector / ETF / peers | Positive | Negative | Mixed | Earlier-best shadow policy; later signals, after-30bp wins, mean to14 |
|---|---:|---:|---:|---|
| Energy / XLE XOM CVX | 114 | 86 | 48 | 10:00 prior5-scaled UP strongest peer; **11**, **45.45%**, **-0.1346%** |
| Financials / XLF JPM BAC | 102 | 80 | 66 | 09:25 sector-only DOWN ETF; **14**, **14.29%**, **-0.5133%** |
| Industrials / XLI CAT GE | 84 | 71 | 93 | 10:00 breadth DOWN strongest peer; **13**, **53.85%**, **-0.2630%** |
| Healthcare / XLV UNH LLY | 55 | 71 | 122 | 09:25 sector-only DOWN strongest peer; **12**, **41.67%**, **-0.4558%** |
| Software / IGV MSFT CRM | 73 | 82 | 93 | 09:25 breadth UP strongest peer; **10**, **30.00%**, **-0.9816%** |

No sector passed the earlier-only **80%-after-cost precision** admission gate: **NO TRADE selected across all five sectors**. Later best-shadow alert coverage/false alarms: energy 5 major-up / 6 nonmajor; financials 0 major-down /14 nonmajor; industrials 4 major-down /9 nonmajor; healthcare 2 major-down /10 nonmajor; software 5 major-up /5 nonmajor. Not a universal forecast; short leg is strictly a price-mark scenario with no borrow data. Later major ETF outcomes separately counted for each sector in structured JSON.

## Track 2 — semiconductor: what follows an emergency warning?
Read-only replay of **2,235** strictly comparable stock-days / **209** >=5% prior-close-to-close losses, with original SOXX+peer confirmation. Thresholds 2/2.5/3% TOTAL decline **including** 1/1.5/2 percentage-point decline over last completed 15m (never add the thresholds). First qualifying alert per symbol-day, then look **forward** to 30-minute price mark and next RTH open as outcome-only. Every no-signal severe stock-day remains in denominator.

| Later (Sep–Nov), 49 serious decline stock-days | Major detected | Other warnings | True major before already -5% | Hypothetical beneficial SELL vs next +30m | Average SELL advantage vs next +30m (30bp cost) |
|---|---:|---:|---:|---:|---:|
| -2.5% total / -1.0pp in 15m | **39/49** | **58** | 23 | **35/97 (36.1%)** | **-0.3169pp** |
| -2.5% total / -1.5pp in 15m | 28/49 | 25 | 13 | 25/53 (47.2%) | +0.1525pp |
| -3.0% total / -1.5pp in 15m | 28/49 | 21 | 13 | 23/49 (46.9%) | +0.1743pp |

For -2.5%/-1.0pp, **only 16/97** later warnings were followed by another >=1% drop within the next 30 minutes; on average an immediate hypothetical sell lost **0.0321pp** vs holding until the next RTH open and improved outcomes on only **40.2%** of warning events. The stricter -1.5pp criterion looked better against a 30-minute hold but worsened vs **next RTH opening**: **-0.1874pp** on average and **43.4%** beneficial, while missing **21/49** severe down stock-days. It also lost **early preopening warning availability**: earliest full-year major-warning moved from **Nov 13, 2025 08:35 ET** to **09:35 ET** under -1.5pp momentum. A next-30-minute improvement in an exploratory sample is **not** sufficient to justify automatic stops or sells. Confirm false positives against *future trade profitability*, not only final-session major-loss labels.

Prior semiconductor sector baseline (different close-only cohort) remains **118 positive / 83 negative / 49 mixed** sessions.

## Data limits and action
This study newly resolves independent sector SIP history previously absent, **not** executable cross-sector 52-week NBBO or BOATS quotes. Missing synchronized issuer earnings/guidance/news, gold futures vs spot, QQQ/futures/currency/economic-calendar time stamps, minute-by-minute quote depth, partial fills, short-sale availability and matched V1 PAPER execution logs. Data end **2026-11-06**, so today Nov 9 is not a completed historical outcome. Full no-signal event audits remain on read-only isolated host at `/tmp/v2-run17-gold-confirmed-replay`, `/tmp/v2-run17-cross-sector-precision` and `/tmp/v2-run17-semi-followthrough`; these are temporary host files, not durable production storage. No claims of actual 80% profitable trading, no new PAPER activation, no V1 changes.

### Reproduction
Run from a clean V2 research checkout on the authorized host (not dirty `/opt` or divergent `/tmp/v2-trading-strategy-research`) with the recorded local SIP inputs:
```bash
python3 -m research.v2_gold_confirmed_walkforward --output /tmp/v2_gold_locked.json
python3 -m research.v2_cross_sector_confirmed_walkforward --output /tmp/v2_sector_locked.json
python3 -m research.v2_semi_postalert_followthrough --output /tmp/v2_semi_30min.json
python3 -m unittest -v research.test_v2_gold_confirmed_walkforward research.test_v2_cross_sector_confirmed_walkforward research.test_v2_semi_postalert_followthrough
```
**24 new targeted offline tests passed (9+9+6)**. Tests of signal causality/selection/no-trade guards are not real-fill validation. Existing BOATS trade BARS for gold do not establish executable bids/asks. Preserve all live monitors, holiday gates, broker accounts/orders and existing PAPER exit paths.
