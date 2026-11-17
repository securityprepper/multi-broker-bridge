# Live collector diagnosis — November 17, 2026

Live Gateway socket 4001 authenticates successfully, separate from Paper4002. Account values and account-scoped reqPositionsMulti complete; the general reqPositions request times out for this session. Live scoped results match AMAT5 and VRT5. Replacing the global position request fixes that collection stage.

The collector now uses account-scoped position requests and matching completion IDs. Six offline checks pass. Broker order-write methods, global cancel, exercise and auto-binding are explicitly refused. Error classification distinguishes the actual error code from request IDs and timestamps.

Actual service readback after the fix: COLLECTION_FAILED, failed_stage ALL_OPEN_ORDERS, position_records2, codes2104/2107/2158 (informational farm status). reqAllOpenOrders still never completes. A separately tested reqOpenOrders receives code321: API interface currently in Read-Only mode. These observations do not prove that switching off Read-Only would fix the all-orders timeout. No Gateway security settings changed, no order binding or order mutation performed, no restart/logout.

Account-scoped executions also failed to complete in the diagnostic. Complete snapshots must not be published as all-clear without order/execution completion. Keep the dashboard's incomplete coverage state. Session reconnect/legacy protocol tests did not resolve the all-orders timeout. Switching to FIX is not appropriate for the current TWS API implementation.
