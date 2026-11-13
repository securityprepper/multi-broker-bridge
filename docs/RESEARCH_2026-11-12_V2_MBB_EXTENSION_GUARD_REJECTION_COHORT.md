# Nov 12, 2026: MBB entry-extension gate — rejection-only causal evidence

**Research-only / no orders / no change to PAPER or LIVE.** Evidence: read-only
`trading-sector-paper-executor.service` journal, November 12 07:00–14:10
America/Chicago. The live `multi_broker_bridge/entry_extension.py` uses
the freshest authenticated completed SIP regular-session close versus proposed
ask and rejects an ask **more than +2.0%** above that close. This is an existing
conservative gate, not evidence of a profitable trading cutoff.

## Bounded audit

- **443** SCAN_COMPLETE records, **494** BUY_WATCH symbol appearances
  covering **52** distinct symbols.
- **395** appearances (48 unique symbols) were rejected by
  `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY`.
- **97** appearances (19 unique symbols) were rejected by the existing
  `ENTRY_EXTENSION_BLOCKED_+x%_CAP_2.0%` check. Observed rejection
  magnitudes **+2.01% to +6.80%**, median **+3.19%**.
- Remaining **2** BUY_WATCH appearances produced **BUY order response**
  records (`pending_new`). This journal status is **NOT** a broker fill
  confirmation. In the same bounded journal window, **2** separate
  `FAIL_CLOSED` ValueError reports and **36** daily-exit-guard records
  appeared; neither is a new filled trade.
- The sums 395 + 97 + 2 = 494 reconcile this journal's BUY_WATCH
  appearances only, **not** all broker trades or all strategy sources.

## Proposed cap grid: existing blocked subset only

| Hypothetical cap | Of 97 rejected appearances newly at/below cap | Still above |
|---:|---:|---:|
| 0.5%, 1%, 1.5%, 2% | 0 | 97 |
| 2.5% | 24 | 73 |
| 3% | 44 | 53 |
| 4% | 57 | 40 |
| 5% | 73 | 24 |

These are **repeated minute-level appearances, not independent tradable
opportunities, fills, or profits**. The rejection log saves rounded percentages
for >2% candidates only: it **cannot** measure how much tightening a 0.5%,
1%, or 1.5% cap would reject, nor score all eligible buys. The source applies
the extension gate **before** checking persistent `tracked` positions, so
some of the 97 may fail the old-entry/re-entry gate even if the extension cap
is loosened. Other same-broker/negative-news, quote, and risk gates also remain
mandatory.

The journal's accepted order responses have no complete independent
source-to-fill timeline. No contemporaneous original recommendation ask,
first verified system ingestion of news, event-specific `NEWS_CLEAR_ASOF`,
broker submit/accept timing or historical quote-supported alternative fill
is present in these rejection rows. Therefore **zero** of the 97 rejected
appearances can be scored as independently verified profitable trades.
There is only **one observed trading date** here, versus the required at least
20 distinct days with untouched holdout for selecting a threshold. No
parameter-change recommendation is supported.

## Safe next-stage validation

On untouched future dates, independently record sector change in the last
60/20/5 minutes; separate prior completed RTH-close extension from
original-recommendation-ask extension and from verified publication/pre-news
price; record publication, first reliable ingestion, qualification,
recommendation, intake, broker submit/accept and actual partial/full fills
as distinct timestamps. Broker fills alone determine executed results.
Reconstruct limit eligibility with marketable ask/bid, quote sizes and
spread/slippage; same-bar conflicts use stop-first, and 13:40 CT remains
the latest hard flatten. Score the full 0.5%-to-5% grid on earlier training and
untouched later days with all declined candidates retained as controls.

Keep the existing 2% PAPER cap, all protections, timers, broker orders and
the production V1 code untouched pending independently approved release.
This research produces no order intent.

Reproducer:
`research/v2_mbb_entry_extension_reason_cohort_20261112.py`
with `journalctl ... -o json` on stdin; synthetic offline test suite:
`tests/test_v2_mbb_entry_extension_reason_cohort_20261112.py`.
