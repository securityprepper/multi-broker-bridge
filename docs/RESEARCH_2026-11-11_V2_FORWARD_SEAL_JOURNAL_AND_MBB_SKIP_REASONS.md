# November 11, 2026 — V2 read-only research: prospective seal integrity + MBB quote skip evidence

## Scope

Owner's Nov 10 research reset remains controlling: **do not retune or activate** retired price-only continuation, gold GLD lag, gap/catalyst chase, 1m shakeout exits, 5-day reentries or trailing strategies. This run only improved the validity of the existing **read-only** prospective seven-sector shadow and independently audited bounded MBB executor journal *diagnostics*. No independent profitable post-signal forward edge is claimed, no new PAPER/LIVE order authorization, no broker orders, no V1 strategy or timers edited, no Gateway restart. Holiday cache was checked on www3 as revision 2, paused=false, next_check_at **2026-11-13 16:13 CST** (valid strictly before boundary absent calendar invalidation); no changes made.

## Prospective forecast first-seen integrity improvement

The previously commissioned separate V2 shadow now emits `sealed_file_sha256` **in its initial systemd journal message after the O_EXCL forecast file has been fsync'd**, at the same run that wrote the 7-sector issue-time forecasts. This gives a separately timestamped, root-owned journal commitment to the immutable forecast's bytes **before** outcomes are available. The distinct later outcome scorer already includes the original file SHA256; a reviewer can compare it against the issuance journal hash to detect edits/backfills. This is an integrity control, not proof of trading profits or a substitute for SEC/news issuer first-seen provenance.

The frozen baseline/peer-confirmed UP/DOWN/ABSTAIN policy is effective **November 12**, not retroactively applied to November 10–11 feature-only records. Shadow capture remains 09:35/09:45/10:05 ET; independent post-outcome scoring at 14:50 ET = 13:50 Chicago. It measures signed movement only **after** the recorded signal, marks flat/tiny as not hits and explicitly counts abstentions/missing outcomes. It uses SIP trade marks and *illustrative* 30/60bp friction, **not** broker-executable NBBO fills. We must not call its after-friction price-mark proxy realized trading profit. Scoring remains research-only. Every prospective forecast date needs original recorded hash, scoring hash and no future-bar availability. Count independent **dates**, not three snapshots as three days, for 20–30+ untouched forward sessions.

The updated collector code and SHA256 assertion test passed along with other V2 tests: **43 tests passed** in isolated host scratch. Installed read-only capture and scoring timers remained enabled and active; this run neither manually invoked a market-data feed with keys nor changed any broker/order services. Previous Nov10/11 schema-v1 snapshot files were not rewritten. No genuine post-policy issued forecasts existed yet on November 11, so no accuracy or trading GO is reported.

## Independent bounded MBB skip-reason audit: Nov 10 vs Nov 11 partial

Created a pure decoder accepting **read-only systemd journalctl -o json**, assigning America/Chicago day from the journal's trusted realtime timestamp and outputting **only** redacted aggregate scan metrics. It deliberately drops account IDs, cash/buying power, client order IDs, broker positions, raw quotes and unknown reason details. Four focused parser/aggregation tests passed, included in the 43-test run. The bounded sample covers November 10 (complete journal date) and November 11 **only through approximately 12:40 CST**:

| Observation | Nov 10 | Nov 11 partial |
|---|---:|---:|
| SCAN_COMPLETE records | 1,622 | 896 |
| Candidate appearances | 687 | 557 |
| BUY_WATCH symbol appearances | 577 | 551 |
| Scan records containing a quote skip | 72 | 0 |
| NO_FRESH_BID_ASK symbol appearances | 456 | 0 |
| PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY symbol appearances | 108 | 536 |
| Reported order objects | 24 | 14 |

These are **repeated per-scan appearances, NOT unique stocks, trades, accepted broker orders or fills**. A previously documented quote-age defect compared newly returned SIP quotes to a stale scan-start time. Current observed active V1 `auto_paper.py` source (last-modified Nov 10 22:24 CT) **already uses a new `quote_received_at` immediately after the GET**, applying `0 <= receipt-quote_time <= 100s`, noncrossed/positive quotes and <=1% spread. This research run did not modify active V1; provenance of its independently applied update was not audited. Nov11 zero quote-skip appearances after this change are encouraging **diagnostic evidence**, but NOT proof that all 456 Nov10 occurrences had this same underlying root cause: their original raw quote-response timestamps were never persisted. It also cannot prove otherwise qualified orders would have filled or earned a profit.

The Nov11 increased skip count is entirely `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` in this bounded journal. That is consistent with the strict owner-approved reentry guard, including the rule to **never automatically re-buy higher after a losing stop**. It is not automatically a broker failure or reason to bypass the guard. Evaluate any prospective changes only after broker-verified account-specific fills, executable spread, post-signal after-fee P&L and independent dated samples. MBB order objects in the log are not fill confirmations; Recommendation Audit alone reports closed trade outcomes. The historical Nov9 03:18 AMD exact skip remains **unprovable** from missing historical detailed diagnostic fields, so these later reasons must **never** be back-projected onto Nov9 as an exact explanation.

## Data gaps and next independent work

- The new seven-sector forecast policy begins November 12; it has **zero** genuinely untouched completed forward days as of this report. A timer's enabled state is not proof a later file succeeded; verify issuance-time journal hash and separate outcome score after the close.
- Quote-level contemporaneous response receipt evidence and actual Alpaca PAPER fill/commission matches are still needed before attributing V1 quote rejects or claiming trade profitability.
- Fresh headline/issuer original-text first-observed timestamps and independent numeric guidance/analyst revisions remain absent in the historic licensed cache. No new catalyst or automatic news strategy qualifies.
- Recommendation-to-PAPER router remains disabled; quote/protection/position hard gates concern only the receiving broker and no other-broker inventory can block otherwise qualified Alpaca PAPER trades. No changes here.

Research files: `research/v2_auto_paper_scan_reason_audit_20261111.py`, `tests/test_v2_auto_paper_scan_reason_audit_20261111.py`, `research/results/v2_mbb_scan_reason_daily_20261111.json`; prospective capture SHA256 enhancement to `research/v2_forward_only_sector_shadow_20261109.py` with tests in `tests/test_v2_seven_sector_forecast_and_score_20261111.py`. **NO GO on new orders or predictive notifications.**
