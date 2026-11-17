# Newly verified IBKR LIVE pending-order safety finding — 2026-11-17 03:33 CST

**Scope:** read-only, no LIVE or PAPER changes; broker access restricted to account inventories and existing Percona readbacks. This is a fresh finding, not the resolved Nov 17 02:38 account-mapping discrepancy.

At 2026-11-17 09:33:07 UTC, Percona `securityprepper_trading.sp_broker_collection_runs` recorded a new `VERIFIED_READBACK` IBKR LIVE manifest with `positions_complete=1`, `orders_complete=1`, **zero positions** and **nine working-order rows**, account ending 3448. All nine order rows appeared in `sp_live_broker_position_order_snapshots` for the *same* `snapshot_run_id`. The separately connected IBKR native account interface returned zero nonzero positions and the same nine unfilled GTC orders; the connector's `NEW` status corresponds to native `Submitted` (AON/WEC BUY) or `PreSubmitted` (MRK BUY, all SELL legs).

Three pending GTC BUY limit entry orders, each submitted on **2026-10-29**:

| Symbol | Shares | GTC limit | Native state | Order ID |
|--|--:|--:|--|--|
| AON | 2 | $315.50 | Submitted | 1728917931 |
| MRK | 4 | $140.00 | PreSubmitted | 2129470181 |
| WEC | 2 | $113.00 | Submitted | 819125976 |

At limits these entries represent $1,417 in prospective purchases. They are **orders, not holdings or fills**. Their eventual execution is possible unless explicitly canceled/expired; this is not an assertion they are unintended.

Six corresponding GTC SELL orders exist in `PreSubmitted` state: AON stop and limit (1728917932, 1728917933), MRK stop and limit (2129470182, 2129470183), WEC stop and limit (819125977, 819125978). They appear to represent protective/target bracket legs; the available native snapshot does not contain parent linkage/OCA/transmit attributes, so do **not** independently classify them as executable or orphaned. Execution feed remains `EXECUTIONS_UNAVAILABLE`.

**Safety consequence:** A flat account is not the same as no pending orders. Any procedure that interprets zero positions as globally flat must separately check *fresh, complete working orders*, including pending GTC entry brackets. The operator must review these three entry orders and accompanying bracket legs in the broker if remaining flat is intended. No LIVE cancel or other broker action is authorized from research.

**Separate newly verified blocker, off-hours one-share IBKR PAPER commissioning:** A host-local `ss -ltnp` check at 2026-11-17 ~09:31 UTC found only `127.0.0.1:4001` equivalent LIVE API listener and **no port 4002** PAPER listener. Prior actual one-share PAPER submissions at ~05:22–05:26 UTC confirm 4002 was previously reachable; the currently running Java Gateway listening on 4001 started at ~08:31 UTC. Without 4002 the premarket SMART-only harness cannot safely obtain a verified DU account, current PAPER positions and working orders, or submit its authorized test. Do not fall back to 4001 (LIVE), start another Gateway, restart/switch session, or retry unknown orders. Requires an approved, restored authenticated PAPER API connection on 4002 without compromising LIVE access, or new explicit owner session orchestration authority. No PAPER test was attempted in this research run.

**As-of and holiday:** Root-owned www3 gate valid and unpaused at 09:30:44 and refreshed at 09:33:38 UTC; revision 2, short published TTL, future boundary November 20 16:07 CST. No scheduler, V1, emergency settings, IBKR live orders, positions, gateway or Pushover were modified. Evidence is read-only and does not establish a profitable alpha. Do not recycle the same order or missing-port status as a later new finding unless its state materially changes.
