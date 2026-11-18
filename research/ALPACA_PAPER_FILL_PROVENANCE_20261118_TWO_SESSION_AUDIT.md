# November 18, 2026 — distinct Alpaca PAPER broker FILL provenance, November 17–18 (research-only)

## Scope and safety

Read-only research audit performed on November 18 around 08:30–08:40 America/Chicago, after validating the current root-owned holiday task gate on www3 (schema 1, America/Chicago, revision 2, published 3.9 seconds earlier, unpaused, valid future boundary). This used only authenticated exact-account-matched Alpaca PAPER `GET` requests and `SELECT` from existing R1M Percona and V2 SQLite ledgers. No PAPER or LIVE broker orders, timers, exits, stops, V1 production code or notifications were changed. It is **not a new successful strategy signal**.

## Broker-source coverage

- Two pages of broker `/v2/account/activities/FILL` from November 17 00:00 UTC onward returned **168 DISTINCT FILL activity IDs** across **94 distinct broker order UUIDs**, with successful pagination exhaustion for this bounded period.
- Independent source mapping of these 94 order UUIDs: **80 R1M PAPER order UUIDs**, **12 V2 PAPER order UUIDs**, and **2 existing off-hours-stop SPY PAPER test order UUIDs**. No unexplained broker UUIDs within this period and queried account. This does **not** establish complete coverage of any other Alpaca account or earlier history.
- All **80 R1M order UUIDs** had broker FILL activity records matching Percona recorded filled quantity and weighted fill price (within $0.02); **40 R1M orders** had more than one distinct FILL activity. R1M entry/exit matching spans **40 round trips**, 20 entry orders and 20 closing orders on each November 17 and November 18.
- All **12 V2 order UUIDs** had matching signed-strategy fill quantities and weighted prices, across **25 distinct broker FILL activity records**, including **8 multipart V2 orders**. These comprise the six documented November 17 shorts and their six premarket November 18 buy-to-cover exits.
- The 2 remaining UUIDs were the already-documented one-share SPY off-hours PAPER commissioning test, one opening and one closing FILL. Its result was not audited here.

## Anti-churn and gross realized return

All figures below are **ledger gross dollars before explicit fees, financing and any independently unmeasured execution costs**; do not label them after-fee or a forward-trading edge. Recorded fill prices were corroborated by actual distinct broker FILL activities, not modeled OHLC.

| Entry day (America/Chicago) | Strategy | Completed round trips | Gross win count | Gross P/L | Exits under 2 / 5 / 10 / 30 min | Verified attributed exit reasons |
|---|---|---:|---:|---:|---|---|
| Nov 17 | R1M | 20 | 3 | -$121.67 | 0 / 1 / 6 / 9 | 7 confirmed turn; 5 each at 0.50% and 0.75% stop; 2 at 1% stop; 1 $1-per-share momentum-fading profit |
| Nov 18 through 08:30 CT | R1M | 20 | 11 | +$17.32 | 0 / 1 / 4 / 12 | 11 confirmed turn; 6 $1-per-share momentum-fading profit; 2 at 0.50% stop; 1 early reversal |
| Nov 17 to Nov 18 | V2 shorts | 6 | 0 | -$550.22 | n/a (overnight) | 6 `RISK_EXIT_SESSION_FLAT_1340_CT` from installed repaired PAPER exit manager, actually filled in Nov 18 premarket |

R1M total observed here is **40 completed PAPER positions across only two distinct trading days**, gross P/L **-$104.35**, not 40 independent market sessions. The V2 short losses were consequences of the previously known and previously reported signed-short/late-liquidation safety defects; they are **not a new distinct safety failure**. Recommendation Audit retains ownership of recommendation-linked close notifications.

## Interpretation and next steps

1. No positive robust after-fee forward edge or 20+ independent-session result is established. No active strategy parameter alteration follows.
2. Keep the exact broker FILL activity ID `→` broker order UUID `→` per-strategy intent `→` matched filled lot path in future research. A broker order may have multiple FILL activity IDs; deduplicate by FILL activity ID, **not by order UUID**, before computing execution metrics.
3. Assess remaining brokerage activity and separate accounts only when exact current account identity and complete bounded pagination are available. Mark unavailable coverage **UNKNOWN**, never zero.
4. Do not infer an exit trigger from price action; use time-appropriate exit journal and deployed version. The R1M source-specific stop reasons above are stored as exit reasons in its ledger; the V2 six forced-flat fills were read back in the corresponding V2 order ledger.
5. Explicit spread, financing and fee records were not independently reconciled for this 168-activity sample. After-fee P/L, reliable statistical confidence, and validated executable new-entry ideas remain **UNKNOWN / NO GO**.

**Provenance:** Alpaca PAPER account GET, FILL activity GET two-page exhausted pagination, 94 order UUID classifications via authenticated broker GET; R1M Percona `securityprepper_r1m_paper` read-only SELECT; `/var/lib/securityprepper-direction-paper/state.sqlite3` read-only SELECT; verified November 18 broker inventory (zero held positions, zero working orders) as of 08:26:52 CT. No article publication timestamp was substituted for first-seen evidence.
