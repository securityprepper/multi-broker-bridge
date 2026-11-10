# November 10, 2026 — verified MBB PAPER RTH churn and session ownership (research-only)

**As-of:** 10:38:46 a.m. CST (2026-11-10T16:38:46Z). **Scope:** authorized GET-only exporter snapshot `/var/lib/securityprepper-paper-inventory/current.json` and a separate read-only MBB executor journal sample. No broker API POST, service/timer change, production checkout edit, DB mutation, or LIVE permission change by this research.

## New factual result: 8 closed MBB PAPER lots, only 1 winner

The broker-verified read-only snapshot covered the Chicago Nov 10 session and reported `recent_orders_complete=true` with a lookback beginning Nov 7. There were 18 filled orders created in this session, all with MBB client-order prefixes: 10 buys, 8 sells, zero other-writer orders in this bounded snapshot. Eight MBB buy/sell pairs matched chronologically by symbol/whole-share quantity; 7 closed at losses and 1 at a gain, gross **-$74.45 before commissions/data costs**. The first seven losses were ZS -$5.30, RPD -$20.40, MPC -$6.25, WMB -$8.70, PSX -$19.53, BKR -$3.28 and TENB -$18.47. FANG subsequently sold for +$7.48, reducing the net loss from -$81.93 to -$74.45. Median time between the observed buy/sell fills was approximately 12.98 minutes; **do not infer a specific SELL rule from the durations**. There were two remaining account long positions, COP 14 and TXN 6 shares, matching the unmatched MBB buy quantities at this instant; no open orders. Interim gross realized P&L is not final daily or after-fee P&L, and no end-of-day flat verification is claimed.

This supersedes the earlier 09:37 CST interim snapshot showing 6 losses and -$63.46. It does not contradict the earlier snapshot: both broker position counts and outcomes changed during the session. No earlier speculative hold-to-13:40 proxy may be substituted for executable fills.

## Concurrent entry quality and remaining known defect

Independent `trading-sector-paper-executor.service` journal sampling from **09:25–10:35 CST** returned 82 `SCAN_COMPLETE` records, 104 candidate appearances (not independent opportunities), 68 `NO_FRESH_BID_ASK` skip observations, 9 `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` observations, and 6 journal order objects for SELLs. Quotes/entry states are changing; the session tracking defect persists, but it did not prevent all buys. The skip totals should not be represented as all broker opportunity counts, and exit reasons were not recorded in the summarized order receipts.

Read-only source review verified a separate `paper_time_exit.timed_flatten` with a **13:40 Chicago** mandatory exit start and 14:00 escalation deadline. The later 13:55 fallback cancellation code is not evidence that the 13:40 guard is absent. However, the timed exit still relies on a persistent `tracked` ledger and aggregate symbol quantity, which is not sufficient proof of share provenance across strategies. Do **not** clear historical rows or deploy the research prototype to unblock entries; this could enable an incorrect cross-strategy sell. Independently complete FILL-activity UUID/order UUID/writer reconciliation and live DB concurrency tests under a separate reviewed PAPER-only release.

The exact **November 9 03:18 CST AMD skip** remains unrecoverable from the historical diagnostic record. The 03:18-started one-minute bar was unfinished at 03:18:40, so that SIP quote cannot alone establish an executable contemporaneously qualified trade. Do not assign a guessed reason.

## New reproducible bounded auditing tool

`research/v2_paper_rth_churn_observed.py` reads **only an existing local JSON file**. It enforces broker-verified PAPER, complete recent-order coverage from Chicago midnight, unique client-order IDs, filled quantity/average prices, timestamp chronology, matching same-writer FIFO lots and account position quantity reconciliation; ambiguity fails closed. No credentials, account IDs or client-order identifiers are output. Neither FILL-activity UUID lineage nor the exact exit decision reason is asserted. A matching aggregate position balance is necessary but not sufficient proof of writer ownership. 

Targeted synthetic tests **14/14 PASS** locally and from the published GitHub source on authorized www3 scratch `/tmp/v2-run11-paper-churn`. The same published program was executed against the live-updating GET-only exporter snapshot, producing the frozen interim JSON `research/results/v2_mbb_rth_broker_churn_2026-11-10_1038CST.json`. Its source, output and tests are research-only, not a strategy or monitoring service; it places no orders.

## Validation limits and next safe work

No prospective sector forecast was sealed in the 09:35/09:45/10:05 ET shadow files: these still contain features with null classifications. They cannot count toward the desired >=80% independent **post-signal** direction accuracy. A winning full-day direction label does not imply positive future continuation. The only prospective forward testing supported today is feature-availability/causality, not forecast hit rate. Continue with precommitted future sealed directional classifications and 20–30+ new days, real executable SIP/BOATS bid/ask and news timestamps, after-fee matched fills, strict stock -2.5% including -1pp/15m research, and two-sided daily outcome review after the close.

**Risk posture:** No new V2 BUY/SHORT/PAPER execution authorization, no predictive push from raw price thresholds, no changes to V1 PAPER/LIVE, broker orders, host timers, 13:15 entry cutoff, 13:40 exit/14:00 verification, or holiday gate. Existing held positions remain governed by V1 safeguards. This is a research snapshot, not an instruction to change them.
