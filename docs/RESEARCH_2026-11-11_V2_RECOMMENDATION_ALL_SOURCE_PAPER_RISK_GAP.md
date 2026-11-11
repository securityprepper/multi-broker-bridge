# November 11 2026 — receiving-Alpaca PAPER all-source risk coverage audit

## New confirmed release blocker in disabled recommendation router
READ-ONLY AST/source inspection of the installed /opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/bridge.py showed the account-wide daily loss and exposure guard (earnings_risk_require) is called ONLY inside the condition row["source_task"] == EARN_TASK. There are zero unconditional daily-loss or combined-exposure checks in the preflight function.

Other Trading Opportunities or Five-Day Rebound recommendation sources currently have receiving Alpaca PAPER account identity, current positions and open orders, same-symbol conflict checks, cash and a $2,000 individual intent cap. But they DO NOT call the independent loss-lockout and combined $11,800 portfolio exposure risk monitor. If the separate router were enabled, these non-earnings orders could bypass established receiving-broker account-wide risk limits. This is a verified **code release blocker**, NOT proof of an actual order, realized loss or MBB safety failure. The separate router timer remains disabled.

The existing earnings-specific PAPER guard is broker-scoped, uses the exact Alpaca PAPER account fingerprint and session, requires a broker-verified independent monitor no older than 95 seconds, enforces a $400 daily loss limit and a $11,800 exposure cap including held positions and outstanding buy orders. It can be applied unconditionally to every recommendation source following a reviewed PAPER-only integration. IBKR/Robinhood inventory is optional context only and MUST NOT block the independently qualified receiving Alpaca PAPER trade.

## Completed research-only work
Created research/v2_router_allsource_risk_coverage_20261111.py and tests/test_v2_router_allsource_risk_coverage_20261111.py on canonical V2 research/rebound-v2-conditional-exits. The pure research model consumes synthetic receiving-Alpaca evidence without any network, broker, DB or order operation. 12/12 targeted offline tests passed on isolated www3 checkout. Scenarios included daily-$401 loss, active lockout, stale/wrong-account risk monitor, missing own positions/orders, pending partially filled orders, gross short exposure, limit crossing and $2,000 single-ticket cap. Even a passing result is SHADOW ONLY; order_authorized is always false.

## Remaining PAPER release requirements
1. Integrate unconditional receiving-Alpaca PAPER daily-loss/exposure checks for all Trading Opportunities, Five-Day Rebound and earnings sources. Include broker-held positions, pending orders and reserved cross-strategy intents without double counting.
2. Apply previously verified fresh quote POST-receipt clock and the second 13:15 CT just-before-broker-POST entry check, with definitive pre-submit no-order disposition only when exclusive ownership and proof no broker POST exists.
3. Run complete host-side regressions and readback tests for idempotency, risk caps, partial fills, post-POST uncertainty, native stop/target brackets, holiday fail-closed checks and 13:40 CT liquidation/14:00 verification before separately approved PAPER commissioning.
4. Preserve all active V1 PAPER/LIVE, broker orders, existing safety monitors, holiday state and timer schedules. This research run submitted zero orders and changed no active source.

There remains NO independently verified, genuinely untouched after-cost profitable new strategy. Retired price-only/gap/GLD-lag/reentry signal families remain retired. Issuer/analyst numeric revisions still lack independent as-of licensed receipt evidence.
