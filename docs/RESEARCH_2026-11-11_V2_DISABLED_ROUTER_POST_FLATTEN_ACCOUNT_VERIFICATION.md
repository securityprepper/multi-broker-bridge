# November 11 2026, 05:31–05:39 CST — disabled recommendation PAPER router false-flat release blocker

## Confirmed by source inspection and offline reproduction
The currently **disabled** `recommendation_paper_bridge/exit_guard.py` function `readback_flatten` checks only the deterministic client ID and the forced **SELL order's** own status / `filled_qty`. If that order is `filled`, it returns `{"status":"FLATTEN_FILLED"}` **without inspecting independently fresh receiving-Alpaca PAPER account positions or open orders**. Its caller `run_guard_once` persists that status without a post-sell portfolio/order readback. This creates a **false-account-flat reporting risk**: a forced SELL can fill while an unrelated or later same-symbol position or working bracket/buy order remains. It can therefore certify an exit order as filled but cannot certify the account has no residual same-symbol exposure by the 13:40 Chicago liquidation goal or 14:00 verification. No actual residual position or trading loss is established.

Reproduced using the existing readback function and simulated PAPER account/order response; it returned `FLATTEN_FILLED` without ever requesting /v2/positions or open orders. No broker network calls were made by the test.

## Isolated research-only corrective component
New `research/v2_post_flatten_broker_account_readback_20261111.py` requires, for a **bounded readback claim**:
- exact receiving PAPER account identity and canonical flatten client ID;
- filled full quantity on an identifiable same-symbol SELL;
- complete, fresh, post-sell same-broker position and working-order GET results;
- exclusive per-account shared lock attestation, to prevent a participating concurrent writer from changing the portfolio during verification;
- **no residual same-symbol position record** and **no outstanding same-symbol order** (including buy, stop, target).
- reject partial fills, wrong accounts, stale/pre-fill snapshots, missing order IDs, incomplete coverage, and unexpected broker values.
- output `BOUNDED_RECEIVING_PAPER_ACCOUNT_FLAT_VERIFIED` only on the complete conjunction; otherwise `UNKNOWN_...` or `FLATTEN_ORDER_FILLED_BUT_POSITION_STILL_REPORTED` / `...WORKING_ORDER_REMAINS`. None authorizes another SELL or any BUY.

The conditions are **not yet integrated into** `recommendation_paper_bridge/exit_guard.py` and do not constitute broker-level atomic position/order guarantees. External writers can act after readback. A future commissioned implementation requires repeated late-session verification, reconciliation with broker fill UUIDs, account-scoped locking, explicit alert/escalation on position/order remaining, and independent PAPER release tests. An order's own `filled` is evidence of the SELL only, **not evidence that the receiving account is flat**.

## Tests
`tests/test_v2_post_flatten_account_readback_20261111.py`: **16 tests passed** on www3 isolated canonical clone. Reproduction, positive and negative snapshots, account mismatch, same-symbol remaining shares, pending stop and pending BUY, stale/pre-sell inventory, incomplete/overfull inventory, missing lock, partial/NaN fill, origin mismatch, unrelated holdings. Combined 70 tests passed including existing exit/reconcile and per-account reservation stress suites. No broker calls or orders.

## Scoped status
Active V1 Alpaca PAPER, IBKR/LIVE, all broker orders, stop/flat/holiday timers, existing active source and user notifications **unchanged**. Recommendation PAPER router remains **disabled**, so this is an **uncommissioned release blocker**, not a demonstrated deployed incident. No after-fee profitable research strategy, prospective multi-day test or new PAPER trading authority was established. Continue prior owner source-scoped risk gates and no-cross-broker gating rules.
