# SRM hourly-report integrity: three reproduced code-level failures — November 19, 2026

**Scope:** read-only investigation for the existing hourly Trading Strategy Research reporter, following the owner's new SRM H1/H2 reporting exception. **No broker API, PAPER/LIVE order, timer, Pushover, active monitor source, service configuration, database, existing watermark, or existing broker risk controls were modified.** Tests used a temporary fake holiday-gate file, temporary event journal/state, synthetic as-of scans, and mocked watcher-paper `emit` responses.

## Live observation for the 11:30 CT hourly run

- Verified the current authoritative root-owned holiday cache twice on www3: schema version 1, valid status, America/Chicago, coverage, current publication, short valid_until, unpaused, and future next_check_at. The second verification was at **11:35:20 CT**.
- Native SRM `latest.json` at 11:35:12 CT showed **zero current active sustained risers and zero new hourly events**.
- No `sustained-alerts-YYYY-MM-DD.jsonl` files exist in the SRM directory; the existing `chatgpt-hourly-sent-events.jsonl` contained **zero rows**. `state.json` had no active `episodes`. The first-observed record from November 18 is separate **AFTER_HOURS_RISER** five-minute research, not an H1 sustained-hour event; do not relabel it.
- The order-outcomes file was absent because no SRM hour handoff had been emitted; do not infer fills or account status. **No H1/H2 notification is warranted.**

## Reproduced problems (new; not yet corrected)

1. **SRM internal holiday-gate freshness fail-open.** The installed `monitor.py` `authorized_gate` validates schema/paused/coverage/next_check_at but *does not validate* `published_at`, `valid_until`, root ownership/mode or a short freshness age. A temporary fixture with valid_until expired by over two hours but future next_check_at returned `(True,"GATE_VALID")`. A missing `valid_until` also passed. If the publisher stops, the monitor could still generate order-intended handoffs despite stale evidence, though the downstream protected watcher-paper broker route retains its independent gates. This **does not prove any prohibited real order or alert occurred**.

2. **Verified H1 lost if the protected handoff is blocked.** The installed monitor appends to `sustained-alerts-YYYY-MM-DD.jsonl` **only** when the upstream watcher-paper queue returns `QUEUED` or `DUPLICATE`. A mock real H1 with status `NOT_COMMISSIONED` appeared in `latest.json` but no durable `sustained-alerts` journal was created; state persisted `last_alerted_hour=1`, so the event cannot be recovered on later hourly reads after `latest.json` advances. The owner explicitly requires reporting verified SRM hours even when PAPER is blocked.

3. **One missing verified scan does not reset the H2 hour count.** The installed `decide` increments `misses` on a missing sustained lead but permits continuity with `misses<2` and a 180-second last-observed gap. Synthetic observations through minute 59, one missing scan at minute 60, and a resumed scan at minute 61 incorrectly yielded `H2` for the original episode. The new reporting contract forbids inferring continuation through missing/stale scans; a resumed rise must be a new H1 episode after appropriate fresh verification.

## Broker-disabled reproducible evidence

- Source-only test: [research/test_srm_hourly_report_integrity_20261119.py](../research/test_srm_hourly_report_integrity_20261119.py)
- Three isolated regression tests reproduced the installed behavior (**3/3 passed**, confirming existing defects rather than confirming a correction).
- The genuine holiday gate and the broker were never mocked or modified in production, nor was the live SRM service restarted.

## Required isolated remediation (not authorized as part of Trading Strategy Research)

- Make SRM itself fail closed on all mandatory trust fields, freshness, ownership/mode and pause, rather than assuming downstream broker checks solve the upstream event/handoff problem.
- Append **all** first-party verified H1/H2 events to an immutable durable journal immediately with a unique `(symbol,first_trend_at_utc,hour)` key and real price/momentum/provenance, *regardless of queue status*. Record blocked status explicitly. Do not reserve away the reporting event when a queue is uncommissioned or fails. Preserve existing broker idempotency and no-retry protections separately.
- Require uninterrupted verifiably observed scans to increment the original trend episode; a missing/stale scan breaks continuation. Never reconstruct H2 from later price movement.
- Regression-test pause expiry, blocked/not-commissioned order paths, lost handoff, replay/watermark, H1→H2 continuation, gaps, midnight, duplicate IDs and broker quote/filled-vs-accepted provenance. Broker entry remains entirely the existing protected watcher-paper route.

**Release remains unapproved; leave existing live code and risk controls unchanged.** This is a newly verified implementation blocker for reliable SRM reporting, not a profitable forward strategy finding.
