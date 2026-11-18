# Nov 18 2026 — Newly reproduced R1M PAPER after-cutoff entry gap

**Category:** new pre-entry safety implementation blocker. **Scope:** read-only evaluation on www3, no broker POST, source modifications, timer changes, LIVE changes, or production release.

## Verified holiday permission

At 2026-11-18 05:33:29 CST, the current root-owned `/var/cache/securityprepper-holiday/task-gate.json` validated schema v1, status_valid, America/Chicago timezone, revision 2, coverage, current publish age 28 seconds, unpaused, valid_until 05:35:31 CST, and next_check_at 2026-11-20 16:07 CST. Historical prior observations were not used as authorization.

## New safety defect (independent of V2 short-quantity and terminal-order issues)

The running `/opt/securityprepper/direction-paper-executor/one_minute_research.py`, `research_open()`, checks:

```python
local=now.astimezone(CT)
if local.weekday()<5 and (13<=local.hour<19) and (local.hour>13 or local.minute>=15):
    return [],'RESEARCH_ENTRY_CUTOFF_BEFORE_MANDATORY_2PM_FLAT'
```

This **fails open from 19:00 CT onward** even on weekdays because `local.hour<19` becomes false. The same program's `feed_for(now)` **permits BOATS from 20:00 ET (19:00 CT)**, so the scan/entry code can reach the unprotected late-entry path. It also fails open during the early-overnight 00:00–02:59 CT interval, and on weekends, even though other feed gates may separately block most such opportunities. This is not a claim that a new after-hours order was actually submitted.

The required policy is **no new special strategy entry after 13:15 CT and no overnight BOATS entries**. Source code has a gap, although other broker/news/price gates may sometimes block a candidate. R1M's time-based exit handles verified positions separately; it does not repair a policy-violating new entry.

## Read-only regression and bounded broker evidence

`research/test_r1m_after_1315_cutoff_20261118.py` extracts and evaluates the **exact installed AST condition**, not a presumed policy. Twelve deterministic America/Chicago cases demonstrate **seven** windows in which a prohibited new entry passes the cutoff; a research-only replacement predicate blocks all seven while preserving 03:00–13:14 CT weekday premarket/day entries. No broker or real executor call was made.

A read-only query of the distinct Percona R1M PAPER `OPEN_CONFIRMED/BROKER_FILL_VERIFIED` entries found **35 filled entries since November 14 and zero fills after 13:15 CT** in that bounded period. Thus **the flaw is verified in current code, but an actual after-cutoff fill is not established**. At 05:31 CST, the account-matched PAPER inventory showed three new R1M shorts, ASML -1, PLTR -12 and TSM -5, with no broker-native working orders. Each had matching source and filled entry in the independent R1M Percona ledger and is managed by its separate software-exit routine. This study does **not** classify those ordinary pre-13:15 entries as a new unprotected-position incident.

## Proposed narrow remediation — NOT deployed

Before any PAPER release, replace the cutoff with a **positive eligibility window**, for example:

```python
if (local.weekday()>=5 or local.time()<dt.time(3,0)
        or local.time()>=dt.time(13,15)):
    return [],'RESEARCH_ENTRY_OUTSIDE_ALLOWED_0400_ET_TO_1315_CT'
```

Also require the actual session to be `SIP` / permitted 04:00 ET onward, a fresh root-owned holiday gate, all independently verified negative-news, extension, quote, spread, account/positions/open-order, idempotency and buying-power safeguards. Preserve the existing independent R1M software stop and 13:40 CT flat, no V1/LIVE modifications, and verify broker-native fill/readback before declaring a position closed.

**Research source:** installed code and exact test on www3, separate R1M Percona records, account-matched recent PAPER inventory. All credentials omitted. **No production or broker mutation**.
