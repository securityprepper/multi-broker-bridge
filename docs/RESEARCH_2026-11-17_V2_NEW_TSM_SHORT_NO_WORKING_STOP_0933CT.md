# New material PAPER held-position safety incident — V2 TSM short, November 17, 2026

**Research-only observation; NO broker POST, cancel, close, or active V1 changes.**

## Independently reconciled NEW holding

At **2026-11-17 15:33:18.893136 UTC** (09:33:18 CST) on `www3.securityprepper.com`, a GET-only Alpaca PAPER broker readback verified the account ID matches the root-owned expected PAPER account. Broker returned **two current positions** and **zero open working orders** in that account. One position is new relative to the previous SNDK incident:

| Symbol | Side | Signed broker quantity | Source | Native entry fill | Entry price | 09:33 broker current price | Open orders |
|---|---|---:|---|---|---:|---:|---:|
| TSM | short | -5 | V2 | 2026-11-17 15:10:39.680983 UTC | $362.92 | $360.05 | none |
| SNDK | short | -2 | V2 | 2026-11-17 09:20:53.466022 UTC | $790.91 | $777.565 | none |

TSM is **newly verified as short and unprotected**, not a repetition of the earlier SNDK incident. TSM was up approximately **0.79% unrealized** (in the direction of its short) at broker readback; the safety concern is **not** a claim its stop had already been breached. No broker-native stop order was open for either symbol.

Provenance cross-check:
- Percona `securityprepper_trading.sp_paper_order_provenance`: TSM V2 `OPEN_CONFIRMED`, sell 5, broker status `filled`, source ledger `legacy_direction_ledger:exact_client_id` and matching client-order identity.
- The legacy `/var/lib/securityprepper-direction-paper/state.sqlite3` was queried **read-only**. Its TSM V2 row shows `BROKER_FILL_VERIFIED`, sold quantity 5, price $362.92, fill at 15:10:39.680983 UTC, `closed_at_utc=NULL`; SNDK V2 row similarly open and verified.
- Alpaca PAPER GET `/v2/positions` returned `qty=-5, side=short` for TSM; GET `/v2/orders?status=open&limit=500` returned **zero orders** account-wide. This alone does not mean a valid software risk monitor would necessarily execute before its threshold, but means there is no currently working broker stop.

## Pre-existing software-stop defect still applies to NEW position

Installed `/opt/securityprepper/direction-paper-executor/direction_paper.py`, `software_risk_exits()`, checks `Decimal(str(pos.get('qty'))) != Decimal(str(qty))` and immediately continues when different. For a native short, broker `-5` does not equal filled absolute `5`. The later `qty_available<=0` test can also incorrectly reject signed short availability. Thus current V2 short positions cannot reach even a software 1% stop, profit-target exit, or session-flat guard through that code path. This is the **same pre-existing defect** previously researched for SNDK; the **new fact is a fresh TSM V2 short entry occurring while defective protections remain deployed**.

Do not infer a fill from order acceptance. This incident uses the recorded exact filled row, observed broker position, and independent readback of working orders. No other brokers' inventories were used to gate Alpaca.

## Owner-action boundary and remediation recommendation

Because this is a scheduled **research-only** task, no broker order, PAPER sell/buy-to-cover, executable patch, systemd setting, LIVE permission, Pushover, or timer was changed. Owner or separately authorized PAPER safety executor should (1) inspect the positions/open orders and ensure protective coverage, (2) commission an isolated, tested **PAPER-only** signed short quantity and available-quantity correction, preserving account matching, idempotency, quote freshness, news clearance, and existing risk protections, (3) rerun a zero-POST regression for both long and short plus partial/mixed/other-strategy positions, and (4) verify native orders/fills after deployment. A temporarily disabled new V2 short-entry pathway could be considered separately if protection cannot be restored promptly, but research does not authorize doing so.

**Prior repeated known finding:** SNDK short unprotected was already reported at 06:40 CST; this report is specifically about the additional TSM short entered at ~09:10 CST. No robust after-fee strategy edge is inferred.
