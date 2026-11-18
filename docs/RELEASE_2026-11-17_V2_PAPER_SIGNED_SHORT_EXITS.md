# V2 PAPER short-protection safety release — November 17, 2026

**Owner authorization:** The owner explicitly requested “Investigate the cause and fix it” after reports of six unprotected Alpaca PAPER shorts. Narrow PAPER-only safety code release, not authorization for manual broker trading, LIVE changes, or any strategy parameter relaxation.

## Scope, root cause, and current state

- Authorized www3 root-owned holiday gate verified on November 17 at ~20:58 CT, schema 1, `status_valid=true`, `paused=false`, timezone America/Chicago, revision 2, fresh `published_at` and `valid_until`, future `next_check_at`.
- Exact expected-account-matched Alpaca PAPER GET-only snapshot at **2026-11-17 20:58:52 CT** reported six short positions AMD -4, INTC -36, NVDA -13, SNDK -2, TSM -5, WDC -7; **0 working open orders**. All six matched independent existing V2 `OPEN_CONFIRMED` `BROKER_FILL_VERIFIED` unclosed fills in `/var/lib/securityprepper-direction-paper/state.sqlite3`.
- Installed `direction_paper.py` previously compared signed short broker quantity (`-4`) directly against positive broker-filled quantity (`+4`), then rejected negative `qty_available`; every short bypassed profit, stop and mandatory exit.
- The time-flat expression was only true at **14:00–19:59 CT**, missing the mandated 13:40 cutoff and becoming false again at 20:00 CT even for overdue positions. Thus forced liquidation was never applied to these shorts.
- Duplicates returned an incomplete dictionary with no `notification` key, causing `KeyError` in the run summary when recent source handoffs repeated a reserved event.
- `decide_and_attempt` also treated negative short availability as if no position existed, suppressing an independently sourced close-only bearish reversal.
- No new after-fee positive trading strategy edge is claimed.

## Installed PAPER-only correction

Original SHA-256 of `/opt/securityprepper/direction-paper-executor/direction_paper.py`: `d4b7c89bf54302f2a7f3a2463b66b5a6d401ffd41d3cab1b42c9a524a3fd7d13`. New, verified installed SHA-256: `f4ac3f1747a8e1e6c21629fd5a9480f309af44bafb965fbe288125f7104a26a3`.

The patch introduces `owned_whole_position_qty`: exact verified whole-lot equality to the *signed* same-account broker net position and sufficient same-signed available quantity, with both long and short side verification. Mismatches, fractional, missing, stale or unknown state cannot authorize an exit. All preexisting open-order and client-order idempotency checks remain.

A sticky `session_flat_due` uses the original signal's 13:40 CT deadline (does not become false after 20:00 or on the following day). When due, `SESSION_FLAT_1340_CT` takes precedence over the price-only stop or profit target, with its distinct deterministic client-order ID. `paper_exit_window` permits new close orders in 04:00–20:00 ET weekday premarket, RTH and after-hours only; **no new overnight order at 20:00–04:00 ET while eligibility is unverified**. R1M, MBB and other independent executor code were not changed. The V2 and OWNED PAPER signals share this direction-paper risk-exit function, so OWNED exits also receive the signed-quantity and 13:40 safety correction; OWNED entry strategy parameters were not modified.

V2 new entries are prohibited outside 04:00 ET to 13:15 CT and while earlier verified V2 entries have not been confirmed closed. Duplicate handoffs now return all required response fields with `notification=NO_POST_NO_TRADING_ALERT` and zero new attempts.

**The code does not install broker-native stops or guarantee fill.** Actual close attempts remain controlled by the existing one-minute PAPER service, broker account identity, live position/open-order readbacks, fresh broker-appropriate quotes, spreads, and a single-use persisted order-intent ledger. No manual Alpaca PAPER or LIVE order was submitted by this release.

## Test and commissioning evidence

- **44 broker-mocked regression tests passed** after deployment: 33 existing tests (with research fixture updates to real signed short quantities and permissible weekday premarket time) plus 11 new targeted signed-short, cutoff, duplicate, ownership, unavailable quantity, open-order, no-retry and market-session tests.
- A **copy of the real V2 SQLite ledger**, reconciled in read-only mode with the six actual signed broker positions, produced **six distinct simulated buy-to-cover intents** at 03:05 CT the next trading day, each `RISK_EXIT_SESSION_FLAT_1340_CT`; a second mock run produced zero duplicates. Those were **simulated broker requests against a fake broker**, not actual Alpaca fills or execution.
- Atomic installation under the existing broker-execution flock, preserved both service/timer configuration and enabled status, and installed a root-protected rollback archive `/var/lib/securityprepper-v2-paper-safety-release-20261117/`.
- Naturally scheduled PAPER executor at **21:07:33 CT** returned `Result=success`, `risk_exits=[]`, `order_attempts=0`. This was during the conservatively excluded 20:00–04:00 ET session; it is not a completed closure.
- Further broker GET-only checks around **21:10 CT** showed fresh BOATS prices with spreads below the configured ceiling for each symbol, but the paper broker Asset GET returned `overnight_tradable=None` and `overnight_halted=None`. Consequently there was no verified eligible overnight path for these specific positions: do not treat a fresh BOATS quote alone as permission for an overnight protective order.
- No position, order, stop, LIVE permission, V1/MBB source, holiday publisher, timer cadence or Gateway was changed by the release. All six shorts were **still open at the verified pre-release inventory readback**. A post-eligible-session exact paper broker order and FILL readback is still required before declaring liquidation achieved.

## Reproducible artifacts

- Exact source delta: `research/v2_paper_signed_short_safety_release_20261117.patch`
- New tests: `research/test_v2_paper_signed_short_safety_20261117.py`
- Original prior failure records: `docs/RESEARCH_2026-11-17_V2_1340_FLAT_DELAY_SHORTS.md`, `docs/RESEARCH_2026-11-17_V2_DUPLICATE_SIGNAL_KEYERROR.md`, `docs/RESEARCH_2026-11-17_V2_SIX_SHORTS_POST_REGULAR_CLOSE_1625CT.md`

Safety follow-up: During the first eligible premarket, check correct account, positions, working orders and fills; do not report accepted limit orders as verified closed positions. If quotes/broker inventory/eligibility are incomplete, fail closed on new orders and flag the unresolved overnight exposure for owner intervention. Keep previous protective safety rules intact.
