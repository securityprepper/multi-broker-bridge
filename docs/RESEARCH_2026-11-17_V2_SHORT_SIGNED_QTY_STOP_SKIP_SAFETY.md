# NEW broker/PAPER position safety incident — V2 short stop skipped on signed quantity (Nov 17, 2026)

**Status:** Independently verified material failure; **research-only evidence; no production code change or broker action**. Under owner instructions, research may not modify active V1 PAPER/LIVE code, commission or place an Alpaca order, edit stops/positions, change scheduler/timers, or send Pushover. Existing tested change needs separate owner-authorized PAPER safety release.

## Broker account and current position, verified by authorized GET-only receiving-Alpaca-PAPER API

The expected account ID was matched using the existing root-owned expected-paper-account credential, without displaying it. Broker GET `/v2/account`, `/v2/positions`, `/v2/orders?status=open&limit=500` on November 17, **12:40:04 UTC / 06:40:04 CST** returned:

- **SNDK SHORT -2 shares, average short fill $790.91, current broker reported $829.00, unrealized loss -$76.18 (-4.816%)**, **zero open broker orders**. The current price is the broker's reported field, not a separately verified executable cover ask.
- NOW SHORT -2 shares, average $98.22, broker reported $98.01, +$0.42 unrealized, also zero open broker orders. R1M's monitored software-only exit is a separate path and **no NOW stop breach is established**.
- No LIVE positions or orders were touched; the above is one positively identified Alpaca PAPER account. Do not claim other accounts verified.

Percona `securityprepper_trading.sp_paper_order_provenance` identifies the SNDK order as `V2 / OPEN_CONFIRMED / sell / 2 / filled` with evidence `legacy_direction_ledger:exact_client_id`. The underlying `/var/lib/securityprepper-direction-paper/state.sqlite3` V2 ledger records a distinct broker-verified filled SELL at **2026-11-17 09:20:53.466022 UTC** at $790.91, `closed_at_utc=NULL`, `exit_reason=NULL`. No closed trade is implied.

## Reproduced actionable defect

The deployed `/opt/securityprepper/direction-paper-executor/direction_paper.py` `software_risk_exits` at the observed as-of time used (unchanged) guard logic:

```python
if Decimal(str(pos.get('qty') or '0')) != Decimal(str(qty)): continue
# ...
available=Decimal(str(pos.get('qty_available') or pos.get('qty') or '0'))
if available<=0: continue
```

The native broker reports short `pos.qty='-2'`, `qty_available='-2'`; the positive fill ledger reports `filled_qty=2.0`. Thus, exact unnormalized signed quantity comparison **skips the short before it can request a quote or evaluate the configured -1% stop**, and later available-quantity guard has the same short-side issue. An isolated, broker-disabled replay of the installed `software_risk_exits` with this exact short quantity shape returned `[]` and verified that quote checking was *not even reached*. Regression source: `research/test_v2_paper_short_signed_qty_skip_20261117.py`.

The direction-paper executor also logged repeated `PAPER_DIRECTION_EXECUTOR_ERROR / KeyError` around 06:31-06:36 CST; subsequent 06:38+ executions returned successfully, but the SNDK short remained open with no broker working stop. The exact separate KeyError cause is not yet assigned; do not conflate with the deterministic signed-quantity exit skip.

## Safe proposed corrective release — NOT COMMISSIONED

1. Independently read receiving broker account, open orders, and **net positions** under the same strict account ID. Map short holdings only when `side=='short'`, filled entry side `'sell'`, `abs(qty)==filled_qty`, `abs(qty_available)>=filled_qty`, and sign is consistent with `short` (negative as in the verified Alpaca response). For long, enforce `side=='long'` with positive matching quantities. Never loosen cross-strategy exclusive-ownership checks, partial-fill protection, idempotent order reservations, quote/news/session rules.
2. Add regression for long, short, mismatched owner/quantity, zero/negative availability, pending order, stale quote, broker-readback error, duplicates, and fail-closed exit; ensure a legitimate short loss reaches stop preflight in a **broker-disabled test** with verified quote.
3. Separately diagnose recurring `KeyError` in the active direction executor in an isolated replay, no production credential or broker POST access.
4. **Immediately inspect SNDK PAPER short and protective coverage manually or through a separately authorized safety operator**. Research does not have authority to cover or amend it. Existing software stop cannot be relied upon for this short until corrected and independently tested.

Preserve current ChatGPT research cadence, V1/LIVE controls, safety watchdogs and active broker permissions unchanged. This is **not** a profitable-strategy finding. It is a new materially unprotected, losing PAPER short.
