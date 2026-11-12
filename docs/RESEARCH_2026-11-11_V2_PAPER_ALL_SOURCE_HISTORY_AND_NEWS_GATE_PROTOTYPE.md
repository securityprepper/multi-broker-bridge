# November 11, 2026 — PAPER broker coverage and as-of negative-news readiness

Research-only. No orders, V1/PAPER/LIVE source changes, timers, stops, holidays or IBKR operations.

## Independent broker history readback

At approximately 21:40 America/Chicago, authenticated Alpaca PAPER GET account verified ACTIVE and unblocked; a GET order-history request with after=2026-10-12T00:00:00Z returned a COMPLETE single page of 125 orders: 120 FILLED orders and five nonfilled. Verified filled-order client prefixes: 102 MBB, 18 FDR, zero OTHER. Filled orders appear on only THREE Chicago trading dates: November 9 (80), 10 (26), 11 (14). These are **orders, not distinct round trips or fill activity events**; the previously paired bounded cohort remains 60 round trips. Do not count matched recommendation trades again, infer absence of another Alpaca PAPER account, or claim history before October 12.

Therefore the current account cannot support an authentic 20-day **broker-filled** rapid-exit validation using this history. Earlier 48 MBB limit exits still lack their original captured decision-reason-to-fill join; do not assign triggers from price patterns. First prospective sessions after the already installed two-bar suppression have not yet occurred. Current PAPER auto_paper journals accepted SELL order ID with exit_signal_reason, but accepted is not filled. Future order UUID/fill UUID joins are required.

## New V2 research-only clearance reducer

Published research/v2_paper_negative_news_asof_gate_20261111.py with 15 synthetic offline tests, all PASS on authorized www3 isolated scratch. It requires issuer identity (ticker, exchange, exact ten-digit CIK), independent issuer/SEC/licensed-news coverage with genuine publication and first-observed timestamps, complete adverse-event category coverage, and order-time freshness. Missing/stale/incomplete sources => NEWS_UNKNOWN; verified material adverse => NEWS_MATERIAL_ADVERSE; pending/contradictory evidence or unclear issuer => NEWS_REVIEW_WATCH_ONLY. Only complete synthetic verified coverage and no adverse evidence yields NEWS_CLEAR_ASOF. News first observed after a historical decision may not retroactively veto that decision. The tester itself does not fetch news, submit orders, prove actual clearance, attest a licensed source, or authorize execution.

**Precise blocker still open:** active Alpaca PAPER auto_paper BUY path has no mandatory independently sourced NEWS_CLEAR_ASOF preflight. A protected genuine publisher, source provenance verification and separately approved PAPER-only entry integration are needed before any claim of compliance. No LIVE changes, and protective exits and 13:40 flatten must remain independent of news availability. The historical 3,141-item headlines archive lacks original first-observed data and is not a clearance provider. No current symbol was cleared.

Holiday cache validated unpaused, revision 2, America/Chicago, valid strictly before November 13 16:13 CST absent edit. Unprofitable strategy families remain retired. No proven new after-fee forward edge, no changes to existing strategy limits, and no new PAPER trading GO.
