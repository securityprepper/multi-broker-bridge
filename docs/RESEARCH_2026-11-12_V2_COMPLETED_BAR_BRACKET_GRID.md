# 2026-11-12 — Exact Alpaca PAPER rapid-exit cohort: causal 1m bracket-grid research (NO GO)

## Scope and evidence
- Research ONLY; one previously authenticated PAPER account, source cohorts MBB (51 completed) and FDR (9 completed); 60 actual completed broker-filled round trips on **three distinct Chicago trading dates, 2026-11-09 through 2026-11-11**. 120 filled broker order UUIDs and 270 individual fill-activity UUID records had previously been reconciled 1:1 to those 60 lots; this audit never treats an accepted order as a fill.
- A new GET-only PAPER audit on 2026-11-12 before the regular session returned **124 total broker orders** again (120 filled plus four canceled), with **zero orders submitted** by the audit. No new completed account sample was established.
- Historical actual realized fill-price P/L: **-$279.34 gross**, not after commissions. MBB 51/-$161.12; FDR 9/-$118.22. These realized values MUST NOT be compared as if they shared the model's incomplete subset.

## New replay
The offline script evaluates 100 combinations per source cohort and all-cohort view: target 0.5%, 1%, 1.5%, 2%; stop 0.5%, 1%, 1.5%, 2%, 2.5%; minimum ordinary hold 0, 5, 10, 15, 30 minutes. A 2.5% completed-close emergency risk exception is never deferred by a minimum hold. The mandatory 13:40 **America/Chicago** flat limit is applied in all scenarios. No stop, native bracket, source trading file, broker route, timer, or risk gate was altered.

Time ordering is strict: start with broker-verified filled entry; discard the incomplete bar containing the entry; read only *completed* subsequent 1-minute SIP trade-bar closes; identify possible threshold signals after that completion; model an exit at the **next minute's OPEN mark**, never at the trigger bar's high/low, with a 30-basis-point illustrative friction deduction. An uninterrupted one-minute sequence is mandatory up to the simulated exit; gaps or missing next opens are UNKNOWN, never filled with later hindsight. An intrabar high/low touching targets is **not** considered an actual executable profit. Intrabar target/stop ordering is not independently observable; source records lack full historical NBBO and some quotes are stale. The exercise is **not** an executable broker-native stop-first bracket simulation. Unchanged emergency protection cannot be verified from trade bars alone.

## Selected predeclared 1% target / 1% stop reference comparisons

| Minimum hold | Scorable mark proxies / actual 60 | Mark-model winning / scorable | Sum after *assumed* 30bp, USD | Unknown |
|---|---:|---:|---:|---:|
| 0 min | 42/60 | 19/42 | -$227.49 | 18 |
| 5 min | 42/60 | 19/42 | -$227.49 | 18 |
| 10 min | 42/60 | 19/42 | -$246.22 | 18 |
| 15 min | 41/60 | 20/41 | -$172.68 | 19 |
| 30 min | 41/60 | 22/41 | -$88.83 | 19 |

The 2% target / 2.5% stop anchor gave **22/40 positive mark proxies**, summed +$88.68 after illustrative 30bp, but 20/60 paths were UNKNOWN. Its worst modeled individual after-friction return was -2.95387%, and one path's post-entry observed low excursion reached -3.89016%. This outcome is selected as a **risk illustration, not a recommendation**; the missing 20 trades, quote spreads, true stop fills and fees can reverse its apparent advantage.

Across the 100 combinations, 40–50 of 60 round trips were scorable depending on parameters. **All 100 combinations have missing/unknown paths and zero independently verified executable alternative exit fills.** An apparent positive sum for a subset of modeled minute-open price marks is not a broker trade result or a profitable strategy. The 30-minute group had only 40–43 scorable marks per variant. Separate MBB/FDR 1%/1%/10-minute anchors were 18/35 and 1/7 positive after illustrative friction, respectively; both have unknown paths.

## GO / data decisions
- **NO GO:** only 3 distinct brokerage trading days, not the required >=20 independent days and a genuinely untouched holdout. Repeated historical threshold selection has contaminated the sample; no 80% predictive precision or after-fee edge is established.
- Historical SIP trade bars do not establish executable bid/ask or native stop fill ordering. Prior audited strict quotes qualify just 62/120 filled legs and 13/60 paired round trips; additional quote-width GETs did not add qualifying <=1.5-second quotes. Actual commission records and many causal exit reasons are still UNKNOWN (48 ordinary MBB sale journals carry no reason).
- The dominant rapid-exit trigger remains **UNKNOWN**; this replay does not assign simulated close-signals to actual broker sell UUIDs. Three identified 13:40 forced closes remain separately verified.
- Do not run an automatic sale, purchase, PAPER/LIVE order or release from this research. Recommendation-linked trade notification remains exclusively in Recommendation Audit. Continue accumulating 20+ truly independent sessions, immutable decisions/exit reasons, valid quote paths and independent paper-fill readbacks before proposing changes.

Reproduce with `research/v2_bracket_grid_completed_20261112.py` against the preverified local private research ledger; run `tests/test_v2_bracket_grid_completed_20261112.py` offline (12 passing). No credential values or private UUIDs are published. The JSON aggregate includes only sanitized cohort counts and illustrative summaries.