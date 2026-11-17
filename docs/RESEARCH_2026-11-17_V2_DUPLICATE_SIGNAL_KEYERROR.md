# Research-only: newly reproduced duplicate V2 signal return-schema failure

**Observed:** 2026-11-17 12:26:33, 12:27:33, 12:28:33, 12:29:33 and 12:30:37 America/Chicago, on www3. Active `securityprepper-direction-paper-executor.service` emitted `PAPER_DIRECTION_EXECUTOR_ERROR` with `reason_type=KeyError` and exit 2. No active source, service, order, broker account or timer change was made by this investigation.

## Exact reproduction and cause

At 12:25, the read-only V2 handoff carried new `EARLY_REBOUND` events for AMD, INTC and MU, subsequently present as reserved signal IDs in the existing direction-paper SQLite ledger. The handoff correctly retains events for several minutes, so these are supplied again in subsequent minute runs.

`direction_paper.apply_signal()` returns this incomplete result when `save_signal()` detects an existing signal ID:

```python
return {'signal':signal['id'],'status':'ALREADY_HANDLED','order_attempts':0}
```

Later `direction_paper.run()` unconditionally counts `sum(x['notification']=='PROVIDER_ACCEPTED_NOT_DELIVERED' for x in results)`. The duplicate result lacks `notification`, raising `KeyError('notification')`. A read-only clone of the existing SQLite ledger, with three independently verified duplicate signals, reproduced exactly `KeyError('notification')` without any broker calls. An isolated copy of the module adding only `'notification':'NO_POST_NO_TRADING_ALERT'` on the already-handled branch passed the same test: `SHADOW_ONLY`, three duplicate no-ops, zero order attempts and notifications. A broker-free regression was committed in `research/test_v2_duplicate_signal_notification_contract_20261117.py`.

## Safety separation

At 12:25:54 CT a separately scheduled, broker-GET-only PAPER inventory readback verified six open shorts AMD -4, INTC -36, NVDA -13, WDC -7, SNDK -2 and TSM -5, with **zero working orders**. These are not new holdings relative to the previous report and do not establish a fresh risk exposure event. The already-reported signed-short-quantity stop skip and 14:00 CT flatten timing defect remain separate. `software_risk_exits()` is called **before** the duplicate result tally, so do not claim the new KeyError caused those previous short-stop misses. This error nevertheless makes the independently commissioned direction-paper minute unit fail and leaves its reconciliation/outcome report untrustworthy until the duplicate contract is corrected.

## Suggested separately authorized PAPER safety release

Minimal change in active `direction_paper.py` should add `'notification':'NO_POST_NO_TRADING_ALERT'` to the duplicate branch, or alternatively make the final count use a safe explicit default. Verify that duplicate signals remain exactly-once no-ops, that no Pushover or duplicate order occurs, and that every result emitted by `apply_signal` maintains the required schema. Run the isolated regression plus existing unit tests, broker GET-only reconciliation and postrelease minute readback. **Do not deploy via this research task** without separate PAPER release authorization; do not change V1/LIVE code, active stops, timers or sessions. The earlier signed-quantity and 13:40 hard-flat defects also require their own explicit, verified protections before concluding exit safety.

No profitable forward edge is claimed, no PAPER or LIVE trades were initiated, and no recommendation-linked closed-trade notification is issued by this research.
