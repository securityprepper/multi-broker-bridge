# R1M PAPER round-trip research — 2026-11-19 04:35 CST

**Scope:** read-only analysis of the **single** Alpaca PAPER account represented by R1M's restricted Percona ledger on www3. This is a partial-account/source research snapshot, **not** all Alpaca PAPER accounts, an independently joined broker FILL activity audit, an audit of all recommendation sources, or a trade recommendation. Existing R1M PAPER source/timers, broker account positions/stops, and LIVE code were not changed.

## Evidence

The query selected unique R1M `OPEN_CONFIRMED` attempts with `outcome='BROKER_FILL_VERIFIED'` and non-null `filled_at_utc`. Closed attempts additionally required both `closed_at_utc` and non-null `realized_pnl`; no accepted-only attempts were counted as fills.

| Entry trading date (America/Chicago) | Ledger-verified filled entries | Closed with gross P/L | Open at query | Gross closed P/L | Positive / negative / breakeven |
|---|---:|---:|---:|---:|---:|
| 2026-11-17 | 20 | 20 | 0 | -$121.67 | 3 / 17 / 0 |
| 2026-11-18 | 20 | 20 | 0 | +$17.32 | 11 / 8 / 1 |
| 2026-11-19 (partial morning) | 13 | 8 | 5 | -$50.33 | 2 / 6 / 0 |
| **Three distinct trading dates** | **53** | **48** | **5** | **-$154.68 gross** | **16 / 31 / 1** |

Closed-lot duration bins (cumulative, in minutes measured from source `filled_at_utc` to `closed_at_utc`): Nov 17 <2:0, <5:1, <10:6, <30:9; Nov 18 <2:0, <5:1, <10:4, <30:12; Nov 19 <2:0, <5:1, <10:2, <30:7. Overall <2:0, <5:3, <10:12, <30:28 of 48.

Gross results by assigned stop arm and closed day (not matched randomized groups across a holdout):

| Stop arm | Nov 17 n / gross | Nov 18 n / gross | Nov 19 partial n / gross |
|---|---|---|---|
| 0.50% | 8 / -$29.91 | 6 / -$29.20 | 4 / -$5.84 |
| 0.75% | 7 / -$67.16 | 6 / +$11.01 | 3 / -$39.54 |
| 1.00% | 5 / -$24.60 | 8 / +$35.51 | 1 / -$4.95 |

Percona `audit_completed_at_utc` was populated on all 48 closed lots, but **no independently joined native broker activity IDs, independently verified fee/slippage ledger, or genuinely untouched 20-day holdout** was established in this run. These are **gross Percona amounts, NOT after-fee forward edges**. The 1% arm's slight three-session gross gain on n=14 is insufficient to recommend a stop change; changing parameters remains prohibited.

At approximately 04:29 CST a GET-only same-account PAPER inventory showed five short positions (AMD, KO, NBIS, NVDA, WDC), zero broker-native open orders. Independent Percona entry fills and quantities matched these symbols; they were not overdue for the original same-day 13:40 CT deadline. A few executor risk checks intermittently returned `QUOTE_UNKNOWN` for KO/WDC; a subsequent authenticated SIP GET returned a fresh KO quote and an older WDC quote, illustrating intermittent premarket quote gaps. Neither alone demonstrated a broker stop trigger or a verified missed forced exit. Leave software-risk and account safeguards unchanged.

## Provenance and reproduction

Data: current www3 `/etc/securityprepper/one-minute-paper-research/percona.json` connection, `paper_attempts` joined to `signals` with source R1M, UTC fill and close timestamps converted using `America/Chicago`, and `research_exit_peaks` for exit evidence. Query pattern:

```sql
SELECT a.symbol,a.filled_qty,a.fill_price,a.filled_at_utc,
       a.closed_at_utc,a.exit_price,a.realized_pnl,
       a.stop_loss_pct,a.exit_reason,a.audit_completed_at_utc
FROM paper_attempts a
JOIN signals s ON a.signal_id=s.signal_id
WHERE s.source='R1M'
  AND a.role='OPEN_CONFIRMED'
  AND a.outcome='BROKER_FILL_VERIFIED'
  AND a.filled_at_utc IS NOT NULL
ORDER BY a.filled_at_utc;
```

The sample must be reconciled to **distinct Alpaca FILL activity IDs** and exact closing FILL activities with order UUIDs and known fees before any performance conclusion. Live broker activity pagination was not available in this run. Retain the minimum **20 distinct trading days** plus untouched forward holdout for changes. Do not report this negative/provisional-performance check as new material edge, and do not repeat it as a notification.

The previously documented rolling-24h R1M daily cap and scan-clock submission cutoff are pre-existing reported blockers; neither was modified or rediscovered here. No broker orders were submitted and no production rule was changed.
