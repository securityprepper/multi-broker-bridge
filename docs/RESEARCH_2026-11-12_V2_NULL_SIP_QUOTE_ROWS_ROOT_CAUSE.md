# November 12, 2026 — exact null-quote API root cause for 25 misclassified PAPER fill legs

**Research only, one authenticated Alpaca PAPER account; no order changes.** This independent follow-up re-queried the **25/120 actual filled order legs** previously marked `HISTORICAL_QUOTE_UNAVAILABLE` because of Python `TypeError`. The bounded source is 60 completed PAPER round trips (51 MBB, 9 FDR) on Nov 9–11; no assertion about other accounts or older orders. The existing exact activity-to-order UUID audit remains 270 unique FILL activities matched to 120 filled orders, with 4 canceled buys separately counted.

## Reproduced exact response

Every one of the **25/25** independently retried SIP historical quote **GET** requests returned **HTTP 200** with the three standard JSON keys `symbol`, `quotes`, and `next_page_token`; in **25/25**, `quotes` was **JSON null** and there was **no continuation token**. Each was requested on the same symbol over the five seconds ending at its **actual filled-order final-fill timestamp**, with `feed=sip`. The original collector's `for x in payload.get("quotes", [])` iterated `None` and raised `TypeError`; its broad exception handler then misleadingly labeled it `HISTORICAL_QUOTE_UNAVAILABLE`. This **resolves the code-path cause** of all 25 prior TypeErrors as a null *quote list* rather than individual bad quote size/price fields, a transport outage, or HTTP rejection.

Of the 25 legs, **21** belonged to Nov 9 and **4** to Nov 10; **15** were before the 08:30 CST regular open (6 buy, 9 sell), while **10** were at or after 08:30 CST (5 buy, 5 sell). A null list means **no quote rows were returned within this specific five-second historical SIP request**. It does *not* establish zero market liquidity, complete market-wide quote absence, broader BOATS/other-feed unavailability, or any failed executable order. Wider lookbacks and actual continuous timestamped quote archives are still unverified.

## Corrected denominator, unchanged quote eligibility

| Five-second historical SIP evidence at actual final fills | Filled legs |
| --- | ---: |
| <=1.5s as-of uncrossed quote, <=1% spread, displayed best-side size >= filled quantity | **62 / 120** |
| Historical quote present but >1.5 seconds old | **33 / 120** |
| Provider HTTP-200 result with `quotes:null`, zero rows in queried interval | **25 / 120** |
| Complete round trips with strict eligible quotes at **both** actual entry and exit | **13 / 60** |

The independent re-query yielded **0/25 newly qualifying quote legs**. Therefore the original 62/120 and 13/60 strict samples are **unchanged**. No actual filled-trade P&L, fees, source attribution, rapid-exit reason or proven execution estimate changes. No new bracket, hold, stop or trailing change is supported.

## Research code, test and next evidence

On isolated V2 research branch only, `research/v2_quote_quality_20261112.py` now distinguishes HTTP-200 `quotes:null` or `quotes:[]` as **NO_QUOTE_ROWS_RETURNED**, absent/wrong-type quote fields as **MALFORMED_RESPONSE**, and pagination as **PAGINATION_UNRESOLVED**. The research tests in `tests/test_v2_quote_quality_20261112.py` explicitly exercise those cases and retain the no-guaranteed-fill result. **17/17 isolated offline tests passed on www3**. Private read-only retry results were retained under `/tmp/v2-run14-quote-typeerror-retry-20261112/`; neither credentials nor private account/order identifiers are published. The GET-only requests submitted **zero broker orders**.

Follow-on quote coverage needs longer prior-only as-of SIP/NBBO observation windows with exact quote age and size-unit interpretation, not imputation. Historical source-versioned exit reasons remain **UNKNOWN for 48/48 ordinary MBB sells**; 3 forced 13:40 filled exits are separately proven. Require 20+ distinct prospectively untouched trading dates, verified decision reasons, fees and executable bid/ask paths before any parameter recommendation. Do not modify V1 PAPER/LIVE, IBKR, broker orders, software stops or schedules. Recommendation Audit remains the only notifier for recommendation-linked closed trades.
