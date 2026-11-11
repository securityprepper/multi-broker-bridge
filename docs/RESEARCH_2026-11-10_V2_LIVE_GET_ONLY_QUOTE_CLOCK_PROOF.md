# V2 GET-only prospective quote receipt-clock proof — November 10, 2026 21:36–21:37 CST

**Scope:** Authorized www3 host, no order endpoints, no position/account API, no modification to V1 PAPER/LIVE or timers. One-off nonpersistent `systemd-run` GET-only market-data observer using data-only credentials. Historical 08:46 CT raw `/quotes/latest` responses are not available, so Nov 10 RTH 456 skip reasons cannot be retroactively assigned precisely.

## A. Prospective genuine Alpaca BOATS latest quote response — deliberately delayed scan-start
At 2026-11-10 **21:36:07.351712 CST** (2026-11-11 03:36:07.351712 UTC), captured scan-start clock, waited **6 seconds deliberately to reproduce a delayed scanner**, then fetched Alpaca `GET https://data.alpaca.markets/v2/stocks/quotes/latest`, `feed=boats`. Response receipt **03:36:13.422605 UTC**, 6.071 seconds after scan-start.

All seven symbols AMD, MU, AMAT, AVGO, INTC, TSM, NVDA:
- Quote timestamp was **newer than frozen start** but **older than actual GET receipt**.
- All seven quote ages as-of receipt **1.099–4.771 seconds**, spreads **0.0579–0.3434%**, positive and uncrossed.
- Frozen V1 scan-start evaluator would return `FUTURE` **7/7**, while corrected V2 receipt evaluator returns `ACCEPT` **7/7**.
- **Experimental delay was injected**: this demonstrates the mechanism using real observed premium data, not an actual V1 scanner trace or proof that 7 intended trades would have filled/profited. Zero broker endpoints/orders.

## B. Prospective natural GET sequence — no injected delay
At 2026-11-10 **21:37:37.051727 CST** (UTC 03:37:37.051727), invoked actual GET-only **47-minute BOATS 1-minute-bars fetch first, then /quotes/latest**, on the exact 13 semiconductor BUY_WATCH tickers reported in the 08:46 CT V1 journal: AMD, MU, TSM, AVGO, QCOM, INTC, AMAT, LRCX, KLAC, ASML, MRVL, TXN, ON. No broker readbacks, no artificial wait; this deliberately understates V1's real multi-request scan latency.

- Historical bar GET: 222 rows across 11 symbols; no truncated token.
- Latest GET receipt UTC 03:37:37.196249; natural elapsed **0.145 seconds**.
- Latest bid/ask accepted by **receipt-clock evaluator: 11/13**.
- Original frozen scan-clock evaluator accepted **10/13**. **MRVL** was marked `FUTURE` by the original evaluator, though its quote as-of receipt was **0.121 seconds old** and **0.2037% spread** (correct evaluator ACCEPT).
- **TXN** spread **1.3537%** and **ON** spread **1.1353%** — correctly rejected by BOTH evaluators. These are real wide-spread restrictions and must NOT be overridden by receipt-clock fix.
- All quote snapshots are contemporaneous **BOATS after-hours**, NOT executable fills or proof of 08:46 RTH SIP quote response. An actual V1 scan also spends time on broker readbacks/more data GETs, so its race risk may be larger.

## Distinct market-risk impact
The **same dropped `quotes` dictionary** controls BOTH routine `BUY_WATCH` admissibility **and the premarket direct-BID -2.5% emergency exit / peak trail supplementary check** in the V1 source. The clock race can therefore suppress an immediately available quote-based risk trigger until a later bar-based decision; the independent 13:40 CT hard-flat guard does not require quotes. No actual missed mandatory exit or loss from this defect has been confirmed. This is an important PAPER execution/risk-monitoring defect, not a LIVE authorization.

## V2 research fix, tests, and blockers
- Isolated V2 source already changed in `multi_broker_bridge/auto_paper.py` to compare `quote_received_at` captured immediately after `/quotes/latest`, preserving 100-second age, 1% spread, positive/uncrossed and genuine-future protections.
- New research-only script `research/v2_live_quote_receipt_readonly_20261110.py` performs only allowlisted `/v2/stocks/bars` and `/v2/stocks/quotes/latest` GETs. It emits categorical assessments, never credentials/accounts/cash. Options `--preload-mbb-bars` and `--pre-get-delay-seconds` separate natural from artificially delayed observations. No permanent timer or executable order route added.
- **38 tests passed** in isolated /tmp/sp-paper-bridge-verify-20261110: 10 observer tests, 4 bar-preload tests, 7 production-equivalent patched-fetcher tests, 10 clock-diagnostic tests, and 7 baseline executor tests.
- **Remaining:** original Nov 10 SIP latest-response missing, so cannot prove why each of 456 BUY_WATCH quote skips happened; need a matched market-hours prospective capture of actual response and receipt timestamps, no orders. Independent security review and separately approved PAPER-only release required to install V2 quote-clock fix in active V1. Recommendation-to-PAPER router remains uncommissioned and requires Percona roles/idempotency and end-of-day broker-level evidence. No credible positive forward after-cost strategy verified here.

**Conclusion:** This is an independently observed real-market proof of a potentially material PAPER risk/entry rejection defect, but NOT evidence of missed profitable executions. Fix clock comparison first under approved PAPER safety change; do not weaken spread, quote freshness, positions, holiday or liquidation safeguards.
