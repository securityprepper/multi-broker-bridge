# November 10, 2026 — Forward-day directional evidence gate (V2 research only)

**No broker orders, V1 PAPER/LIVE edits, production database changes, timer changes, notifications or strategy activation.** All work below uses a read-only host journal/inventory inspection and an isolated offline statistical audit. The holiday cache remains previously validated unpaused (rev 2) strictly before November 13, 2026 at 16:13 CST absent calendar invalidation; this run did not change the gate.

## New bounded operational observations

Read-only `trading-sector-paper-executor.service` JSON scans from **06:30–07:29:59 CST on November 10** produced **72 scans**, of which two showed BUY_WATCH. Those two scans contained **eight repeated candidate appearances** across MU, SNDK, AVGO, INTC, ASML and MRVL: five `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY`, three `NO_FRESH_BID_ASK`, zero *reported orders*, and **31 retained tracking rows**. Candidate appearances are not independent executable missed trades. The known cross-session MBB lockout continues; no new origin for the November 9 03:18 AMD skip is established.

A separate authorized GET-only Alpaca PAPER inventory snapshot was independently verified at **07:28:43 CST**: **zero positions, zero open orders, complete recent-order coverage within the snapshot window**, 80 filled and four canceled recent orders. Its newest recorded created-at timestamp preceded November 10; no November 10 broker order was in that bounded snapshot. This is stronger than the executor's self-reported zero-order scans but not evidence of future orders or broker-wide provenance beyond the snapshot coverage. The exporter itself submits no orders.

## New research finding — 30 days is a floor, not proof of 80% precision

A point estimate of 80% directional hits is not itself an independently demonstrated 80% forward reliability guarantee. Because sector and time-slot variants are evaluated repeatedly, treating multiple slots on the same market day as independent trials would overstate evidence. The historical search tried **1,620 combinations**, so its reused chronological last-period metrics are explicitly NOT untouched validation.

The new pure offline source `research/v2_forward_day_evidence_gate_20261110.py` precommits an illustrative conservative **42-hypothesis** family (7 sectors × 3 forecast slots × 2 directions), uses a two-sided familywise 95% Bonferroni-adjusted Wilson lower bound, and always counts all eligible days, including abstentions. With this family, even **30/30 favorable independent days have a lower bound only ~74.06%**; **43/43** reach ~80.37%. At only 30 days, even an unadjusted 95% Wilson lower bound accepts 29/30 at ~83.3%, while the 42-way adjusted lower bound does not. This is a research screening rule, not an asserted regulatory or financial guarantee, and actual independent samples may be correlated across sectors.

A small earlier **reused historical** seven-sector earliest-signal audit already showed forward hit rates energy 18/48 (37.5%), financials 23/44 (52.3%), gold miners 28/47 (59.6%), healthcare 19/48 (39.6%), industrials 21/48 (43.8%), semiconductors 22/48 (45.8%) and software 24/48 (50%). These are **post-signal** marks but NOT new prospective observations, and no sector establishes 80% forward accuracy. Do not reuse the earlier 88–100% previous-close-to-close descriptive scores as predictions.

## Audit semantics and tested constraints

For every sector and specified horizon, the new gate selects only the **first sealed forecast per independently dated trading session**, never the best later update. It requires source bar completion <= forecast availability <= recorded seal < future evaluation <= independently recorded retrieval. Any missing day is an abstention; any movement under 5 basis points is separately classified as tiny, **not credited as a correct directional prediction**. It computes signed forward change from the **signal-time mark**, not yesterday's close, and distinguishes raw direction correctness from after-cost outcomes. Simulated 30bp costs are not real fills.

Attested quote/fee inputs are still external assertions: the source **does not authenticate** broker history, cryptographic sealing, quote executability, short eligibility, or calendar revision. It **never** returns trading permission or PAPER release GO. A per-sector UP/DOWN reliability result also cannot be certified from several forecasts on one session, and the seven sectors may share correlated shocks. Policy selection across the earlier 1,620 choices cannot be retroactively treated as independent; genuinely frozen candidates and 30+ new days per sector/side remain necessary.

**13 targeted offline tests passed** in isolated `/tmp/v2-research-run11-stats`, including no-lookahead ordering, earliest-signal-only, missing-day abstentions, tiny movements, 80% directional accuracy versus negative after-cost returns, repeated IDs, 42-family confidence, and fail-closed missing provenance. No host production checkout or divergent older V2 checkout was changed.

## Next checks

Read sealed Nov 10 forward-shadow observations only **after 08:35:25 CST** and independently verify their creation/journal timestamps; score future 15m/60m/13:40 CT outcomes only **after** each horizon. Use actual quote snapshots/fees and broker fill/order UUID chain evidence before any PAPER release consideration. Operational MBB new-session rearm still needs independent PAPER-only authorization, real Percona cross-writer testing and verified position ownership. Do not clear yesterday's tracked rows, interfere with mandatory exits, or touch IBKR Gateway. Keep 13:15 CT entry stop, 13:40 flat, 14:00 verification, holiday rules, restricted LIVE and quiet low-false-alert policy unchanged.
