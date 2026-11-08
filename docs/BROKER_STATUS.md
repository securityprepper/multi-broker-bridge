# Broker capability and readiness

## Alpaca

- **Paper API:** Official REST at https://paper-api.alpaca.markets/v2/orders
- **Supported now in code:** single stock, whole-share DAY LIMIT, strict $200/order cap, account check, order acknowledgment, client ID readback.
- **Sell:** blocked unless a long position's available quantity is verified.
- **Not in v1:** market, margin, fractional, 24-hour, bracket, stop, OCO, replace, automatic daily close, batch orders.
- **Operational:** Requires separately provisioned PAPER trading credentials. Existing Alpaca market-data credentials on www3 are not presumed to authorize broker PAPER trading. No authenticated submission verified.

## Interactive Brokers

- **Paper API:** Official asynchronous TWS API against local IB Gateway at 127.0.0.1:4002.
- **Supported now in code:** stock whole-share DAY LIMIT with broker nextValidId, exact single DU PAPER account, receipt callback, $200/order cap. Verifies long position quantity before a sell.
- **Operational:** Official ibapi Python client exists on IBKR host, but the broker's PAPER port 4002 was not accepting a local connection at the last check. An authenticated PAPER Gateway session is needed before broker-connected testing. No order submitted.
- **Not in v1:** protective brackets, extended-hours orders, automatic reconnection/retry, multi-account, cancel, flatten, production trading. Until callbacks and broker readback are tested, submission is not considered commissioned.

## Robinhood Agentic

- **Official interface:** https://agent.robinhood.com/mcp/trading
- **Actual behavior:** Dedicated real-money Agentic brokerage account; no published sandbox/PAPER trading endpoint.
- **Supported now in code:** simulation/preview and explicit refusal of order submission.
- **Not in v1:** real Robinhood orders, unauthorized Robinhood API login, bracket/conditional broker features, unattended real trades.
- **LIVE trading:** Requires separate user connection, account onboarding, approval settings, and new explicit LIVE authorization. Never reinterpret a PAPER authorization as Robinhood live authorization.

## Definitions

- **Preview passed:** Local validated request, no broker communication.
- **Connectivity passed:** Broker answered a read-only account check, not an order.
- **Submission passed:** Broker acknowledged an actual PAPER order and matching broker/client order identifier.
- **Fill passed:** Broker returned fill/execution proof.
- **Protected position:** Exit order separately verified; no provider guarantees execution of an overnight stop.

## Scope limits

No second IBKR Gateway, no replacement of the current paper-monitor systems, no root privileged installer, no LIVE, no repository credentials, and no claim of broker execution until readback. The former advanced bridge is retained for copying narrow, demonstrably needed features only.
