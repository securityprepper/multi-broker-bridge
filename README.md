# Multi-Broker Bridge

A **small, PAPER-first** order adapter for Alpaca, Interactive Brokers, and Robinhood Agentic. This replaces the disabled `ibkr-execution-bridge` development workflow. The old repository is retained read-only for selective reuse; it is **not** a runtime dependency.

## What works and what does not

| Broker | PAPER order transport | Live trading | Initial order type | Constraints |
|---|---|---|---|---|
| Alpaca | Official HTTP PAPER endpoint (`paper-api.alpaca.markets`) | Disabled | Whole-share LIMIT DAY | Requires `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY`, paper keys only |
| IBKR | Official `ibapi` client via existing local PAPER IB Gateway (`127.0.0.1:4002`) | Disabled | Whole-share LIMIT DAY | Requires exact `DU...` PAPER account, nextValidId, order acknowledgment; active Gateway login |
| Robinhood Agentic | **Not offered by Robinhood** | Disabled | Simulated preview only | Official Trading MCP uses a dedicated real-money Agentic account; no simulated order is submitted to Robinhood |

Robinhood live Agentic placement is a **different project and permission**. No unofficial Robinhood APIs, scraped sessions, or live orders.

## Design

- Small broker-specific adapters; no second Gateway, root operator, Kubernetes, leader election, or redundant hosts.
- Default preview-only. `--execute` is required for any PAPER submission.
- Exact broker/environment/account verification, whole positive share quantities, positive limit prices, a **$2,000 cap on each separate stock order**, broker available-funds limits, and strict ticker validation.
- A durable local SQLite submission registry prevents repeating the same client order ID after a timeout, including ambiguous broker responses. `UNKNOWN` requires reconciliation; never auto-retry it.
- Provider acknowledgments are not fills. Print status and identifiers without account details.
- No automatic extended-hours stops or bracket protections in v1. SELL checks an existing long position; no deliberate shorts. Robinhood has **no broker PAPER environment** and remains simulation-only.

## First-run steps

1. Configure each broker's PAPER credentials/session outside the repository (environment or protected service configuration). Do not commit credentials.
2. Run `python -m multi_broker_bridge.cli --broker alpaca --symbol SPY --side buy --qty 1 --limit 100 --client-order-id TEST-001` for a preview.
3. Verify connectivity and account ownership with `python -m multi_broker_bridge.cli --broker alpaca --check`.
4. An explicitly approved small PAPER test may use `MULTI_BROKER_ALLOW_PAPER=1` and `--execute` together. For IBKR, use the official Python `ibapi` package installed on the IBKR host under an unprivileged service account. Never run from root.
5. Alpaca status: `python -m multi_broker_bridge.cli --broker alpaca --readback TEST-001` (requires PAPER credentials). Inspect broker activity before asserting a fill, then test cancel and close separately when implemented.

**Do not use a dummy low limit order as proof of an actual fill.** The first safe milestone is a broker-accepted PAPER order with a matching readback, not a profitable or fully protected position.

## Setup environment

```text
ALPACA_PAPER_KEY_ID=...
ALPACA_PAPER_SECRET_KEY=...\nMULTI_BROKER_ALLOW_PAPER=1           # only for explicitly authorized PAPER orders
IBKR_PAPER_ACCOUNT=DU...          # Exact known paper account
IBKR_PAPER_PORT=4002              # Fixed by implementation
MULTI_BROKER_STATE_DIR=/path/to/private/state
```

The CLI never prints secrets, does not accept live endpoints, and does not create real Robinhood orders.

## Safety/scope

Do not replace any existing Gateway login or restart other broker systems as part of this project. PAPER orders must be authorized and monitored; market hours, partial fills, rejected orders, and provider outages can change real broker state. New features are added only as needed, with tests and a short review of scope/risks.
## Initial sizing

Each buy order for a separate symbol is independently limited to $2,000 in PAPER (e.g. 1 SNDK, 2 MU, 4 AMD shares if each order's limit price × quantity is <= $2,000). There is no additional strategy-wide or account-wide exposure ceiling in this bridge; the broker's available PAPER buying power remains binding. Orders may still be rejected for insufficient buying power. No automatic allocation or real broker submission is enabled by this configuration change.
