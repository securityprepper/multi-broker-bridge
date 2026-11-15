# Nov 14, 2026 — MBB prior-session tracking lock and adverse-news coverage (RESEARCH ONLY)

## Evidence and exact bounded scope

At 2026-11-14 ~18:35 CST the trusted HTTPS holiday gate was independently refreshed and validated **unpaused**, `status_valid=true`, `calendar_revision=2`, `timezone=America/Chicago`, `calendar_coverage_ok=true`, `published_at=2026-11-14T18:35:00-06:00`, `valid_until=18:37:30 CST`, `next_check_at=2026-11-20T16:07:00-06:00`. Thus read-only research was permitted; weekend market-session eligibility remains a separate protection.

A GET-free, broker-credential-free, read-only replay of the existing authorized systemd `trading-sector-paper-executor.service` journal for **Friday Nov 13, 2026 America/Chicago, before 13:15 CT** found:

| Evidence | Exact count |
|---|---:|
| `SCAN_COMPLETE` records in PAPER_EXECUTION mode | 953 |
| Those recording `gate_allows_new_entries=true` | 953 |
| BUY_WATCH **symbol appearances** (NOT independent orders/trades) | 534 |
| BUY_WATCH appearances assigned a recorded skip reason | 534/534 |
| `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` | 170 appearances / **34 distinct symbols** |
| `NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE` | 355 appearances / **50 distinct symbols** |
| `ENTRY_EXTENSION_BLOCKED` with 2% cap | 9 appearances / **4 distinct symbols** |
| Broker-order intent records emitted in those 953 SCAN_COMPLETE messages | **0** |
| Missing/contradictory JSON scan records in bounded replay | 0 |

The 170 prior-entry appearances occurred from **01:29:43 to 09:30:46 CT**. The 355 news-unknown appearances occurred **09:41:44 to 13:10:44 CT**. The extension rejects occurred **04:53:43 to 07:35:44 CT**. Symbol cohorts overlap; 534 are repeated scan appearances across **50 unique BUY_WATCH symbols**, not 534 qualified trades. The complete 534/534 partition had **zero `NO_FRESH_BID_ASK` reasons on Nov 13**, so the previously documented stale-scan-clock defect does not explain *these* Friday skip appearances.

**Journal intent is not a filled broker order.** An independent credential-scoped GET-only PAPER activities/orders readback was not available to the nonprivileged research shell on this run, and no claim of zero fills at all Alpaca accounts is made. The most recent separately verified broker-fill cohort remained 62 closed PAPER trades on four trading dates (Nov 9–12), not the required 20 distinct sessions.

## Newly demonstrated cross-session lock hazard

Active V1 `multi_broker_bridge/auto_paper.py`, **inspected read-only and not changed**, loads `tracked` from persistent `strategy.sqlite3` by `SELECT symbol,entry_ref,highest,entry_time,entry_qty FROM tracked` without a trading-date filter (around lines 339–341). For an eligible `BUY_WATCH`, `if symbol in tracked` forces the exceptional `_verified_cheaper_reentry` path (around lines 563–569). This can produce `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` instead of treating a symbol that fully exited on a **previous** trading session as an ordinary fresh-day candidate. The only `DELETE FROM tracked` in this V1 file is for a terminal **zero-filled** canceled/expired/rejected entry (around lines 350–367); a fully filled and later sold position is not removed there.

`premarket_policy.eligible_discount_reentry` expressly requires the sell and the proposed reentry to belong to the **same trading session**, with further profit, timing, lower-ask and broker readback requirements. It must stay strict for genuine same-session reentries. But it is not a substitute for an independent new-day eligibility path after a fully reconciled prior-day exit.

**Concrete cross-day check:** MBB AMD was filled BUY/SELL Nov 9 (07:35:42 to 07:37:42 CT, gross -$2.80). Friday Nov 13 it logged **15** `PRIOR_ENTRY...` skips from 03:15–09:30 CT and **13** separate `NEWS_UNKNOWN...` skips from 09:41–13:09 CT. MCHP (actual Nov 11 closed MBB trade) and OXY (Nov 12 closed MBB trade) also emitted a Friday prior-entry skip. These demonstrate that a prior-session source tracking entry can still affect subsequent-day decisions. This identifies a **source-level fresh-day admission defect/risk**, not proof that any missed Friday buy would have been profitable or had broker clearance.

The separately recorded `NEWS_UNKNOWN` gate correctly fails closed when publisher/issuer/licensed-news coverage is not verified. For a Nov 13 fresh BUY its controlling adverse-news window is **Nov 12 00:00 CT through each individual Nov 13 as-of clock**, not 30 days, a rolling 48-hour period, or two trading sessions. Its coverage cannot be bypassed to fix tracking. A change of the stale-tracked handling would not create eligibility for those 355 news-unknown appearances.

## Offline reproducibility and boundaries

Research-only tool `research/v2_mbb_prior_entry_research_20261114.py` reads existing journal JSONL via stdin, never contacts Alpaca, never reads credentials, and outputs aggregate decision counters, unique-symbol denominators, first/last times and completeness status. Regression tests `tests/test_v2_mbb_prior_entry_research_20261114.py` were run in isolated host scratch: **7/7 passed**. Reproduction on authorized host:

```bash
journalctl -u trading-sector-paper-executor.service --since '2026-11-13 00:00:00' --until '2026-11-14 00:00:00' -o json --no-pager | python3 research/v2_mbb_prior_entry_research_20261114.py --day 2026-11-13
```

Do not conflate skip appearances with fills or trade-level after-cost performance. The result is limited to one unit's decision journal, not verified complete account coverage, source-to-fill IDs or actual NBBO executions. This research cannot rank the previous rapid-exit triggers; 48/49 ordinary sell acceptance records in the prior bounded audit lacked stored exit reason. Existing 62 completed PAPER round trips spanned only 4 distinct dates, versus the required >=20 for out-of-sample exit-policy evidence.

**Proposed separate review, not authorized release:** a candidate fix must expire or reconcile `tracked` upon new Chicago/actual trading-session boundary **only after broker-native proof of complete prior-day fills/exits and absent current position/pending orders for the same receiving PAPER account**. Preserve same-day idempotency, discount reentry constraints, unknown-account fail-closed, NEWS_UNKNOWN, last-five-completed-minute direction, quote/spread/extension protections, 13:15 cutoff, 13:40 flat, holiday gate and all LIVE/PAPER boundaries. Add regression cases for prior-day fully closed vs unresolved/partially filled, same-session reentry, Sunday/Monday session mapping, and simultaneous executor exposure before any separately approved PAPER-only deployment.

**No orders placed, no active V1 source, LIVE system, broker state, timer, schedule, stop or holiday control modified.**
