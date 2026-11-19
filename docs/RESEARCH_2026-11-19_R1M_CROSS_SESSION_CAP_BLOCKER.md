# November 19, 2026 — New R1M PAPER 24-hour cap crosses actual trading-session boundary

**Status:** Verified code-level implementation blocker, NOT a verified missed filled trade and NOT a broker safety failure. Research-only, no PAPER/LIVE order, stop, account, unit/timer, authorization, execution source or production change.

**Observation:** At 01:37 CST, the current root-owned holiday gate `/var/cache/securityprepper-holiday/task-gate.json` passed schema v1, status_valid=true, America/Chicago, calendar revision 3300 with coverage, published-at freshness <150 s, valid-until future, next_check_at 2026-11-20 16:07 CST, and unpaused.

## Verified production source and account-specific denominator

Installed `/opt/securityprepper/direction-paper-executor/one_minute_research.py`, SHA256 `350a8646254cfd2ad1381002a43af30fe0d081ad5c99b81d2c4f9a6fbc302285`, sets `MAX_ENTRIES_PER_SESSION=20` and `MAX_PER_SYMBOL_PER_SESSION=2`. However `research_open_count(db,now)` computes `ses=session_key(now)` but does **not** use `ses`. The two count queries restrict entries to `s.signal_at_utc >= now - timedelta(days=1)` instead of the *current R1M entry session*. Thus yesterday's POST-attempted entries consume today's session cap even when the previous positions are closed.

Independent read-only Percona source join of `signals` and `paper_attempts` found **20** uniquely identified R1M `OPEN_CONFIRMED` broker POST attempts / verified paper fills on November 18, with original signal timestamps **09:04–12:11 UTC** (03:04–06:11 CST). At the *next eligible entry window* Thursday November 19 **03:00 CST / 04:00 EST**, the current rolling-24h SQL would still count all 20, reaching the configured cap immediately, while a genuinely new session contains **zero** POST attempts at its start. The per-symbol rule also carries across days: **CRWV, MU and SNDK** each have two prior-session POST attempts, potentially preventing a first new-session entry for those symbols until yesterday's attempt ages out. The restriction starts lifting as November 18 timestamps age past 24 h and may interact with new POSTs. No claim that a qualifying signal or broker order was actually missed on November 19 is made.

The observed `RESEARCH_DAILY_CAP_REACHED` overnight scan decisions are not independent missed opportunities because R1M's correct post-November-18 safety gate prohibits BOATS/overnight **new entries**. The newly reproduced failure applies to the next eligible weekday 04:00 ET SIP entry window.

## Broker-disabled regression

Exact current `r.research_open_count` imported from the installed executor, with 20 **previous-session-only** distinct mocked POSTs plus verified-closed test ledger rows, returns `count=20` at the next day's 04:00 ET. A proper current-session-bounded count returns 0. A second test demonstrates the stale 2-per-symbol limit. Both tests **PASS** as reproductions in isolated temporary SQLite; they do not contact brokers or alter Percona or active execution.

Test: `research/test_r1m_rolling_24h_session_cap_20261119.py`. This is *not* a test of a commissioned correction, and the existing regression outcome is not a permission to deploy.

## Narrow PAPER-only remedy proposal — NOT RELEASED

Replace the count and per-symbol filters with the true local `America/New_York` entry session bounded by **04:00 ET of the current trading date** through the following 04:00 ET, converted to aware UTC endpoints. Since the installed R1M safety gate only admits weekday SIP entries from 04:00 ET until before 13:15 CT, do not reauthorize BOATS, nighttime, weekends or holidays as a side effect. Preserve the fixed per-session total cap 20, per-symbol cap 2, live-concurrent positions cap 10, original same-broker quote/spread and owning-broker inventory guards, holiday gate, adverse-news clearance, stop arms, first-five-completed-minute bars, 13:15 entry cutoff and original-fill-based sticky 13:40 flat.

Add regression cases for 03:59:59 vs 04:00 ET, daylight saving boundaries, two distinct sessions, repeat symbol across sessions, same-session 20/2 enforcement, older active lots still counted in the **separate** concurrent-open-position gate, and filled/accepted vs merely reserved attempts. No production code or broker execution may change without separately authorized PAPER release and passing tests.

**Related research, not a GO:** 40 other verified closed R1M PAPER round trips exist across just two actual fill dates (Nov 17–18), with gross realized P/L -$104.35 (14 positive, 25 negative, 1 zero). Fees/net P/L are not established; 2 distinct broker days fail the 20-day requirement. Do not interpret the proposed cap correction as evidence that more entries would be profitable. Recommendation Audit exclusively notifies closed recommendation-linked trades.
