# November 17, 2026 — V2 mandatory 13:40 CT flatten is independently delayed until 14:00 CT (research-only)

**New safety finding, distinct from previously reported signed-short-quantity stop bypass.** On authorized www3, after strict fresh root-owned America/Chicago holiday-gate verification (schema 1, revision 2, status_valid, coverage, unpaused, published within 150 seconds), read-only review of `/opt/securityprepper/direction-paper-executor/direction_paper.py` showed a second independent V2 PAPER exit defect:

```python
local=now.astimezone(CT)
near_cutoff=local.weekday()<5 and local.hour>=14 and local.hour<20
why=('PROFIT_TARGET' if change>=Decimal('1.0') else
     'STOP_LOSS' if change<=Decimal('-1.0') else
     'SESSION_FLAT_1400_CT' if near_cutoff else None)
```

The owner requires **13:40 CT mandatory flatten** and **14:00 CT latest flat verification**. Even after repairing signed quantity / availability handling, this installed branch cannot trigger a *time-based* V2 exit between 13:40 and 13:59 CT. It must not be treated as meeting the existing hard-flat condition.

## Evidence

- A broker **GET-only**, exact expected-account-matched Alpaca PAPER readback at **2026-11-17 11:28:24 CT** confirmed six current V2 short positions **AMD -4, INTC -36, NVDA -13, WDC -7, SNDK -2, TSM -5**, and **zero open orders**. Independent existing V2 SQLite signal/order ledger read-only join verified those exact six are V2 `OPEN_CONFIRMED` `BROKER_FILL_VERIFIED` unclosed entries. This is **not** six new shorts; their exposure and their signed-quantity flaw were previously reported, and are not repeated as new events.
- Isolated broker-free AST regression evaluated the exact installed `near_cutoff` expression on Tuesday, November 17: **13:39 false, 13:40 false, 13:50 false, 13:59 false, 14:00 true**.
- The independent MBB `paper_time_exit._positive_whole_qty` refuses `side="short"`; the Recommendation PAPER `exit_guard.exclusively_owned` also refuses shorts. The independently managed R1M close is ownership-limited to R1M, not V2. Thus, none of these examined 13:40 safeguards covers the six V2 shorts. This does not assert exhaustive absence of all other possible infrastructure.
- The original signed short quantity check (`Decimal(pos.qty) != Decimal(filled_qty)`, and `available<=0`) independently bypasses V2 profit/stop exits, which is already documented in the two previous November 17 safety reports; do not conflate the two defects.
- Installed source SHA-256: V2 `d4b7c89bf54302f2a7f3a2463b66b5a6d401ffd41d3cab1b42c9a524a3fd7d13`, MBB time exit `5970169afacad188f130e975ee5371676684bf94669a17c9ab5b06ffc35f9bd9`, recommendation guard `f10f2845274259b9103f88aa833a6b6be34a24a8ed2ce2bdf0cadc6e9c3c97ec`.

## Remediation boundary

A **separately authorized, narrowly scoped PAPER safety release** must correct both (1) signed short quantities/available quantity comparison and (2) **13:40 CT** time-based exit eligibility, with independent same-account, exact filled lot, open-order and no-duplicate checks, cancellation/fill-race and partial-fill handling, verified broker receipts and price/session guardrails, plus post-deployment readback. Do not allow negative qty handling to accidentally close an unrelated strategy's net position. Any emergency exit must remain safe if market/quote or broker state is unknown. Keep 13:15 CT last entry, 13:40 hard flat and 14:00 latest flat verification. Maintain all other safety gates and LIVE prohibitions. No PAPER/LIVE orders were placed; no V1 source, timers, stops, services, permissions, or production files were changed by this investigation.

**Evidence:** broker GET-only readback, code inspection, deterministic AST regression. **Not evidence** of profitability, after-fee forward alpha or a filled closing order.
