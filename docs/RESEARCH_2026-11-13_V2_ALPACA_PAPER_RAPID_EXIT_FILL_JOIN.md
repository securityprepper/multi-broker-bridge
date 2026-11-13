# Nov 13, 2026 — Alpaca PAPER multi-source rapid-exit evidence (research only)

## Scope and provenance

At ~14:39 America/Chicago, a **new read-only** reconstruction used the existing authorized **Alpaca PAPER** credential scope and GET-only broker activities/orders API via the repository's `paper_fill_audit` helper. The bounded historical request starts at **2026-11-09 00:00 UTC**, not at the beginning of account history. It is **one credential-scoped PAPER account**. It does not establish coverage of other Alpaca PAPER accounts, other brokers, or any earlier carried position. Source classification uses verified broker order UUID joins and `client_order_id` prefixes, not recommendation links. No source credentials or account IDs are output.

A FIFO quantity-preserving match of broker **FILL activity IDs** to broker **FILLED order UUIDs** produced:

| Source | Fully closed entry orders | Wins | Gross filled P&L USD | <=2m | <=5m | <=10m | <=30m | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MBB | 53 | 16 | -154.14 | 4 | 12 | 22 | 38 | 15.24m |
| FDR | 9 | 0 | -118.22 | 0 | 0 | 0 | 9 | 24.00m |
| **Combined** | **62** | **16** | **-272.36** | **4** | **12** | **22** | **47** | — |

MBB entry counts by Chicago date: Nov 9: 31; Nov 10: 13; Nov 11: 7; Nov 12: 2. FDR: all nine on Nov 9. These are **only four distinct trading days**; the >=20-day, untouched out-of-sample requirement is unmet. The counts above use *first verified entry fill to last verified exit fill*, including partial fill timings. They are not accepted-order counts.

The source returned **277 unique FILL activity IDs**, mapped to **124 distinct fully FILLED broker order UUIDs** (62 buy and 62 sell), from 128 returned orders (four additionally cancelled). Zero duplicate activity IDs, unmatched exit quantities, unclosed entry quantities or cross-source FIFO allocations in this bounded slice. No separate SECTOR/OTHER client-order prefix appeared in this bounded account's completed fills; this must **not** be interpreted as proving the absence of trades at other PAPER accounts or outside the queried interval.

## Exit identification and uncertainty

Of 62 filled exit orders, **58 were limit and four market**; all had blank broker `order_class`. Therefore **zero of these 62 exits was evidenced as a broker-native bracket exit**. The four market exits were XOM on Nov 9 at 13:40:31 CT, COP and NET on Nov 10 at 13:40:31–34 CT, and VRNS on Nov 12 at 13:40:32 CT. These align with the mandated 13:40 CT flat, and the executor reported `FLATTEN_IN_PROGRESS` on those dates, but the flat journal's per-order action linkage was empty; **individual causal attribution remains unverified**.

Across 49 MBB ordinary sell-order acceptance journal records, **48 had no persisted exit reason**. One had `exit_signal_reason=trailing peak reversal`: OXY Nov 12, accepted 09:33:50 CT. Its broker order UUID matches the actual FILLED exit UUID at 09:33:50; the position was held ~44.98m and gross P&L was +$5.78. This establishes **one** evidence-linked software exit cause, but **not a dominant rapid-exit cause** (the OXY trade exceeded 30m). The nine FDR exits have no comparable independently verified triggering reason in this join. Classify causes for all other rapid sales as **UNKNOWN** until original decision records are matched to FILLED broker IDs, not inferred from subsequent prices, thresholds, or order acceptance.

Selected actual filled outcomes:

| Date CT | Symbol/source | Fill-to-fill hold | Gross P&L |
|---|---|---:|---:|
| Nov 9 | AMD / MBB | 1.995m | -$2.80 |
| Nov 9 | AMD / FDR | 24.017m | -$17.92 |
| Nov 11 | MCHP / MBB | 23.029m | +$8.09 |
| Nov 11 | CARR / MBB | 1.999m | -$1.44 |
| Nov 11 | KMI / MBB | 5.152m | -$0.63 |
| Nov 12 | OXY / MBB | 44.977m | +$5.78 |

These P&Ls are **gross actual PAPER fill economics**, not LIVE returns and not after commissions/fees. Broker fills prove executed entry/exit; they do **not** prove executable counterfactual target or stop hits. Historical decision reason persistence is incomplete and historical minute-level NBBO/BOATS quote coverage remains unverified. No bracket/stop/minimum-hold changes are warranted from this cohort.

## Implementation and validation

Research-only source: `research/v2_alpaca_paper_roundtrip_audit_20261113.py`. Synthetic regression tests: `tests/test_v2_alpaca_roundtrip_audit_20261113.py`, 8/8 passed on isolated www3 scratch. The audit imports the existing **GET-only** fill/orders helper only under `__main__`, never sends broker POST/PATCH/DELETE, preserves fill-ID deduplication and fails closed on contradictory duplicates. It keeps unresolved fills, unmatched sells, incomplete positions and cross-source allocations visible rather than silently scoring them. The code has no active PAPER/LIVE executor integration.

**Next evidence gates:** authenticated inventory of each actual PAPER account; complete post-entry one-minute SIP NBBO/usable spread and commission/partial/unfilled behavior; original reason-stamped decisions joined by accepted order UUID to broker FILLED events; >=20 distinct broker-trading days and genuinely untouched temporal holdout before changing exits. Preserve the independent Recommendation Audit notifier, all active V1/LIVE, news veto, holiday, stop, 13:15 entry cutoff and 13:40 flat restrictions.