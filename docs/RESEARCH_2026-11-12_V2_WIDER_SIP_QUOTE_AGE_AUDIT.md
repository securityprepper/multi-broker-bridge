# November 12, 2026 — wider SIP quote-window recovery for 25 Alpaca PAPER fill legs

**Research-only, one broker-verified PAPER account. No broker orders, live source, timers, or protective stops changed.** Follow-up to [the exact 5-second null-quote finding](RESEARCH_2026-11-12_V2_NULL_SIP_QUOTE_ROWS_ROOT_CAUSE.md). Existing bounded source has 60 completed round trips (51 MBB, 9 FDR) on November 9–11, 2026; 120 actual filled BUY/SELL order legs. Only the **25/120** legs for which prior 5-second SIP GET returned `quotes:null` were re-queried; broader account and historical completeness is **not established**.

## New verified GET-only evidence

Each request ended at the **actual broker final-fill timestamp** and used original SIP quote timestamps only at/before that fill. First retrieve the preceding **120 seconds**, fully resolving pagination; where no rows appeared, try **300 seconds**. Check positive/noncrossed bid/ask, both displayed sizes, <=1% spread, and latest quote age. No high/low bar touch or broker acceptance was substituted for an actual fill.

| Previously null 5-second legs | Result |
| --- | ---: |
| Retrieved at least one **historical valid displayed** quote in longer window | **19/25** |
| Last valid quote **older than 1.5s** at actual fill | **19/19** (ages **6.727–39.292 seconds**, median **9.517s**) |
| Historical quote had best-side displayed size >= actual fill quantity | **19/19** (size presence **not** queue/fill proof) |
| No returned quote rows even with 300-second lookback | **6/25**, all premarket |
| New <=1.5-second qualifying legs recovered | **0/25** |

Premarket: **9/15** had an older usable-shaped SIP quote, **6/15** lacked quote rows for 300 seconds. At/after 08:30 Chicago: **10/10** had older quotes and **0/10** a <=1.5s qualifying quote. The six no-row cases are both entry and exit legs for premarket **MRVL, MU, and SNDK**. The 19 older quote spreads had a **0.1131% median**, but were too stale to claim a broker-executable counterfactual.

This distinguishes **quote sparsity at subsecond decision time** from the previous erroneous blanket TypeError label. It is not evidence of zero actual liquidity, broker failure, missing BOATS depth, or hypothetical tradable profit. **Strict SIP quote evidence remains 62/120 filled legs and 13/60 completed round trips with qualifying quotes on both sides**; there is no change to actual PAPER gross/after-fee results or source attribution.

## Evidence and safety

Read-only authenticated historical quote queries, private result at `/tmp/v2-run15-sip-quote-width-20261112/quote_width_private.json`. Reproducible GET-only collector `research/v2_sip_quote_width_getonly_20261112.py`, with **11/11 isolated offline tests passed** (`tests/test_v2_sip_quote_width_20261112.py`). No credentials or account/order UUIDs are published. No broker submissions or live changes.

**No exit-rule GO.** Historical decision reasons remain unknown for **48/48 ordinary MBB exit orders**, executable continuous bid/ask paths and fees remain incomplete, and this actual-fill sample spans only **three** trading dates versus the mandated 20+ untouched trading days. Next research must capture source-versioned decision-reason IDs at fill time and full timestamped SIP/BOATS quote availability; wider stale quotes cannot validate minimum holds, trailing exits, stop/target grids or a profitable trading change. Recommendation Audit remains the sole recommendation-closed-trade notifier.
