# V2 two-sided as-of sell-timing and crash-warning opportunity-cost stress — 2026-11-09

**Research only.** No WebSocket broker connection, orders, V1 strategy changes, live monitors, holiday timers or production checkout modifications. Nothing in this study warrants automatic buys or sells.

## Data and causality

Replay the existing 52-week **split-adjusted Alpaca SIP five-minute OHLC** history of AMD, MU, SNDK, NVDA, AVGO, WDC, TSM, INTC and SOXX, covering **2,244 stock-days** from November 10, 2025 through November 6, 2026. The prior baseline has **250 sector sessions: 118 positive, 83 negative, 49 mixed**, and **254 close-to-close gains >=5% / 209 declines <=-5%**.

At the decision point, use ONLY the completed five-minute candle, previous completed regular-session close, and (where used) completed 09:15 ET sector snapshot. The owner's **2.5% total decline including at least 1 percentage point in the last 15 minutes** remains an overlapping, unchanged comparator. Realized closing labels, next-bar opening prints and following-day opening marks are **post-signal outcomes**, not live features. The study uses no same-day close in a signal and no future day in policy selection. It does not modify the prior-five-completed-day rule.

A hypothetical entry is price-eligible only if the next five-minute opening print plus 15 bp adverse buying friction stays within the completed signal closing mark +30 bp limit envelope. Bounded sell exits use an independently observed, later completed candle and a subsequent next-bar opening mark with 15 bp selling friction and a 30 bp sell-limit envelope. A price-ineligible sell is **unfilled** and remains marked through 14:00; it is not assumed to fill or reprice later. These assumptions are **not NBBO quotes, order-book liquidity, executable fills or measured latency**.

## Track 1 — Can exit timing rescue rising-sector buys?

The existing 09:35–10:30 ET SOXX +0.5%, stock +1%, half-of-peers +0.25% continuation signal had **697 stock-day signals**, detecting **150/254 major gainers** and appearing on **40 eventual >=5% losers**. Evaluate fixed 11:00, 12:00 and 13:00 exits, a 14:00 hold baseline, and fixed take-profit/stop-loss combinations (0.5%/-0.75%, 1.0%/-1.5%, stop-only -0.75%, take-profit-only 0.5%). Entries after a fixed exit time do not receive retrospective fills.

**Equal-weight across independent signal dates; percentage of modeled entry price after both execution-friction allowances:**

| Exit candidate | Through Aug 2026 | Sep–Nov 2026 | All |
|---|---:|---:|---:|
| Hold to 14:00 | +0.0860% | **-0.6568%** | -0.0410% |
| Fixed 13:00 | -0.0049% | -0.5429% | -0.0968% |
| Fixed 12:00 | -0.1245% | -0.5011% | -0.1888% |
| TP +1% / SL -1.5% | -0.2736% | -0.3585% | -0.2881% |

The **best policy selected exclusively from the earlier-period signal-day returns was HOLD to 14:00**. Locked without using later outcomes, it yielded **-0.6568% per signal-day** on the Sep–Nov evaluation set. Faster exits improved some later outcomes retrospectively but were worse in earlier history: choosing them from the later sample would be future leakage/overfitting.

An expanding monthly walk-forward additionally chose ONE strategy for each entire coming calendar month using only the preceding **120 calendar days of completed signal-day evidence**, minimum 15 independent days, with no test-month refitting. Across **415 eligible signals on 71 independent days**, its day-equal modeled mean was **-0.1416%**, worse than **-0.0760%** from holding the same entries to 14:00. Later period: -0.6045% versus -0.6568% baseline; still negative. A single good month cannot establish a stable improvement. The original 14:00 signal-weighted full-sample proxy (+0.1344%) differs from the day-equal mean (-0.0410%) due to highly correlated simultaneous sector trades. Do not treat stock signals as independent samples.

**Action:** no exit policy beats the baseline robustly; do not activate automatic buys. Next study should use actual quotes/BOATS to separate missed fills from true signal economics, and independent rising sectors for holdout validation.

## Track 2 — Which sell warnings protect next open, and what do false warnings cost?

Compare (a) strict previous-close 2.5% including 1pp/15m through 10:30 ET; (b) 08:30/09:15 ET SOXX+peer down-breadth snapshots; (c) 09:35–10:30 ET reversal of a qualifying bullish preopening SOXX+peer sector; (d) earliest valid preopening union; (e) earliest of all three. Each is evaluated on **every** stock-day, including nontriggers, and never uses closing severity to decide whether to alert.

| Rule | Major downs found / 209 | Warnings on nonmajor-down stock-days | Major up days incorrectly exposed to early selling | Mean hypothetical sell advantage vs next regular opening |
|---|---:|---:|---:|---:|
| Strict 2.5%/15m rule through 10:30 | 180 | 370 | 18 | -0.5514 pp |
| Preopen breadth snapshots | 143 | 474 | 11 | -0.4701 pp |
| Opening-sector reversal | 25 | 224 | 16 | +1.0592 pp |
| **Premarket union** | **155** | **519** | **22** | **-0.5397 pp** |
| **Premarket + first-hour union** | **200** | **806** | **37** | **-0.0824 pp** |

The all-window union misses **9** major decliners. Of 200 major declines warned, **166** first warned while the stock was still less than 5% below its previous close; the others were already at least 5% lower. It is a high-coverage **watch** tool, not a viable unconditional sell instruction: 806 warnings were on days that failed to close down 5%; among them 318 had favorable and 445 adverse modeled sell-versus-next-open outcomes (other cases were zero/unscorable). **Earliest severe-loss warning:** November 13, 2025 at **04:20 ET**. Major declines still missed by the combined first-hour strategy include **WDC -8.912% and AMD -7.8196% on November 20, 2025**, and SOXX/MU/SNDK on June 16, 2026.

The **premarket union** had 155/209 severe-down hits, **121** before the stock had already lost 5%, but 519 alerts on nonmajor-down stock-days. Across its alerts, modeled early selling versus the *following day's* regular open was **-0.5397 percentage points overall**, **-1.1237 pp** in the earlier period and **+1.1478 pp** in Sep–Nov: not stable enough to sell. Against the *same morning* 09:30 opening mark, the mean was only **+0.0023 pp**. Within the premarket union's 519 nonmajor-down warnings, **169** hypothetically benefited from early sale and **314** were worse off compared with holding to the next open; the rest were zero/unscorable. Thus, a severe-day classification alone understates the cost of false warnings.

Of **87 stock-days that opened down at least 5%**, the union produced a warning before 09:30 on all 87, but in **45** cases the stock had **already declined 5% at the warning**; just **21** had an eligible warning in the **preceding evening**. A preopen signal after a gap develops is *not evidence the preceding regular-session loss could have been prevented*. In thin overnight books an actual limit sell might not execute at all.

On November 2, 2026 the preopen union warned on **none** of AMD/INTC/MU/SNDK/WDC's severe declines. Opening sector reversals warned AMD/MU/SNDK/WDC at **09:40 ET**, and the strict rule warned INTC at **09:35 ET**. These are useful postopen warnings, not preceding-evening protection.

## Reproduction

New isolated source: `research/v2_locked_exit_policy_walkforward.py` and `research/v2_downside_early_sell_opportunity_cost.py`. Targeted tests: `research/test_v2_locked_exit_policy_walkforward.py` and `research/test_v2_downside_early_sell_opportunity_cost.py`. Structured summaries:
- `docs/RESEARCH_2026-11-09_V2_LOCKED_EXIT_WALKFORWARD_RESULTS.json`
- `docs/RESEARCH_2026-11-09_V2_DOWNSIDE_EARLY_SELL_RESULTS.json`

Commands (authorized read-only historical dataset input only):

`python3 -m research.v2_locked_exit_policy_walkforward --output /tmp/v2-run9-locked-exit-results.json`

`python3 -m research.v2_downside_early_sell_opportunity_cost --output /tmp/v2-run9-downside-results.json --audit-output /tmp/v2-run9-downside-audit.json`

The second script also generated a **2,244-row daily individual-stock audit** locally, including signal source/timestamp/mark, gap, close, whether major gain/loss and the next-regular-open counterfactual; rows include all nontriggers. The full audit is reproducible but not checked into Git to avoid unnecessary data duplication.

**143 research unit tests passed** in isolated scratch at `/tmp/v2-run9-locked-exit` (126 prior + 17 new). No production checkout, divergent local V2 research checkout, broker credentials, accounts, orders or V1 timers were touched.

## Material blockers

Full synchronized **SIP/NBBO bid/ask and size**, **BOATS historical quotes**, consolidated 1-minute overnight/RTH observations, point-in-time QQQ/SOXX/futures and earnings/news availability, independently sourced other sectors and matched V1 broker fills are not in the present replay inputs. Accordingly: no defensible **real fill probability**, causal preceding-evening news warning, cross-sector effectiveness, or actual P&L comparison to V1 can yet be reported.

**Do not activate V2 live feeds or automatic PAPER/LIVE orders based on these tests.**
