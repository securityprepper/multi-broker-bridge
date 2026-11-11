# 2026-11-11 01:30 CT — uncommissioned Alpaca PAPER recommendation router receipt-clock and last-moment cutoff release blockers

## Scope and verified host state

Read-only source inspection on `www3.securityprepper.com` of:
`/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/bridge.py`.

**The separate recommendation router timer is `disabled` and `inactive`.** This audit performed NO broker network requests, broker orders, service restarts, LIVE changes, timer edits, or production source changes. The currently running MBB PAPER quote-clock hotfix is a DIFFERENT executable and must not be treated as covering this separate router.

The cached trusted holiday state was validated as **unpaused, calendar revision 2, America/Chicago, covered through 2036-10-25, next refresh strictly by 2026-11-13 16:13 CST**, subject to explicit calendar invalidation.

## Release blocker A — fresh quotes falsely rejected against preflight-start clock

The inactive router `bridge.py::preflight(row,now,...)` performs GET account, GET positions, GET open orders and GET SIP `/quotes/latest` but checks freshness as `0 <= now - quote_timestamp <= MAX_QUOTE_AGE`, with `now` fixed at `process_once` start. The owner-approved MBB hotfix was NOT applied here.

**Actual installed Python module, fully synthetic/patched API reproducible test:** preflight started with clock `T`; quote timestamp `T + 4 s`, simulating a fresh quote produced while the GET was pending; otherwise valid Alpaca PAPER account/positions/orders, positive own-account risk proof, bid 100.04, ask 100.10, no other-broker dependency. The **installed router rejected `quote stale`** without making any real broker calls. This is a source-level false rejection; it does NOT establish a historical skipped executable fill.

Correct release logic: capture `quote_received_at = datetime.now(timezone.utc)` **immediately after GET**; enforce `0 <= quote_received_at - quote_timestamp <= 45 seconds`, keep noncrossed, positive finite and <=1% spread, account, buying power, own positions/orders, paper status, holiday, bracket protection, idempotency, order readback. Do not weaken time or spread limits or use historical as-if timestamps to claim current fills.

## Release blocker B — the 13:15 Chicago owner entry cutoff is not checked immediately before the POST

`bridge.py::process_once` captures `now` once at startup, checks `entry_window(now)`, then performs database read, recommendation preflight, account/position/order/quote GETs, claim insertion, intent update and commit, and finally `POST /v2/orders` with **no refreshed entry-window/cutoff check after the reservation**. `preflight(row, now,...)` uses the SAME original `now`; it is not a second fresh clock.

A scan that enters at **13:14:56 CT** and reaches broker POST at **13:15:03 CT** would pass those old checks even though the submission would violate the explicit **13:15 CT latest-entry limit**. This is a **code-path release safety weakness in a disabled router**, not evidence that such an order occurred.

Required separately reviewed release correction: at the FINAL boundary immediately before POST, recapture an authoritative aware UTC clock; recheck today's RTH/session/holiday and the strict `CT < 13:15` limit, recommendation expiry, and quote age relative to **submission** (refresh quote if needed). When after cutoff, do **not** POST; record a deterministic broker-NO-ORDER cutoff outcome that is distinct from `BROKER_SUBMISSION_UNKNOWN`, reconcile the existing reservation and same-broker idempotency/claim state safely; no automatic retry. Do not defer this until after POST or assume earlier preflight is still valid. Existing 13:40 CT flat remains mandatory.

## Independently implemented research-only enforcement prototypes

Published only to `securityprepper/multi-broker-bridge` branch `research/rebound-v2-conditional-exits`:
- `research/v2_recommendation_router_quote_receipt_clock_20261111.py`: pure receiving-broker quote-receipt verifier and post-reservation final submission-time guard; NO network, credentials, broker actions or order permissions.
- `tests/test_v2_recommendation_router_quote_receipt_clock_20261111.py`: **21 new offline tests passed** (correct post-GET timestamp, strict 45s/1% safety limits, future/crossed/NaN/spread/stale rejection, exactly 13:15 CT cutoff, late after reservation, quote expiry between preflight and submit, premaket/weekend exclusion, no orders).
- Combined with unrelated news receipt tests: **26 tests pass** in clean isolated research scratch. The production recommendation router's existing `test_cross_broker_optional.py` suite: **7/7 PASS** read-only, confirming latest owner directive that unavailable/stale/overlapping OTHER-broker data is an *advisory* and cannot block independently qualified Alpaca PAPER actions. Same-broker risk/inventory failures still block. No other broker requests precede basic qualification in this observed path.

## Unchanged and incomplete

Active Alpaca MBB V1 PAPER, FDR, live IBKR or Robinhood, existing broker orders, old production dirty checkout and all production timers/holiday/stop/flatten protections remain unchanged. The recommendation PAPER execution router remains uncommissioned, so **no strategy execution GO** or financial performance is implied. A distinct security/engineering release must apply and test fixes inside the separate inactive router before any commissioned PAPER order; test with simulated crossing and actual broker-side readback, never infer fills from market marks. Future reliability testing requires >20–30 untouched days and actual spread/fees.

Historical Nov9 03:18 AMD skip remains unresolved without old full diagnostic fields; no speculation.

No confirmed profitable forward after-cost strategy has been established by these source safety tests.
