# Nov 10, 2026 CT — READ-ONLY MBB BUY_WATCH quote-coverage diagnostic (V2 research)

## Scope and method
Read only the authorized `trading-sector-paper-executor.service` JSON journal from Nov 10 00:00:00 through 13:15:00 America/Chicago, filtered to records containing `buy_watch_symbols` and `skipped_buy_reasons`. A pure research parser sanitizes output to candidate symbols, fixed reason codes, aggregate counts and times; no broker/account/cash/credentials/order details are emitted or changed. Code: `research/v2_mbb_paper_buy_watch_coverage_20261110.py`. Seven standalone synthetic tests exercise deduplication, unknown/malicious reasons, secret-field suppression, malformed rows, and truncated scans.

| Observation | Count |
| --- | ---: |
| Diagnostic scan records | 944 |
| BUY_WATCH symbol mentions across scans | 577 |
| Unique (minute, symbol) observations | 517 |
| BUY_WATCH skips tagged `NO_FRESH_BID_ASK` | 456 (79.03% of candidate mentions) |
| Skips tagged `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` | 108 (18.72%) |
| Candidate mentions without a tagged skip | 13 (2.25%) |
| Duplicate skip-symbol entries within a scan / possible >=48-entry truncations | 0 / 0 |
| AMD candidate mentions | 26: 16 no-fresh-bid-ask; 10 ineligible discounted reentry |

These are **scan-level repeats**, not 577 independent recommendations, broker order rejections, or actual missed fills. The 13 untagged mentions must NOT be labeled successful BUY orders without broker-order matching.

At 08:46:46 Chicago, the RTH SIP-mode service produced 13 semiconductor `BUY_WATCH` symbols (including AMD, MU, TSM, AVGO, INTC) and **all 13** had `NO_FRESH_BID_ASK`. The strategy correctly declined to send those BUYs under its established quote-safety filter. This is a major candidate-coverage *blocker*, not evidence that a price-only signal was profitable.

Production V1 currently checks quote age <=100 seconds, a positive ordered bid/ask, and spread <=1% before accepting a `quotes/latest` response. The single `NO_FRESH_BID_ASK` diagnostic does **not** distinguish no API quote, outdated timestamps, inverted/zero quote, too-wide spread, or other invalid data; do not assume Alpaca SIP entitlement failure or adjust the guard without evidence. A bounded retrospective quote-history GET under this independent execution context was rejected; no historical NBBO validation or cause was established. Do not disclose or alter credentials to bypass it.

**Nov 9 AMD 03:18 diagnosis remains unresolved.** The needed symbol-level diagnostic fields were absent from that historical journal. Nov 10's later AMD skip classification cannot be projected back to Nov 9.

## Preserved safety evidence and next steps
A bounded Nov 10 13:38-14:10 journal audit found the 13:40 liquidation guard reached `FLATTEN_IN_PROGRESS` once, followed by 35 `FLAT_IN_BROKER_SNAPSHOT` readbacks through 14:09. This establishes the service's reported broker-snapshot status in that window, not a standalone complete broker FILL-UUID audit or realized-profit measure.

The next independent read-only data probe should classify **freshness, quote availability, market session, normalized spread, API feed, and snapshot completion** by symbol and timestamp, then reconcile broker accepted/filled orders. Preserve the 100s/1% fail-closed checks until authorized evidence supports any adjustment. No V1 timer, PAPER/LIVE broker order, holiday rule, strategy parameters, stop, or cutoff was modified. This research task has **no newly verified profitable after-fee forward strategy** to report; order routing for the Trading Opportunities recommendations remains uncommissioned pending separate release controls, rather than an active path.

Do not resume retired unprofitable price-only, gold-lag, routine reentry, or synthetic-trail research families. Retain the separate novel official-guidance/news catalyst research and the closed-trade Recommendation Audit notifier ownership.
