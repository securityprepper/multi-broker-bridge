# November 11, 2026 — Independent prospective SIP quote-receipt validation (research only)

## Scope and trusted holiday boundary
Read-only research on authorized www3. Previously validated holiday status was revision **2**, unpaused, America/Chicago, calendar coverage through 2036-10-25, `next_check_at=2026-11-13T16:13:00-06:00`; current time was strictly earlier with no known invalidation. No Alpaca PAPER trading endpoints, IBKR/Robinhood checks, broker cash/positions/orders, Pushover, V1 service source or timers, holiday gate, or execution permissions were accessed or changed by this probe.

**Method.** A one-off, hardened, nonpersistent `systemd-run` process ran as `alpacafeed`, loading the existing authorized *data-only* Alpaca credentials using systemd `LoadCredential` without printing or saving their values. It issued exactly one GET to the official `https://data.alpaca.markets/v2/stocks/quotes/latest` for 17 prespecified sector symbols, `feed=sip`, and recorded a UTC quote-receipt timestamp immediately after the HTTP response. See [Alpaca's latest-quotes API](https://docs.alpaca.markets/us/reference/stocklatestquotes-1). There was no order or account API use.

## New measured evidence

At **2026-11-11 19:39:15.229266 UTC (13:39:15.229266 CST)**, one fresh batch returned a quote for **17/17** requested symbols (AMD, MU, SNDK, NVDA, AMAT, AVGO, INTC, TSM, CRWD, PANW, ZS, CAT, GE, BA, GS, JPM, BAC). Total request/response duration was **0.110 seconds**.

- **Correct quote-receipt clock:** **17/17 ACCEPT** under the existing max-100-second SIP quote age, strictly nonfuture timestamps, positive noncrossed bid/ask and <=1% bid-ask spread conditions.
- **Clearly illustrative stale-clock counterfactual:** if the identical quote timestamps had instead been evaluated against a fabricated scan start exactly **6 seconds before response receipt**, **17/17 would have been wrongly rejected as “future.”** This is **not** an actual V1 scan, and no real scan-start timestamp or broker preflight was observed in this probe.
- **Do not infer additional filled orders, P&L, winners, or repaired missed buys.** Neither quote publication nor tight spread ensures a limit order executes. This one session/one retrieval is not a statistical accuracy or profit result; two repeated intraday samples are not independent days.

This controlled contemporaneous example directly demonstrates that receipt-relative quote freshness can matter, consistent with previously identified V1 stale-scan-start timing risk. It does **not** retrospectively prove which 2026-11-10 `NO_FRESH_BID_ASK` appearances were attributable to that defect, nor settle why AMD was skipped at 03:18 CST on Nov 9. The original historical raw quote-response/eligibility records were not preserved.

## Reproducibility and quality gates

Pure GET-only source `research/v2_getonly_quote_receipt_20261111.py`, **nine passing offline tests** in `tests/test_v2_getonly_quote_receipt_20261111.py`, and sanitized aggregate `research/results/v2_getonly_quote_receipt_20261111.json`. Tests include future-to-scan vs past-to-receipt, sub-millisecond future timestamps, stale >100s, crossed/zero/negative prices, >1% spread, missing quotes, aggregate redaction, and exact data-only HTTPS endpoint. Acceptance comparisons use **unrounded actual durations**; rounding is display-only. Test execution was successful in a portable scratch repo layout.

Next independent step is prospective matching of first-received quote, correct receipt clock, own-sector BUY_WATCH eligibility and same-broker preflights *during the same actual V1 scan*, requiring additional read-only correlation evidence. A separate six-second comparison cannot replace that attribution. Full matched broker fill activity, actual commissions/slippage and >20 untouched future dates are needed for any after-cost strategy judgement. The frozen seven-sector shadow starts its genuinely prospective policy on Nov 12; its slot snapshots and after-outcome scorer must be verified when due.

**Conclusion: no new PAPER/LIVE strategy GO, no profitable after-cost validation, no new confirmed safety incident.** Existing broker orders, V1 safety/exit, receiving-broker-only authorization, 13:15 CT entry cutoff, 13:40 CT flat, 14:00 verification, and all scheduled tasks were untouched.
