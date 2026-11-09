# V2 PAPER streaming synthetic-stop — offline prototype (2026-11-08)

## Scope and activation
Research-only decision model in `research/v2_streaming_synthetic_stop.py`.
No WebSocket connection, credential use, broker submission, scheduling, deployment,
or V1 import is included. **Not suitable for unattended trading.** Existing
PAPER and LIVE services, broker positions and orders must remain unchanged.

## Initial reference behavior
* An observer supplies verified previous regular-session close, verified long
  available shares, permission for the current session, no existing sell order,
  the latest bid/ask and a quote exactly 15 minutes prior (within five seconds).
* Require bid <= 97.5% of the prior regular close, and a decline in bid of at least
  1% of the prior close in 15 minutes. The recent 1 percentage point is **inside**
  the total 2.5% move, not additional to it.
* Propose (never submit) a sell limit 0.15% below the observed bid, rounded down
  to a cent. This is **not** a guaranteed fill and the 0.15% buffer is an
  experimental input, not validated trading performance.
* Suppress proposals with a quote older than two seconds, crossed/overwide
  spread, missing exact 15-minute history, unverified long quantity, unknown
  open sell orders, duplicate event time, unsupported session or >5% total
  decline (do not chase severe gaps blindly).
* Permit one outstanding intent; uncertain and partial order statuses lock
  subsequent proposals. No automatic cancel/replace or repricing is implemented.
  Cancel/reject only rearms on verified no-open-sell reconciliation.

## What remains before PAPER order execution
1. Authenticate and ingest Alpaca SIP quote/trade WebSocket and BOATS overnight
   stream as applicable, with sequence and heartbeat checks, feed permissions,
   clock skew and reconnect backfill.
2. Verify brokerage account, held **long available** quantity, open/unknown sell
   orders and exact market-session permission before every proposed order.
3. Validate order characteristics per session, tick sizes, buying power and
   API restrictions, including extended-hours eligible limit order time-in-force.
4. Implement durable idempotent client_order_ids and broker readback, crash
   recovery, partial fill handling, safe explicit cancellation/replacement and
   locking through network uncertainty.
5. Replay actual timestamped consolidated bid/ask samples, including sparse
   overnight liquidity and missing/stale data. Compare standard stops, this
   synthetic stop, and adaptive-limit variants with empirical latency,
   spread, partial-fill and unfilled-order costs. Analyze every positive and
   negative stock/sector day, both triggered and missed opportunities.
6. Run isolated PAPER shadow mode (log-only), then actual PAPER orders only after
   a separate deployment review and explicit execution authorization. No LIVE
   enablement follows from PAPER acceptance.

## Test command
`python -m unittest -v research.test_v2_streaming_synthetic_stop`

The initial targeted checks cover both overlapping threshold boundaries,
unverified holdings/session, quote staleness/crossed spread, deep gap, duplicate
event times, unknown/partial outcome suppression, and cancellation reconciliation.

These unit tests do **not** establish exchange routing latency, real fills, or
the strategy's trading profitability.
