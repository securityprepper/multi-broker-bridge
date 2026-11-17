# November 17, 2026 14:35 CST — V2 Alpaca PAPER shorts remain open AFTER 14:00 latest-flat objective

**New finding distinct from earlier 13:40 breach:** At 2026-11-17T20:35:55.795094+00:00 (14:35:55 CST), the enabled read-only Alpaca PAPER inventory exporter recorded a fresh, account-verified `ACTIVE` broker snapshot with **six open SHORT positions** and **zero OPEN orders**. Snapshot had 39s age at independent 14:36:34 CST check. The owner's latest verification/flat objective is 14:00 CST, so these positions remained open at least 35 minutes after that deadline. There were **no verified broker protective stop orders** in the open-order list.

| Symbol | Current broker side/quantity | Broker reported average entry |
|---|---:|---:|
| AMD | short -4 | 488.5475 |
| INTC | short -36 | 54.13 |
| NVDA | short -13 | 151.65 |
| SNDK | short -2 | 790.91 |
| TSM | short -5 | 362.92 |
| WDC | short -7 | 273.54 |

**Evidence:** `/var/lib/securityprepper-paper-inventory/current.json` (source `securityprepper-paper-inventory-readonly.service`), 5-minute broker GET-only exporter, with `paper_only=true`, `broker_verified=true`, `positions_count=6`, `open_orders_count=0`. Its code issues fixed GET requests for account, current positions, open orders, recent orders and clock; no order-write actions. The independently examined minute bridge journal entry at 14:35:33 showed `broker_post_attempt_count=0`, `risk_exits=[]`, with V2 early rebound `TSM` action `CLOSE_ONLY_NO_NEW_POSITION`. At approximately 14:36 another preexisting `KeyError` failure recurred; duplicate signal crash is an **already reported, unresolved defect**, not a new root cause.

**Prior distinct findings (do not notify again):** Short signed-quantity mismatch in risk exit matching; 13:40 time guard set to 14:00; duplicate signal `notification` summary `KeyError`; and an actual 13:40 liquidation miss. Those are not this finding. The new and additional outcome is documented failure to meet even the 14:00 final objective.

**Action:** Owner should review all six broker PAPER shorts and protective coverage immediately. A separately approved PAPER-only safety release must correct signed-quantity handling, required 13:40 exit and duplicate-signal exception. Read-only research cannot place exits or modify current production executor, timers or commissions. No broker orders, LIVE/PAPER execution settings, scheduled tasks, or protective stops were modified during this investigation. The presence of six open positions is broker-confirmed; no fill or hypothetical profit/loss inference is made.

**Holiday gate:** Fresh authoritative root-owned gate passed at 2026-11-17T20:35:24.328071+00:00: schema1, status_valid true, timezone America/Chicago, revision2, calendar coverage true, unpaused, published 14:35:00-06:00, valid until 14:37:30-06:00, next boundary Nov 20 16:07-06:00. This is per-run verification, not reliance on historical Nov14 state.

**Related earlier incident:** `docs/RESEARCH_2026-11-17_V2_ACTUAL_MISSED_1340_FLAT_SIX_PAPER_SHORTS.md`.
