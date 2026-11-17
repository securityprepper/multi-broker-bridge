# Off-hours software stop watch

Deployed report-only observer for IBKR Live and Robinhood Agentic long stock positions.
No LIVE submission or cancellation method exists in the observer. Live closing remains
disabled pending separate owner authorization and complete readiness evidence.

## Behavior
- Each minute off-hours, match a positive equity position to its account's active,
  unfilled SELL GTC stop. Filled/canceled/rejected/pending-cancel orders are excluded.
- Breach threshold: at least max($0.01, 0.05% of the stop). This initial noise
  threshold is configurable in source and has not been optimized against live fills.
- Position and order evidence must be at most 120 seconds old; price at most 90
  seconds old. Prices are completed one-minute trades, not executable bid guarantees.
- Match account and stock symbol. Options, crypto, shorts and PAPER are excluded
  from live detection. Paper harness fixtures are explicitly isolated.
- Dashboard displays broker coverage and breached stop rows independently of the
  main position filters. Include PAPER reveals commissioning result summaries.
- Pushover groups up to three rows, masks account IDs, shows stop, price, distance
  and Chicago quote time. Delivery receipts and current state persist in Percona.
  Failed deliveries retry. The same order and stop price does not repeat every
  minute; a verified recovery above the stop rearms it. A changed stop is new.
- Existing holiday validation remains before any broker or market contact.
  Robinhood off-hours cadence is one minute; existing regular-session cadence
  remains 15 minutes. The existing holiday scheduler still defers this timer.

## Runtime
Generic detector: multi_broker_bridge/offhours_stop.py.
Dashboard implementation: deploy/trading-dashboard/ in this branch.
On www3 it is installed at /opt/securityprepper/trading-dashboard.
Collector service: securityprepper-trading-dashboard-collector.service.
Robinhood read-only collector: /opt/securityprepper/robinhood-mcp-collector/holiday_runner.py.
Its timer now wakes at *:*:15; scheduled_slot returns true for PREMARKET,
AFTERHOURS and OVERNIGHT using the generic session function.
Retain the existing gate validation and holiday scheduler allowlist.

Collector needs two additional LoadCredential entries using the existing
sector-monitor/private/pushover_user and pushover_token files. Never embed values.
The existing sp_dashboard database role needs SELECT on sp_robinhood_mcp_orders
and SELECT/INSERT/UPDATE on the two new tables. Do not rerun provision.py to
rotate its credentials during a routine deployment.

CREATE TABLE sp_offhours_stop_watch (
 id TINYINT PRIMARY KEY, updated_at_utc DATETIME(6) NOT NULL, payload_json JSON NOT NULL
);
CREATE TABLE sp_offhours_stop_paper_tests (
 test_id VARCHAR(64) PRIMARY KEY, updated_at_utc DATETIME(6) NOT NULL, payload_json JSON NOT NULL
);
Use the existing securityprepper_trading Percona database.

## Verification on November 16, 2026 (Chicago)
- 13 pure detector/exit-plan tests and 8 integration tests passed.
- Alpaca PAPER: one SPY share bought at $739.84. A native GTC stop at $740.20
  remained unfilled while the overnight quote was $739.76, 0.0594% below it.
  The detector identified it; cancellation was confirmed, an extended-hours
  DAY LIMIT sell filled at $739.76, and final native position readback was zero.
  Initial setup failures and their subsequent cleanup remain in private Percona.
- Real Pushover PAPER TEST accepted with a provider delivery receipt.
- IBKR PAPER: identity, completed position/order inventory, and overnight quotes
  verified. Actual one-share OVERNIGHT submissions rejected with error 10329
  (direct-routing precaution), followed by 201 (order discarded). No fill.
  Independent subsequent position/open-order readback was empty. Do not report
  this as a passed execution test or retry blindly.
- Paper commissioning tools are fixed to paper-api.alpaca.markets or local IBKR
  port 4002 with exact expected DU account verification. The IBKR harness now
  accepts PREMARKET/AFTERHOURS on SMART as well as OVERNIGHT on its own venue.
  Expected IBKR account comes from IBKR_EXPECTED_PAPER_ACCOUNT; gate JSON must
  be freshly copied from the trusted publisher before the test.
- At commissioning, Robinhood Agentic had zero positions and working orders.
  The regular Robinhood account is deliberately outside this task's scope.
- IBKR Live has no current persisted position/order feed and no Live gateway
  listener on the connected IBKR host. The dashboard clearly reports this gap.

## Remaining readiness requirements
1. Complete an actual IBKR PAPER stop-breach/cancel/limit-exit/final-flat test.
   Use SMART during premarket if OVERNIGHT remains blocked. Never weaken global
   Gateway precautions, create another Gateway, or replace the authenticated one.
2. Commission a complete, fresh read-only IBKR LIVE positions/open-orders feed,
   including an account manifest proving an empty snapshot is complete.
3. Prove account-specific live routing/session eligibility, cancellation/fill
   race handling, pending orders, partial fills, restart deduplication and a
   kill switch. Re-read positions and the original stop before any future exit.
4. Robinhood Agentic execution capability/session coverage needs separate
   verification. Its collector's OAuth grant is read-only by policy and must
   not be reused for trading.
5. Notify the owner when ready. Separate explicit authorization is still needed
   before enabling actual LIVE closes. Paper evidence does not guarantee fills.

Vendor references:
https://www.interactivebrokers.com/support/faq/content/691836583
https://www.interactivebrokers.com/campus/trading-lessons/overnight-trading-in-tws/
https://robinhood.com/us/en/support/articles/extendedhours-trading/
https://docs.alpaca.markets/us/docs/orders-at-alpaca