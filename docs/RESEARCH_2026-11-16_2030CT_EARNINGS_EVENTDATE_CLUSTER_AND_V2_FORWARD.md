# 2026-11-16 20:30 CST — V2 research-only outcome, no strategy release

## Provenance and scope

Research task’s holiday gate validated as **fresh, root-owned, rev2, unpaused** at 2026-11-16 20:30:57 CST (`published_at 20:30:03 CST`, `valid_until 20:32:33 CST`, `next_check_at 2026-11-20 16:07 CST`). Gate was independently rechecked at 20:32:26 CST before the latter data inspections. No broker orders, executor changes, stops, Pushover, timer updates or V1 modifications were made.

Sources: local immutable `/var/lib/securityprepper-earnings-anticipation/research-20261116-broad-market-pre-earnings-3809.json`, `research-20261116-sector-98-last-earnings.json`, `latest.json`, and the 2026-11-12/13/16 sealed V2 GET-only forward-shadow forecast/outcome score files. Historical earnings asset/date eligibility was frozen before price fetching, but Nasdaq dates were retrieved retrospectively and **not issuer-confirmed**.

Reproducible research-only source: `research/pre_earnings_eventdate_clustered_controls_20261116.py`. No host or broker POST operations. This study explores the newly requested PRE_EARNINGS_ANTICIPATION_V1 workstream without weakening the existing news, market-quote, account or order-safety gates.

## Event-date matched descriptive analysis (not a backtest of executable fills)

The broad historical set has 3,809 ordinary-stock earnings symbol/date pairs (69 distinct calendar event dates; no duplicated pair), 58.89% positive over the five *previous* trading closes. Matching the frozen 98 sector-list symbols against this event set gives **138 eligible events on 31 distinct dates**. For each sector event we subtracted the mean return of at least three *other* ordinary-stock earnings events **on the same date**. This is only a same-earnings-date peer comparison, **not** SPY, matched-portfolio alpha, or real-time executable bid/ask.

| Prior-close horizon | Sector event N | Positive raw | Sector mean raw | Mean vs same-date peer (pp) | 95% event-date-cluster resampling interval (pp) |
|---|---:|---:|---:|---:|---:|
| 5 trading sessions | 138 | 41.30% | -0.37% | -1.75 | [-4.87, +1.20] |
| 10 trading sessions | 138 | 28.26% | -4.70% | -6.67 | [-9.19, -3.87] |
| 15 trading sessions | 138 | 26.09% | -7.77% | -9.64 | [-12.38, -6.39] |

The five-day calendar splits show regime sensitivity rather than durable alpha: Aug–Sep 61 sector events had 65.57% positive and +2.60pp vs peers; Oct–Nov 77 sector events had 22.08% positive and -5.20pp vs peers. The sampling interval above is a **descriptive event-date-cluster bootstrap**, not a confidence interval for unseen market sessions, execution prices or causal strategy effectiveness. Both intervals, sector identification, and event selection were retrospectively observed; no claims of forward validation are allowed.

## Growth-threshold sensitivity, no historical point-in-time comparability

Among current 171 upcoming research candidates, exactly **five** meet two successive 15% revenue-and-GAAP-EPS fiscal-growth thresholds (BZ, NVDA, ROAD, VEEV, YMM); **12** meet the single-most-recent annual 15% thresholds (the five plus ADI, DELL, ESE, ESLT, FIVE, LQDT, P). Their matching **earlier** historical pre-five-day earnings event sets showed respectively 1/5 and 4/12 positive. **These are not historical eligibility or trade results:** the financials were screened using the current November 16 snapshot, not each earlier earning-date first-seen data. The group is too small and selection can incorporate hindsight. Do **not** tighten/loosen growth thresholds or issue a broker order from these numbers.

Unresolved: issuer-confirmed releases, immutable prior same-quarter consensus observations, original estimate revision timestamps, issuer-confirmed historical prior-earnings pre-close, independent news clearance, and real ASK/BID + commissions + spread + holiday-adjusted prior-day noon exit. As of this run, `latest.json` reports 0/171 candidates with a verified original consensus-baseline snapshot, 0 verified issuer upcoming releases and 0 cleared/commissioned orders. The 98-symbol coverage reports all 98 EPS revision directions as UNKNOWN (no prior point-in-time revision baseline).

## Independent forward-only sector shadow crosscheck

Across three sealed distinct trading days (November 12, 13 and 16), each has 21 seven-sector by slot 60-minute benchmark-side outcomes, 63 total slot-sector-day records. Of these, 51 are issued non-abstained direction calls: **21/51 directional hits**. Illustrative modeled mean after 30bp and 60bp friction: **-0.28% and -0.58%**, respectively; these are *trade-bar marks*, not brokerage ask/bid or after-fee fill P&L. Semiconductors show 6/9 directional hits and illustrative +0.89% after 30bp, but only three truly distinct sessions, and the November 16 semiconductor day is 0/3; no 20–30 session OOS criterion is met and no GO is warranted. The other six sectors were not independently positive in this tiny set.

## Broker coverage / safety check

Fresh 2026-11-16 20:30:48 CST Alpaca PAPER inventory GET-only snapshot reports 0 positions and 0 working orders in the **one verified connected account**, with 72-hour recent-orders window marked complete for that account only. This does not prove all PAPER accounts or lifetime fills are covered. No new source-attributed closed trades can be claimed. Do not emit a Recommendation Audit closed-trade notification from the research task.

## Result / reporting

**No newly verified after-fee robust forward edge, no newly discovered material held-position safety failure, and no newly actionable owner intervention blocker.** Keep research-only status and existing guardrails; preserve forward provenance and test against 20–30 untouched sessions before any separately authorized PAPER release. Routine negative outcomes are intentionally not user-facing notifications.
