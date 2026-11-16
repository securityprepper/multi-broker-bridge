# November 16, 2026 — newly isolated R1M PAPER admission failure (research-only)

**Status:** Exact exception cause reproduced independently; **active executor NOT changed**. No broker POST/short/LIVE actions from this research.

## Fresh www3 observations

On Monday November 16, 2026, between 07:05 and approximately 12:34 America/Chicago, systemd journal events for `securityprepper-one-minute-paper-research.service` showed 330 application outcomes: 287 `RESEARCH_FAIL_CLOSED` with `error_type=ProgrammingError` and 43 `R1M_EXECUTED_PAPER` with zero qualified signals reported on sampled successes. The service runs with root commissioning marker plus `--execute`, so failed attempts suppress genuine R1M PAPER experimentation. This has **not** been demonstrated to affect independently commissioned MBB/FDR PAPER or any LIVE broker.

The R1M state database at inspection had **302** timed prospective signal rows but **0** `signals.source='R1M'` and **0** R1M paper attempt rows. Retained timing events still record candidates, but do not constitute accepted orders or fills. The observed exception appears before an R1M broker POST.

## Proven exact cause

`/opt/securityprepper/direction-paper-executor/one_minute_research.py` assigns a Python `decimal.Decimal` to `signal['vs_close_pct']` when a completed previous RTH close is available:

```python
signal['vs_close_pct']=round((Decimal(str(stat['last']))/reference-1)*100,4)
```

Later, `direction_paper.save_signal()` passes that value as the **tenth SQLite INSERT parameter** (the `vs_close_pct` column), but `sqlite3` has no native binder for `decimal.Decimal`. The exception is:

```
sqlite3.ProgrammingError: Error binding parameter 10: type 'decimal.Decimal' is not supported
```

The originally reported service wraps the exception without logging the SQL exception text, so a read-only copy-based replay was necessary. A 2026-11-16 12:38 CT replay on an **in-memory SQLite copy** and fresh market-data GETs reproduced exactly the same exception, while prohibiting all broker interactions. The source's existing entry-extension risk guards never receive a valid persisted signal in this path.

## Isolated test evidence

`research/test_v2_r1m_sqlite_decimal_bind_20261116.py` uses only in-memory SQLite plus the installed `direction_paper` code. All three tests passed: the candidate extension has Decimal type; current `save_signal` fails to bind parameter 10; explicit finite native-float conversion permits the signal INSERT.

**Minimal proposed PAPER-only correction** (subject to separate release authorization, not deployed by this research):

```python
signal['vs_close_pct'] = float(round((Decimal(str(stat['last'])) / reference - 1) * 100, 4))
```

Do not remove prior-RTH-close requirements, threshold extension vetoes, negative-news checks, receiving-broker quote/buying-power/positions/orders protections, entry cutoff, emergency exit controls or short permissions. Add a regression to the actual one-minute executor tests that exercises the real candidate path with an existing prior RTH close and a temporary database, and assert that after admission normal extension guards still block extended candidates. Validate in a non-order sandbox before separately approved PAPER commissioning.

## Authorization boundary

The Task - Trading Strategy Research owner instruction prohibits changing active V1 PAPER/LIVE execution, unit files, timers, source, services and broker permissions. This research only wrote this isolated test and report on the V2 research branch. Deployed production executor remains unchanged, failed and fail-closed where this path is encountered. It requires a **separately authorized PAPER-only executor correction** from its owner; a prior authorization to repair the distinct news-source collector does not implicitly authorize this change.

No robust after-fee forward edge is established by this incident. Continue auditing broker accounts/sources independently; a bounded inventory of one Alpaca PAPER account does not prove all accounts.
