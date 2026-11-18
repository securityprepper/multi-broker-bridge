# November 18, 2026 — V2 PAPER terminal exit reconciliation: isolated research candidate

**Research only; NOT commissioned.** The previously reported terminal-limit retry and partial-fill defect remains unresolved in the active V2 PAPER executor. No LIVE/PAPER orders were submitted, and no active V1/V2 production code, services, timers, holiday gates, stops, alerts, or account permissions were changed by this research.

## Provenance and scope

The owner-authorized November 17 PAPER protection patch is installed in `/opt/securityprepper/direction-paper-executor/direction_paper.py`, SHA-256 `f4ac3f1747a8e1e6c21629fd5a9480f309af44bafb965fbe288125f7104a26a3`. Its already reported limitation is that a deterministic limit exit is never retried after broker-confirmed terminal zero-fill, and terminal partial fills were incorrectly labeled unfilled. Root-owned www3 task gate was freshly validated unpaused during this November 18 research run; the historical Nov 13 snapshot was not used.

A candidate correction was written **only** to a separate research working directory. It retains exactly-once unknown order handling and does not bypass same-account, signed exclusive-position, live working-order, quote, session, 13:40 flat or holiday protections.

## Candidate behavior

- Broker terminal statuses `rejected`, `expired`, `canceled`, `done_for_day` become `BROKER_ORDER_TERMINAL_UNFILLED` **only when the broker explicitly reports cumulative `filled_qty=0`**, with matching symbol, side, client ID and broker order ID. Missing, malformed, negative, excessive or inconsistent values remain UNKNOWN and do not authorize retries.
- Terminal partial or unexpectedly full cumulative fills receive `BROKER_TERMINAL_PARTIAL_UNRESOLVED`, retaining the observed filled quantity and average price. Such a state is not evidence of a fully closed lot, and remains ineligible for automatic retry until independent fill/activity attribution and remaining position reconciliation are implemented.
- A previously confirmed terminal-zero-fill outcome may advance to one distinct deterministic retry generation only after another matching broker order GET, fresh same-account position/readback, exact strategy-owned signed quantity, and zero working orders. Previous ambiguous, accepted or partial exits block retries; the model has at most three retry generations (four attempts including the original).
- This is a **candidate mechanism**, not a declaration that every race, cancellation or partial-fill case has been solved, nor proof of broker acceptance or actual fill. In particular, cross-reason unresolved exit intents and journal/fill race coverage need independent tests before any release.

## Reproducible testing

An isolated, credential-free broker mock and disposable SQLite ledger were used. **61/61 tests passed**, comprising 17 new terminal-retry scenarios and 44 existing direction, signed-quantity, cutoff, source and audit cases with realistic fixture fields. Tested strict zero-fill verification, canceled/expired/done-for-day/rejected states, partial 2-of-4, unknown broker state, mismatched account/symbol/side/order ID, uncertainty, active competing orders, mismatched position, retries capped and basic quote failure. No native PAPER submission or actual broker FILL was tested.

Files:
- `research/v2_terminal_exit_retry_candidate_20261118.patch`
- `research/test_v2_terminal_retry_candidate_20261118.py`

**No production release approval.** Preserve the ongoing 13:40/14:00 special-strategy liquidation target. Close verification still requires broker-native FILL and an account-matched flat manifest. The previous six PAPER shorts were again present in the 01:31 CT GET-only snapshot on November 18, with no working orders; this is an unchanged exposure, not a fresh new safety event.
