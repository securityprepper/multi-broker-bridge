# R1M one-minute PAPER persistence: SQLite to Percona — deployed 2026-11-16

**Release status:** Installed and live-verified on authorized `www3.securityprepper.com` at 14:48 America/Chicago. Owner explicitly requested "Use Percona, not SQLite. Fix the problem." Scope is the independently commissioned R1M PAPER strategy and its hourly GET-only research audit; this is not an authorization to change unrelated V1 PAPER/LIVE strategies, trading limits, emergency settings, or scheduling.

## Root cause and remediation

Prior research artifact `docs/RESEARCH_2026-11-16_R1M_DECIMAL_SQLITE_ADMISSION_BLOCKER.md` proved a Python `Decimal` in `vs_close_pct` could not be bound as SQLite parameter 10. Existing service invocations failed closed before a broker POST.

**Now:** R1M persistence uses Percona Server 8.4, database `securityprepper_r1m_paper`, InnoDB case-sensitive tables, and dedicated localhost-only `sp_r1m_paper` with SELECT/INSERT/UPDATE/DELETE rights only. The root-only credential is loaded into both systemd services via `LoadCredential=r1m_percona_config`. The 13-table schema was provisioned with root authority, independently of the unmodified legacy SQLite ledger used by other directions. No dynamic schema DDL or SQLite fallback is permitted in the R1M production path.

**Installed files:**
- `/opt/securityprepper/direction-paper-executor/r1m_percona.py`, SHA-256 `acbc5114431cd7aed2326448be285f87c44de174aaa664d6e8e67c0fa1263078`
- `/opt/securityprepper/direction-paper-executor/one_minute_research.py`, SHA-256 `075a90b45f79d06b78f5d63970107ae9b00fbcd7a6af9ad3abe6f351a674dcc4`
- `/opt/securityprepper/direction-paper-executor/research_audit.py`, SHA-256 `795db9c2a3b637aceacae067452071617bf965963196e5dae0ac0ffc1fbe268a`
- `/opt/securityprepper/direction-paper-executor/test_r1m_percona_adapter.py` plus 24 pre-existing R1M regression tests (32 tests passed in total).
- Recovery copies of the two prior executor/audit source files: `/var/lib/securityprepper-r1m-percona-release-20261116/`, mode 0700.

**Minimal code changes:** R1M executor and hourly audit call the dedicated `r1m_percona.connect()` when using their production-default state path, preserving explicit temporary SQLite path use in older non-live unit tests only. The historical extension calculation now requires finite `Decimal` and converts rounded percentage to a native float before signal persistence. No eligibility, clearance, quote, order submission, stop, session, or entry threshold was changed. The Percona adapter preserves atomic pre-POST reservation commits and unique `client_order_id` idempotency; SELECT/INSERT/UPDATE/DELETE plus a strictly verified fixed schema are allowed. Unavailable Percona fails closed, never falls back to SQLite.

## Provenance and validation

The old SQLite file was read without modification to migrate previous signals, research runs, audits, recommendations, timing histories, and counterfactual audit data. At migration final backfill there were 420 historic timing records and 80 research runs; there were **zero recorded PAPER order attempts** to move. After the cutover, the Percona readback showed 436 timing rows, 82 research runs, 16 R1M signal rows and zero broker POST attempts, demonstrating new events were written into Percona, not the old R1M SQLite path.

- 24 existing R1M unit tests passed unchanged; 8 new fail-closed adapter tests passed; 32 total.
- A disposable, isolated Percona test database verified duplicate reservation rejection, persisted signal/episode/timing records, exit peak upserts and repeated hourly audit updates without broker calls. Its database was dropped and the test grant revoked after testing.
- **14:48:09 CST, November 16:** natural scheduled `securityprepper-one-minute-paper-research.service` completed successfully with `Result=success`; inspected 221 stocks, four qualified R1M signals, all blocked by the original 13:15 CST entry cutoff, zero PAPER posts.
- **14:49:01 CST:** a broker GET-only manual `securityprepper-one-minute-paper-audit.service` check returned `Result=success`, `orders_submitted=0`, `notifications_sent=0`, `broker_readback_unknown_count=0`.
- Both original systemd timers remained enabled; no modifications to their recurrence, R1M broker order code, research commissioning marker, V1/LIVE accounts, protective stops or holiday publisher.
- No forward after-fee profitable alpha is established by this repair. Recommendation Audit alone remains responsible for notifications of newly closed recommendation-linked trades.

## Archived source

- Percona adapter snapshot: `research/r1m_percona_release_20261116.py`
- Adapter regression: `research/test_r1m_percona_adapter_20261116.py`

If Percona becomes unavailable, R1M intentionally stops admitting new signals or orders (database fail-closed); do not reenable legacy SQLite for R1M without a separately approved recovery plan. Keep existing broker protective exit functions independently operational. The original source files in root-owned recovery storage support incident recovery after ensuring position and order state is fully reconciled.
