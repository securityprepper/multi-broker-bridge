# V2 Research — 52-week delayed-entry sector anti-churn and one reentry stress (2026-11-09)

**RESEARCH ONLY. NO broker orders, release activation, Alpaca/IBKR mutations, V1 timer/monitor/strategy edits, or LIVE actions.** Validated holiday cache: unpaused revision 2 until **November 13, 2026 16:13 America/Chicago**, absent known calendar edit. This study uses completed history through November 6, not a partial November 9 closing outcome.

## What was tested and why this differs from 10:05 full-day sign accuracy

The desired target is **returns AFTER an actual as-of signal**, not already-observed close-to-close direction. This pass extends the earlier 20-session **one-minute** anti-churn study to 248 eligible sessions per sector using separate split-adjusted **Alpaca SIP five-minute TRADE bars** for all seven sectors. Six-sector peer bars and gold-miner spot-confirmation bars are from earlier 52-week research. A common, deliberately simple 09:35 ET candidate was used, not tuned to these outcomes:

* Use the **completed 09:30–09:35 ET five-minute candle** and strictly the prior **FIVE completed RTH session closes** to check sector ETF >=0.20% in sign direction, with at least two sector stocks >=0.20% same direction. Gold miners also require GLD >=0.10% same direction. Semis uses SOXX + any two of AMD/MU/SNDK; other sectors use 2 leader stocks, gold 3 leaders.
* First hypothetical stock entry at **09:40 ET OPEN**—a five-minute decision/execution delay, avoiding same-instant bar-close/open fills. Both UP and DOWN scenarios; DOWN assumes theoretically accessible short positions but has **no real borrow/short locate** evidence.
* Stop rules use a previously completed five-minute close, then one additional five-minute execution-delay buffer; next-next bar OPEN mark, no same-bar fills. All positions time-flat at **14:40 ET = 13:40 Chicago**, 20 minutes earlier than owner-approved 2pm Chicago latest flat.
* Compare hold (no intraday stop), tight five-minute joint stock/sector reversal, +/-1% target/stop, hard -1.5/-2.5/-4%, and a +1% arming level with **2.5 percentage-point trailing-from-best-close stop**. The latter is the earlier 20-day candidate being checked for stability.
* Report percent profitable and mean per filled-mark scenario **AFTER an illustrative 0.30 percentage-point round-trip cost**, plus 0.60 percentage-point stress. Neither is a measured bid/ask spread or matched actual broker fill. Measure day-equal averages, negative tail and trade count. The 70/30 date split is shown but has been researched repeatedly and is **not a fresh blind test**. The frozen candidate is retested **backward** on older history, not true chronological forward validation.

## Full-year 09:35 delayed entry → 13:40 Chicago hypothetical gross and after-cost performance

| Sector | Eligible days | Forecast days | Candidate stock positions | Hold profitable after 30bp | Hold mean net per stock | +1% arm / 2.5pp trail mean net | Tight 5m mean net |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semiconductors | 248 | 194 | 526 | 262/526 = **49.81%** | **+0.1166%** | **−0.1005%** | −0.2890% |
| Gold miners | 248 | 180 | 523 | 215/523 = 41.11% | **−0.2888%** | −0.2974% | −0.2239% |
| Energy | 248 | 186 | 372 | 123/372 = 33.06% | −0.4346% | −0.4322% | −0.3608% |
| Financials | 248 | 126 | 252 | 74/252 = 29.37% | −0.5359% | −0.5395% | −0.4383% |
| Industrials | 248 | 105 | 210 | 85/210 = 40.48% | −0.3620% | −0.3886% | −0.3814% |
| Healthcare | 248 | 99 | 198 | 93/198 = 46.97% | −0.2233% | −0.2238% | −0.2380% |
| Software | 248 | 107 | 214 | 97/214 = 45.33% | −0.2107% | −0.2124% | −0.3227% |

No strategy produces >=80% after-cost profitable-trade precision. Only semiconductor unconditional holding has slightly positive average after the 30bp **assumed** cost; at 60bp it becomes **−0.1834% per stock position**. Its mean is only **+0.0275% day-equal**, meaning concentration on favorable stock-days inflates its trade-equal mean. Worst held semiconductor position **−10.7403%** after 30bp and **52/526** held positions lost at least 4%. This is not an acceptable unconditional release safety profile.

### Does the 20-day trending/trailing improvement survive the larger sample?

**NO.** The earlier isolated 20-day one-minute sample showed +1%-armed/2.5pp trail average **+0.6856%** versus unconditional hold **+0.6361%** (54 entries). On **248 days of five-minute data**, the candidate falls to **−0.1005%** versus hold **+0.1166%** (526 entries). The later 75-day portion also underperformed (trail **+0.0115%** versus hold **+0.0901%** per trade). Semiconductors trailing reduced day-equal return by **0.2105 percentage points** relative to hold; day-cluster bootstrap exploratory 95% interval **[−0.3651, −0.0667] pp**. The tight 5m reversal similarly reduced day-equal returns by **0.3456 pp**, with illustrative interval **[−0.6813, −0.0119] pp**. No correction for repeated strategy testing or regime autocorrelation; not a definitive future estimate.

In the same **last 20 dates** the five-minute delayed-entry simulation returned hold **+0.8892%** versus trail **+0.8578%** net; it does NOT reproduce the modest 1m trail advantage even on that date range. One-minute and five-minute signals/exit sampling and price latency differ, so neither the raw difference nor its sign can be interpreted as a verified live edge.

## One same-day reentry after the five-minute tight stop

Causal confirmation: wait >=15 minutes after exit, observe a completed same-direction stock + SOXX bar both still >=0.2% vs previous close; execute 10 minutes after its bar start; one reentry maximum, finish by 13:40 Chicago. On the 248-day semiconductor sample, **526 first trades** became **982 total executions** (456 reentries). First-only tight policy mean **−0.2890%** per first trade; one-reentry per-original-position total mean **−0.4800%**, with **202/526 (38.4%)** positive original positions after both attempts. This is approximate fixed-notional return, not capital-matched realized P&L. Reentry increases turnover and modeled loss. **DO NOT enable reentry** based on this.

## Two-sided market and missed severe stock days

This rule is an **entry candidate**, not a valid preceding-evening emergency warning. Sector counts below are a strict classification where the sector ETF AND **all tested peers** end positive (UP), all negative (DOWN), else MIXED. They differ from older majority-breadth definitions.

| Sector | UP / DOWN / MIXED | >=5% UP stock-days; signaled | <=−5% DOWN stock-days; signaled |
|---|---|---|
| Semiconductors | 76 / 63 / 109 | 139; 113 | 106; 74 |
| Gold miners | 106 / 94 / 48 | 47; 43 | 43; 38 |
| Energy | 114 / 86 / 48 | 1; 1 | 1; 1 |
| Financials | 102 / 80 / 66 | 0; 0 | 1; 0 |
| Industrials | 84 / 71 / 93 | 11; 8 | 12; 5 |
| Healthcare | 55 / 71 / 122 | 7; 3 | 3; 0 |
| Software | 73 / 82 / 93 | 11; 6 | 7; 6 |

The early semiconductor breadth candidate signaled 113/139 major upside stocks (81.3% recall) and 74/106 major downside stocks (69.8% recall), missing **26 major winners and 32 major losers** already using the weak "by close" target. Among 526 chosen stock-days only 187 corresponded to a same-direction >=5% closing move; **339** had no such major same-direction close, so do not conflate high extreme-day recall with trade precision. A 09:35 warning cannot protect against an already occurred overnight gap. This study does not establish preceding-evening or next-regular-open exit benefit; see prior independent as-of alert research for those failures.

## Broker reconciliation and execution blockers

No new broker inventory or individual FILL UUID ledger was read in this replay. Prior broker-verified Nov 9 14:03 CST snapshot listed 62 completed MBB orders, 18 FDR orders, zero other order IDs and zero simultaneous paired filled exposure in eight common symbols. **The earlier 33 unmatched FILL activity events still lack exact activity UUID -> order UUID -> client-order-family mapping; do not claim they are all FDR or that there is no third writer.**

Missing for GO: full historical executable SIP/BOATS NBBO and short-locate/borrow data; matched V1 PAPER fills and individual FILL UUID ledger; synchronized prior-evening news/futures/earnings economic-event timestamps; true independent forward shadow results on untouched future dates. Do not compare historical trade-mark calculations to the real MBB Nov 9 −$129.92 loss as though they were realized alternative P&L.

## Files and reproducibility
* `research/v2_52week_delayed_anti_churn.py` — semiconductors 52-week causal and seven stop exit policies
* `research/v2_cross_sector_0935_risk_replay.py` — six other independently sourced sectors
* `research/v2_semi_52week_reentry_stress.py` — one-reentry at most, with cooloff and as-of reconfirmation
* `research/test_v2_52week_delayed_anti_churn.py` and `research/test_v2_semi_52week_reentry_stress.py` — **12/12 targeted offline tests passing**
* `research/results/v2_52week_seven_sector_0935_delayed_risk_2026-11-09.json` — all seven sector policy/70-30 splits/paired bootstrap summaries
* `research/results/v2_52week_seven_sector_0935_daily_audit_2026-11-09.csv` — every qualifying **1,736 sector-day**, with daily market state, signal/abstention, major up/down peer counts, and modeled holding versus stop results.
* `research/results/v2_semi_52week_0935_reentry_2026-11-09.json` — distinct tickets and per-original-position impact
* Expanded event ledgers in isolated host scratch `/tmp/v2-run23-full-year-anti-churn/` not linked to any broker runtime.

**Decision: NO V2 auto-trading release or V1 change.** The new 52-week evidence rejects promoting the previously attractive 20-day trailing stop. Earlier market context, economically meaningful after-cost prospective edge, realistic execution risk and true out-of-sample validation must be established before a separately approved PAPER-only trial.
