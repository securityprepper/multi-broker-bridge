# IBKR Advanced Execution Bridge retirement

Owner-directed transition to `securityprepper/multi-broker-bridge`.

## Confirmed changes

- **Advanced bridge production runtime:** `ibkr-bridge.service` was stopped and disabled on `ibkr-bridge-primary-chi`.
- **Scheduled development automations:** `Task - IBKR Deployment One/Two/Three/Four` were disabled.
- **Preserved:** `ibkr-gateway.service`, root operator and root maintenance services, existing PAPER status/once services and sockets, broker login/state and LIVE safeguards were not stopped or altered.
- **Old repository:** `securityprepper/ibkr-execution-bridge` remains readable for selectively copying proven functionality; no new work should be scheduled against it. This file does not archive or delete the repository.
- **Task Pause Watch:** Its controlling instructions expressly prohibit re-enabling intentionally paused tasks; the retired deployment automations should remain disabled.

## Selective reuse

Copy only a feature needed by a real order workflow, its small tests, and a concise runbook. Avoid importing the old project's root installer, large commissioning state machine, notification system, failover work, or LIVE activation into this minimal bridge.

## Do not confuse safety with readiness

Stopping the old runtime does not log into IB Gateway, establish Alpaca PAPER credentials, approve Robinhood LIVE trading, or verify a new bridge submission. The new bridge is preview-first and has not yet been commissioned to place authenticated broker PAPER orders.
