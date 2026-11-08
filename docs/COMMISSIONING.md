# Commissioning checklist

## Current facts (November 7, 2026)

- `multi-broker-bridge` code and Python offline tests pass. No broker order has been submitted from this repository.
- Existing IBKR `ibkrbridge` account can import the official `ibapi` client, and the protected existing configuration has an `IBKR_EXPECTED_ACCOUNT` field. The local PAPER API port `127.0.0.1:4002` was **refusing connections**, even though Gateway service status was active. Reauthenticate IB Gateway PAPER and verify port/session before any submission.
- On www3, the Alpaca feed timer was disabled. Root-protected **market-data** credentials exist, but there is no confirmed separate PAPER trading account credential provision. Do not treat data entitlement or a staging script as successful broker PAPER order execution.
- No connected Robinhood Agentic Trading MCP/PAPER environment was verified. Robinhood's agent account is real brokerage, not PAPER.

## IBKR PAPER readiness

1. Owner authenticates existing Gateway in PAPER; do not restart the Gateway or disturb other running services just to test this project.
2. Keep code execution under `ibkrbridge`, using existing official ibapi Python environment. Map the existing protected `IBKR_EXPECTED_ACCOUNT` to `IBKR_PAPER_ACCOUNT` **without exposing or committing the value**.
3. Perform a read-only `--check` and validate exactly one DU-prefixed PAPER managed account.
4. Enable the dedicated local PAPER execution gate only after confirming host readiness; authorize one tiny test, read broker acknowledgment/position before any further attempt.
5. If any connection or callback is ambiguous, reconcile broker orders before considering a distinct new order. Never retry the same client order ID.

## Alpaca PAPER readiness

1. Obtain separate PAPER trading credentials; keep them in the host's protected credential store (never source, task logs, or chat).
2. Use only the fixed `paper-api.alpaca.markets` endpoint. Check account identity and trading-block status.
3. Authorize a low-value DAY limit test with a unique client ID; verify it with `--readback`. An accepted order is not a fill.

## Robinhood

There is no advertised paper-trading endpoint for Robinhood Agentic Trading MCP. `--capabilities` and preview are safe; attempted execution is refused. Any real Robinhood Agentic account connection and actual order would require a separate explicit LIVE decision and agent-account approvals. Do not use real money to satisfy a PAPER test.

## No automatic trading

Do not enable scheduled placement from the five-minute monitor until at least one authorized broker-accepted PAPER order, its status readback, and cancellation/exit management have been verified. This remains a small project with broker-specific enhancements added when needed.
