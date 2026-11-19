# R1M PAPER cutoff and sticky-flat safety correction — deployed November 18, 2026

**Owner approval:** “Fix the problem” following the independently reproduced R1M 19:00 CT entry reopening and midnight liquidation-reset report. Narrowly scoped change to the currently commissioned Alpaca PAPER R1M strategy only. No LIVE trading, IBKR Gateway, V1 PAPER/MBB executor, service unit, timer, market-data source, stop parameter, Pushover or broker account-permission changes.

## Verified initial conditions

At 23:48 CST, the authoritative root-owned America/Chicago `/var/cache/securityprepper-holiday/task-gate.json` was current, unpaused, with schema_version=1, status_valid=true, revision=2, full coverage, fresh published_at/valid_until, and a future next_check_at. A live, GET-only, account-matched Alpaca PAPER inventory check at 23:49 CST established **0 open positions and 0 working open orders**. The separate production R1M ledger remains in **Percona**, not SQLite; temporary SQLite ledgers are used solely by offline regression tests.

## Root cause

`research_open`'s negative cutoff check rejected only the 13:15–18:59 CT interval, reopening eligibility at 19:00 CT when BOATS starts and earlier that morning. `manage_research_exits` computed 13:40 on the *current clock day*, so previously opened lots stopped being flat-due when the local clock crossed midnight.

## Installed repair

File: `/opt/securityprepper/direction-paper-executor/one_minute_research.py`

- Previous SHA256: `8a78b7b6a1842d62a1abed7b7d008c92f903bdbf29267bafd8d4d28241ed46b9`.
- New SHA256: `350a8646254cfd2ad1381002a43af30fe0d081ad5c99b81d2c4f9a6fbc302285`.
- Root-only rollback archive: `/var/lib/securityprepper-r1m-paper-clock-safety-release-20261118/`.

`r1m_entry_allowed(now)` is a **positive** eligibility gate: weekdays from 04:00 ET (03:00 CT) until strictly before 13:15 CT, on SIP, excluding earlier hours, BOATS, weekends and any unknown/naive clock. All existing holiday, quote/freshness/spread, account, positions/open orders, news, extension, idempotency, borrowing and notional protections remain in force. Exit-only functionality is not treated as a new entry.

`r1m_flat_due(original_fill_at,now)` anchors 13:40 CT to the actual original verified broker fill in `paper_attempts.filled_at_utc` (falling back to the original immutable signal timestamp where a legacy verified fill lacks the timestamp). The due flag stays true after midnight, on holidays/weekends and on later sessions, rather than resetting at each day change. Once due, mandatory flat is checked **before** the prior stop and profit conditions; the pre-deadline stop arms (0.5%, 0.75%, 1.0%) are unchanged. The risk exit remains a broker-checked limit order, not a guaranteed fill or a broker-native stop.

## Tests and production readback

- **65/65 offline regression tests passed**, including 8 new tests with numerous subcases: entry-window boundaries, DST/naive clocks, before-broker rejection, permitted mock premarket entry, original-fill anchor, missed-midnight persistence, a simulated next-session forced sell, no duplicated submission and forced-flat precedence. Existing tests were retained; one legacy test fixture was corrected from a prohibited Sunday-night trading timestamp to Monday premarket.
- Source replaced atomically under the existing broker-execution flock; current code SHA verified from the installed host.
- Natural, existing one-minute timer runs following installation completed successfully, including the **23:55:09 and 23:57:09 CST** oneshot runs with `Result=success`, no PAPER order attempts, and the unchanged active/enabled timer.
- A fresh Alpaca PAPER GET-only inventory at **23:57:16 CST** confirmed 0 positions / 0 open orders. No actual PAPER or LIVE order was submitted by this safety release.
- Production R1M research and broker fill records remain in Percona. No training changes or profitable forward strategy edge were established.

## Artifacts

- Exact source-only diff: `research/r1m_paper_clock_safety_fix_20261118.patch`.
- New mock-only regression suite: `research/test_r1m_clock_safety_fix_20261118.py`.

**Residual limitation:** Persistent due eligibility is not itself proof of an executed close. A previously rejected/expired/partially filled exit can still require explicit terminal-order and cumulative-fill reconciliation before any safe *new* close intent; this release does **not** loosen the existing single-use idempotency to allow blind retries. Broker order acceptance must never be reported as a confirmed fill. Only Recommendation Audit reports newly closed recommendation-linked trades.
