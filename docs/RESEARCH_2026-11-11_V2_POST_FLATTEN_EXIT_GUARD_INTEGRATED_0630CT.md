# 2026-11-11 06:30–06:43 America/Chicago — integrated research-only receiving-PAPER post-flatten readback

## Scope and holiday gate
Holiday cache was read from authorized www3. Revision **2**, `paused=false`, `timezone=America/Chicago`, `calendar_coverage_ok=true`, `calendar_coverage_through=2036-10-25`, and `next_check_at=2026-11-13T16:13:00-06:00`. Current time Nov 11 06:30–06:43 CST is strictly before boundary; no edit or invalidation observed, so no holiday refresh, timer/schedule change, or pause triggered.

The only source modifications were in the canonical isolated **research/rebound-v2-conditional-exits** branch of `securityprepper/multi-broker-bridge`. Active production V1, Alpaca PAPER broker/order state, IBKR LIVE/Gateway, FDR and all timers remain untouched. No authenticated broker request, order submission, cancellation, position modification, Pushover notification, or LIVE request was made.

## Integration completed
**Prior defect already identified:** the disabled recommendation router's `readback_flatten` interpreted a fully filled forced SELL as `FLATTEN_FILLED` without reading receiving-Alpaca PAPER account positions and working orders. Offline research helper existed, but its rules were not connected to the bridge source.

Now `recommendation_paper_bridge/exit_guard.py` on the isolated research branch:
- Requires canonical recommendation/client order ID, explicitly passed recommendation symbol, matching broker order symbol, side SELL, broker order ID, and exact finite Decimal intended/filled quantity.
- After a **fully filled** SELL, independently GETs current **same receiving Alpaca PAPER** `/v2/positions` and `/v2/orders?status=open&limit=500`, following a verified PAPER account GET. Rejects malformed/incomplete inventory and 500+ working-order boundary.
- Returns **`CRITICAL_FLATTEN_RESIDUAL_POSITION`** for any remaining same-symbol position and **`CRITICAL_FLATTEN_WORKING_ORDER`** for any still-working same-symbol order.
- For a zero-position/zero-working-order snapshot returns **`FLATTEN_SELL_FILLED_FLAT_SNAPSHOT_UNLOCKED`**, NOT `FLATTEN_FILLED`. The receiving broker snapshot is only an instant of observation: because the disabled router still has no proven shared-account lock with MBB/FDR and no atomic cross-writer ownership, this cannot certify the account remains flat.
- Keeps canceled/expired/rejected and partially/unfilled order statuses distinct. Does **not** issue or retry any sell, or alter an existing broker order.

Updated legacy exit tests to expect the safe bounded status, and added 14 fake-broker account readback tests for residual positions, open orders, wrong account/symbol/side, partially filled, canceled and malformed/overflow/nonfinite observations. **72 tests passed**: 58 existing recommendation-paper tests and 14 new integrated tests. `git diff --check` clean before publication.

Commits on canonical isolated research branch: `2f9d4d5417974c3c37bff753e1a2885938116554` (guard), `d1f16d7fdab682385e5bbb5a24ea002312ed1a4f` (legacy tests), and `8d831aa82022953c70ec922376cf9f2b10c88b0c` (14 new tests). Validated in separate isolated scratch `/tmp/v2-strategy-run9-20261111`; production dirty checkout and older divergent research workspace not modified.

## Current research coverage / next requirements
- Three sealed first prospective Nov10 before-outcome shadow snapshots exist at 09:35, 09:45 and 10:05 Eastern, from the 23-symbol/7-sector GET-only forward shadow timer, with zero broker requests/orders and no future outcomes embedded. This is **one prospective day**, not 20–30 untouched forward days, and **not** statistically reliable evidence for after-cost directional prediction. Do not re-parameterize retired price-chase/GLD-lag/stop variants based on one day.
- The recommendation PAPER router is still **disabled/uncommissioned**. Its separate all-source receiving-broker daily-loss/exposure budget, shared cross-strategy lock/reservation, final cutoff, quote receipt clock, broker-native protected-entry readback and post-flatten lock remain outstanding release requirements. Research branch source integration above does not certify commissioning and does not grant PAPER order permission.
- The historical 2023–26 analyst/issuer dataset lacks original immutable first-observed timestamps and matched numerical independent analyst estimate revisions; therefore no statistically verified after-fee issuer-guidance/revision edge is established. Do not infer original event availability from publisher `created_at` or revised archive headlines.
- Full 20+ prospective days, real broker bid/ask/latency/fill/no-fill/commission, and separately commissioned shared-lock end-to-end tests are needed before any new strategy GO.
- No other-broker positions/orders are required to assess an Alpaca PAPER recommendation. Any optional cross-broker holdings are informational only and are **not** execution gates. This research run deliberately did not inspect IBKR or Robinhood positions/orders.

No novel profitable strategy or new critical broker incident was verified in this run. No predictive/price-only push notification warranted.
