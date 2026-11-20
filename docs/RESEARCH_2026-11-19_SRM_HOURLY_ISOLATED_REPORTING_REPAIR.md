# SRM hourly reporting continuity — isolated research repair (November 19, 2026)

**Scope:** Owner's “Proceed” directs continued Trading Strategy Research and the sole-owner ChatGPT Sustained Riser Monitor (SRM) hourly reporter. This investigation is research-only and made **no production SRM, Pushover, watcher-paper router, broker, scheduler, V1 or LIVE modifications**. The supplied hourly :30 America/Chicago reporting schedule remains unchanged.

## Gate and native source verification

- Checked the [holiday pause policy](https://github.com/securityprepper/trading-opportunities/blob/main/HOLIDAY-PAUSE-RESCHEDULE.md), then verified the authoritative root-owned, non-group-writable, schema-1 `/var/cache/securityprepper-holiday/task-gate.json`: America/Chicago, `status_valid=true`, `calendar_coverage_ok=true`, revision `3300`, `paused=false`, fresh publication and validity at **22:08 CT November 19**, next boundary **November 20, 16:07 CT**.
- Read first-party `/var/lib/securityprepper-sustained-riser-monitor/sustained-alerts-2026-11-19.jsonl`, `latest.json`, `order-outcomes-latest.json`, and `chatgpt-hourly-sent-events.jsonl`. The journal contains **11 source H1 events**. The durable reporting ledger contains **12 unique reported episode-hour keys**, including one independently verified H1 that was suppressed by the legacy per-symbol H1 cooldown and not written to the native event journal. All 12 were previously reported in this chat; **no new verified H1/H2 events remained** to be reported from these files.
- `latest.json` at 22:08 CT reported `active=[]`, no new SRM alerts, and no new order handoffs. The original latest PAPER outcomes were `NO_ORDER_OUTSIDE_RTH_BRACKET_WINDOW`; neither accepted orders nor fills were inferred.
- No stock below the USD $5 verified price floor was reported, recommended, routed, or added to a watchlist by this research.

## Previously identified causal defects — tested isolated repair, NOT DEPLOYED

1. **Expired holiday gate:** Installed `authorized_gate` validates only the next boundary, not file ownership, `published_at` freshness, `valid_until`, or revision. The isolated patch enforces root-owned regular file, immutable critical schema fields, valid coverage, `published_at` age 0–150 s and future `valid_until` and `next_check_at`; fails closed otherwise.
2. **Lost H1 upon non-QUEUED router outcome:** Installed source writes `sustained-alerts-YYYY-MM-DD.jsonl` only for `QUEUED` or `DUPLICATE`. A first-party verified H1 with blocked or failed watcher-paper handoff is missing from the journal. The isolated patch persists an immutable exact-episode-hour receipt **before** handoff, regardless of later `BLOCKED`, missing or ambiguous order outcome; the event record explicitly does **not** assert a fill. Cross-date duplicate checks compare historical journal files so a restart or midnight rollover does not create another H1/H2 receipt. If durable recording fails, the broker handoff fails closed.
3. **Unverified continuation:** Installed continuity accepts one missed minute (up to two misses and 180-second gaps), potentially advertising H2 without verified consecutive observations. The isolated patch requires exact adjacent completed minute observations, no prior inactive gap, and a fresh supported scan. The first stale/missing scan terminates continuity. A recovered rise creates a **new episode H1**, rather than an old H2.
4. **Unrelated per-symbol cooldown:** Installed `first_hour_alerted_at` suppresses distinct valid H1 episodes within the same hour. Isolated patch removes this suppression for **sustained events only**, retaining the major-mover separate guard and exact episode-hour idempotency. This addresses the earlier independently verified second INSM episode.

## Tests and commissioning boundary

- **43/43 broker- and Pushover-disabled regression tests passed** in an isolated staging directory: 17 existing adjusted SRM tests; existing major-mover/stop/signed-batch tests; 8 new SRM gate, continuity, blocked-outcome, journal, duplicate, price-floor and cross-midnight tests.
- No network broker POST, order, Pushover send, service restart, timer change, root publisher change, or production source edit was performed.
- Production source SHA-256 remains `1f84713de295d106431a672cd83a2cb307d8ce8d571cd1bb673216cea0889fff`. Isolated staged source SHA-256 is `cd70e16962070d21fe826f45e307da51175bfb4dc7556bb6c36e2d0ff26770e2`.
- Research patch: `research/srm_hourly_gate_journal_continuity_research_20261119.patch`.
- Existing-test adjustment: `research/srm_hourly_existing_test_update_20261119.patch`.
- Added regression tests: `research/test_srm_hourly_gate_journal_continuity_20261119.py`.

**Not a production release.** Active Pushover and watcher-paper source behavior remains unchanged until separately approved and commissioned with native service tests, reporter dedup/readback validation, and a fresh verified holiday gate. The research does not authorize new paper orders or alter LIVE trading.
