# November 11, 2026 — all-source Alpaca PAPER rapid-exit reconciliation (read-only)

## Boundary / evidence

America/Chicago run, 2026-11-11 ~16:34–16:39 CST. Trusted holiday gate on www3 was verified **unpaused**, revision 2, America/Chicago coverage through 2036-10-25, next refresh 2026-11-13 16:13 CST, strictly future at inspection. Research-only: **zero broker orders submitted**. No active V1/PAPER/LIVE source, service, risk configuration, stop, timer, Gateway, or broker order changed.

Ran existing isolated **GET-only** `securityprepper-paper-inventory-readonly.service` (GET account, positions, orders, market clock) and `trading-sector-paper-fill-audit.service` (GET order and FILL activities), then independently read the 2026-11-09–11-11 systemd journals and the active source `multi_broker_bridge/auto_paper.py`, `trend.py`, and `paper_rebound_runner.py`. The broker inventory was recorded at **2026-11-11T22:34:46Z**. It covered one authenticated Alpaca PAPER account and the order-history window starting 2026-11-08T22:34:46Z (124 broker orders, <500 cap; broker claimed complete for that request). It is **not** evidence that other credentials/PAPER accounts were enumerated. The exporter intentionally omits raw account ID, order UUID, and fill activity UUID; source-separated historical per-account completeness requires those to be exported in a redacted/verifiable research-safe form.

The **independent FILL activity** audit fetched 270 actual broker FILL activity rows since 2026-11-09 00:00Z and joined them by broker **order UUID** against 124 broker orders: **237** activities mapped to MBB, **33** to FDR, **0 unknown** in this bounded sample. This is **270 activities**, not 270 orders or round trips. The separate order inventory contained **120 filled orders** (102 MBB + 18 FDR), plus four canceled MBB orders. Each filled buy was matched against its corresponding filled sell in the same observed account, symbol, strategy prefix, and session: **60 order-level round trips** (51 MBB, 9 FDR), 0 unpaired at this snapshot. Actual fill-average gross MBB P&L = **-$161.12**, precisely agreeing with the independent activity audit. FDR filled-order average gross P&L = **-$118.22**. Total **-$279.34 gross PAPER**; 14/60 profitable round trips. Fee/market-data-cost net P&L has **not** been established. Partial fill timestamps can differ from order-level final `filled_at`; sub-minute holding duration requires activity-level per-lot event matching, not just paired order timestamps.

## Session and rapid-exit accounting

| Day CT | Source | Closed pairs | Positive gross | Gross realized PAPER P&L |
|---|---:|---:|---:|---:|
| 2026-11-09 | MBB | 31 | 6 | -$134.66 |
| 2026-11-09 | FDR | 9 | 0 | -$118.22 |
| 2026-11-10 | MBB | 13 | 5 | -$31.89 |
| 2026-11-11 | MBB | 7 | 3 | +$5.43 |
| **Total** | | **60** | **14** | **-$279.34** |

Using elapsed time from *final order fill* to *final exit order fill*, inclusive cutoff:

| Maximum hold | All source cohorts | MBB only | Actual gross P&L for included pairs |
|---|---:|---:|---:|
| 2 min | 4/60 | 4/51 | -$18.07 |
| 5 min | 13/60 | 13/51 | -$76.34 |
| 10 min | 22/60 | 22/51 | -$128.76 |
| 30 min | 47/60 | 38/51 | -$275.37 |

These are **cumulative**, not additive buckets. 38/51 MBB pairs (74.5%) closed within 30 minutes; 22/51 (43.1%) within 10 minutes. Only 1 of the 22 MBB pairs closed within 10 minutes had a positive actual gross fill P&L. Do not treat these 60 correlated three-session trades as 60 independent validation days.

## What is causally known about exits

**FDR: the exact exit scheduler is verified.** The Nov 9 read-only `trading-five-day-rebound-paper.service` journal at 07:30:12 CT recorded **seven** `PREOPEN_EXIT_REQUEST` actions and **two** `NO_FRESH_EXIT_QUOTE` events. INTC's sell became an explicit preopen exit request at **07:32:12** after quote availability recovered; WDC remained `NO_FRESH_EXIT_QUOTE` until **07:37:12**, when `PREOPEN_EXIT_REQUEST:WDC` was issued. Broker FILL evidence confirms seven sells at 07:30:13–14, INTC at 07:32:14, and WDC at 07:37:13. Thus **all nine FDR sells were scheduled 08:30 ET preopen exit management**, *not* MBB's 1% profit target / 1m trailing / two falling bars. All nine closed at a loss, -$118.22 aggregate. Current FDR new entries remain paused. `PREOPEN_EXIT_REQUEST` was only an intent; the independent broker FILLED status establishes actual sales.

**MBB: three forced exits are directly supported.** Filled order `type=market` at **13:40:31–34 CT**: XOM Nov 9 (-$4.74), COP Nov 10 (+$8.68), and NET Nov 10 (+$4.41), matching the mandatory flat window. The other **48 MBB sell orders are `limit`**, but the **actual reason for each is not persisted** by the installed `auto_paper.run` journal emitter. During the bounded period, 4,617 MBB scan records contained 4,326 `SCAN_COMPLETE` and 289 `PAPER_DAILY_EXIT_GUARD` records; 48 logged ordinary sell intents had **no reason field**. The current `trend.py` supports `LOSS_WATCH=-1%`, `PROFIT_TARGET=+1%`, `TRAIL_ENABLE=+0.5%`, `TRAIL_REVERSAL=-0.5%`, and two completed falling bars; premarket uses a separate +2% bid-profit rule except hard -2.5% emergency and eligible software peak stops. But reading the current implementation **does not prove which historical branch fired**: exact original decision outputs, historical persistent peak, entry timing, and verified as-of bid and completed bars would be required. **Reason for all 48 regular MBB limit exits = UNKNOWN**, not a guessed classification. The 289 exit-guard scans are *scan outcomes*, not 289 actual exits.

Read-only order-fill examples (fill-price difference is **not** the reason code): AMD Nov 9 MBB 07:35:43–07:37:42 (-$2.80, 1.98m); MCHP Nov 11 09:44:54–10:07:49 (+$8.09, 22.92m); CARR 10:51:48–10:53:48 (-$1.44, 2.00m); KMI 12:51:55–12:56:59 (-$0.63, 5.07m). FDR AMD 07:06:14–07:30:14 (-$17.92) was a *separate strategy* and must not be merged with MBB AMD.

## Exact blockers and next research

1. **Original MBB exit-reason provenance absent**: need a *separately approved* immutable, redacted decision audit recording decision reason, first-seen/scan/quote-receipt timestamps, completed bar endpoints, source version, order client ID/UUID, and subsequent fill-activity UUIDs. Do not edit currently active V1 to obtain it in this research task.
2. **Per-fill/partial fill timing, account identification, and costs**: today's exporter has order-level averages and last-fill times but omits fill activity UUIDs and anonymized stable broker-account identifier; activity audit validates source counts/aggregate MBB P&L but does not publish a normalized per-fill/per-lot ledger. Missing one-minute historical SIP NBBO/BOATS samples for every executed trade precludes true quote-side fill-rate, MAE/MFE, and spread/slippage comparisons. No high/low touch = executable fill.
3. **Sample too short**: these are only **three distinct sessions**, versus the required **20+ independently evaluated dates**, and no strictly prospective held-out 20-day replay of 100 stop × target × hold arms exists. Hold-to-13:40, target, stop-first ambiguity, stop-first within the same minute, fees, and drawdown comparisons therefore **NOT VALIDATED**. Do not propose a stop/target/hold change on this sample.
4. **Negative-news clearance**: before any future researched BUY becomes eligible, verify same-issuer identity, SEC/issuer negative news and independent timestamped latest coverage, labeling `NEWS_CLEAR_ASOF`, `NEWS_UNKNOWN` or hard `MATERIAL_ADVERSE_VETO`. `NEWS_UNKNOWN` and mixed news are **not** BUY. This audit placed zero buys and recommended none.

**Disposition:** Exact scheduled FDR preopen-exit mechanism established, MBB short-hold losses established, MBB individual trigger attribution blocked by absent original reason fields. Keep research separate; no strategy release, no V1 monitor edits or broker orders. Only the Recommendation Audit is responsible for notifying newly closed recommendation-linked trades.
