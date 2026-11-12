# November 12, 2026 — exact broker UUID / activity UUID / MBB decision join (V2 research only)

**Research-only; no broker writes or active strategy edits.** On the authorized www3 host, the study fetched the authenticated Alpaca **PAPER** account and read-only `/v2/orders` and `/v2/account/activities` FILL pages, joined their true broker order UUIDs to journal-reported broker UUIDs, and checked each FILL event UUID/quantity against the filled order. Account identity and full order IDs are private and not in this report. The session's previously broker-verified round trips were cross-validated against fresh full order/fill readbacks. Evidence retrieved **2026-11-12 00:33–00:40 CST**. No other Alpaca accounts are claimed complete.

## Newly resolved coverage and exit-source accounting

| Source | Filled buy orders | Filled sell orders | Nonfilled canceled buys | Completed round trips |
| --- | ---: | ---: | ---: | ---: |
| MBB ordinary scan | 51 | 48 | 4 | 48 ordinary exits plus 3 forced exits |
| MBB 13:40 exit guard | 0 | 3 | 0 | 3 |
| FDR | 9 | 9 | 0 | 9 |
| **Total** | **60** | **60** | **4** | **60** |

The authenticated **one-account** order universe has **124 unique broker orders** (120 filled, 4 canceled) and **270 unique broker FILL activities**, **237 MBB and 33 FDR**. A fill activity is *not* a new trade or order. All 270 event UUIDs resolve to one of the 120 filled order UUIDs, and the sum of fill activity quantities equals broker reported final quantity for each of those orders. There are no additional filled-order sources or extra filled orders **within this specific account and three-day bounded GET result**; that does not establish other PAPER accounts or older dates are covered. The 60 completed long round trips remain MBB 51, FDR 9; Nov 9: 40, Nov 10: 13, Nov 11: 7. Previously measured gross broker realized PAPER P&L on these exact completed pairs: **-$279.34 before unknown commissions**. Do not add any quote-midpoint slippage to the actual fill result again.

**Exact missing exit-reason link:** all **48 of 48** filled ordinary MBB exits join exactly by the actual broker UUID to the contemporaneous MBB order-acceptance journal. **0 of 48** recorded a non-null `exit_signal_reason`. Their trigger classification therefore remains **UNKNOWN**, including rapid exits. The current source's ability to print `exit_signal_reason` cannot retrospectively prove why older versioned runs sold. The **9 FDR** exits belong to an independent source and have no MBB decision reason. Thus the study does **not** claim that 1% profit, -1% loss watch, trail, or falling bars dominated. Of the original 60 round trips, **22** closed in 10 minutes or less; those rapid exits still have no broker-UUID-linked specific trigger.

**Three source-proven forced exits:** MBB's separate time-guard client namespace `MBB-YYYYMMDD-F-SYMBOL`, an actual *market* sell order, individual broker filled-order UUID/quantity/price, independent FILL activities, and the same-symbol journal `MARKET_FLATTEN_ACCEPTED_NOT_FILLED` jointly identify:
- **XOM, Nov 9, 13:40:31 CST**, verified filled; broker gross outcome **-$4.74**.
- **COP, Nov 10, 13:40:31 CST**, verified filled; gross **+$8.68**.
- **NET, Nov 10, 13:40:34 CST**, verified filled; gross **+$4.41**.

The guard's initial *acceptance* was not assumed filled: these three outcomes were established independently from broker fills. All three exited **31–34 seconds after the 13:40 target**, yet before the absolute 14:00 CST latest-flat objective. Do not call 13:40:00 exact liquidation proven. These forced exits are **not evidence** that routine small-shakeout exits occurred.

## Timing and study limits

For the **48 broker-UUID-matched ordinary MBB sell submissions**, the lag from the order-response journal timestamp to broker final-fill timestamp was median **1.86s**, minimum **0.03s**, maximum **166.46s**. Distribution: 26 <=2s, 13 >2–5s, 5 >5–30s, 1 >30–60s, and 3 >60s. The three slowest were **AMAT 166.46s**, **S 147.52s**, **APA 63.08s**. This is *submission response to final broker fill*, **not** latency from the causal price signal and not proof of adverse slippage.

Historical version/risk provenance cannot be assigned from current `trend.py`; its separate two-falling-bars exit behavior changed on Nov 11. No exact old-exit event reason exists in the matched journals. The prior independent NBBO study found a qualifying <=1.5-second prior ask/bid on both legs for only **13/60** actual pairs. Alternative target/stop × hold replays remain constrained by 3 dates, missing executable quote paths, absent commissions, unknown historical adverse-news clearance, and no untouched >=20-day test. **NO GO** on any change to PAPER or LIVE exits, bracket limits, stop triggers, or new strategies.

## Reproducibility / scope

Isolated offline-validated code: `research/v2_paper_uuid_exit_reason_join_20261112.py` and 14 offline tests `tests/test_v2_paper_uuid_exit_reason_join_20261112.py`. The read-only collector allowlists only authenticated account and order/FILL GETs; it never sends POST/DELETE, logs credentials, or saves account/order UUIDs to the published files. The private full inputs and sanitized aggregate are held under host-only `/tmp/v2-run12-uuid-reason-join-20261112`. **14/14 tests passed**. Future prospective observations must durably capture versioned decision reason + client ID + broker order UUID + actual filled activity UUID, and capture comparable post-entry SIP executable bid/ask, with receiving-broker-only safeguards and negative-news as-of research controls. The Recommendation Audit remains sole notifier for recommendation-linked closed trades; this task handles all bounded source cohorts. Active V1, existing broker orders, IBKR, and all timers left unchanged.