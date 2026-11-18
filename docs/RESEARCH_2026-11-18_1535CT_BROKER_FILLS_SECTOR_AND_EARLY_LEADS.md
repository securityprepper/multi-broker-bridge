# Trading Strategy Research — 2026-11-18 15:35 CT, read-only closed-session census

This is an **isolated research-only** record, not an order authorization, live trading recommendation, Pushover trigger, or strategy GO. Source-level row artifacts and reproducible read-only scripts are retained under `/tmp/v2-trading-strategy-research/research/v2_20261118_1535_*` on www3, which has a divergent local research head; do not reset/force push production or replace unrelated edits.

## Gate and provenance

- Verified contemporary root-owned `/var/cache/securityprepper-holiday/task-gate.json`: schema 1, America/Chicago, status_valid, calendar coverage through 2036-10-25, revision 2, `paused=false`, freshly published and `valid_until` future, next boundary 2026-11-20 16:07 CT. All probes are GET/SELECT; no PAPER/LIVE order, Pushover, timer, broker position, V1 source or gateway change.
- Alpaca PAPER native account identity matches expected configuration. Latest verified inventory at 2026-11-18 15:36 CT showed **0 positions / 0 open orders**. Never extrapolate this to another account.
- Alpaca FILL activities were paginated by **native activity ID** for Nov 16–18, deduplicated, then exact broker order UUIDs joined to the same account's Percona `sp_paper_order_provenance` source/role. **181 unique FILL activity IDs, all 181 matched**. These are not accepted-order counts and include partial fills.

## Filled PAPER round trips — preliminary anti-churn study

- In the bounded 2-trading-day R1M sample, Percona+broker inventory showed **40 distinct filled opening orders and 40 filled closing orders**, 64 individual opening FILL activities (partials), and zero verified post-13:15 CT entry fills. The 40 entries occurred between 03:00 and 06:11 CT; closing fills through 06:48 CT. No newly confirmed cutoff breach.
- Strict FIFO quantity matching by source/symbol reconstructed **93 matched R1M partial-lot legs**, preliminary **−$104.35 gross** across the two dates. This is **not** 93 independent trades, and fees, activity fees/corrections, contemporaneous deployed exit journal and a 20-distinct-day evaluation are not established. No exit-parameter decision is supported.
- The same bounded ledger showed **8 V2 opening orders and 8 closing orders** (16 native opening FILL activities), matched fractional-lot legs and preliminary **−$549.28 gross**. The prior six-short exit incident is already known and must not be renotified. This study does not reclassify unknown exit intentions from prices.
- The completed two-day source audit **does not** establish all other historical broker-account fills; missing account coverage remains UNKNOWN. The stop/target replay grid and fee-adjusted holdout have not been validated.

## Two-sided sector evidence (Nov 17–18, licensed completed SIP 5m bars)

Seven ETFs SOXX, GDX, XLE, XLF, XLI, XLV, IGV and three representative peer stocks per sector had 78 complete RTH 5m bars on each studied day. The user's two-completed-close extreme thresholds generated **zero** qualifying ETF shock alerts on either day (and no peer-confirmed qualifying events). The individual weakness test (`<=−2.5%` since previous RTH close, **including** a `>=1 percentage-point` decline within the latest completed 15m) identified **9** stock/ETF first occurrences Nov17 and **7** Nov18. On the first strictly subsequent 5m-close path, only **5/16** advanced further down over 15m; **9/16** advanced down over 60m. These are observations **after** the original as-of mark, not previous-close descriptive accuracy. They use nonexecutable OHLC closes; no positive after-fee alert or short edge is established. No more-price-only emergency alerts or orders warranted.

## Expanded lead and S&P500 read-only research (Nov 18)

The new Quality Watch scan ledger provided original scan-availability timestamps for 195 distinct `expanded_buy_preflight_candidates` and 76 `broad_sp500_research_leads`. These observations are **NOT issuer first-seen news receipts or NEWS_CLEAR_ASOF**. A 272-name union (the above leads plus independent broad-market gainers/decliners) had 270 names with complete two-day 5m reference coverage.

In the sole Nov18 sample, among **unextended <=2% relative to preceding RTH close**, pre-13:15 CT candidates with a last fully completed 5m price proxy:
- Expanded: **171** eligible; **105/171** positive 15m, **93/171** positive 60m, **92/171** positive into 15:00 CT close (nonexecutable).
- Broad S&P: **38** eligible; **25/38** positive 15m, **20/38** positive 60m, **19/38** positive into 15:00 CT close (nonexecutable).
- Among **32** eventual >=3% S&P500 day gainers in the independent 14:55 CT snapshot, **13** had an early, unextended QW lead satisfying those proxy constraints; **19** did not. This is selected-day coverage, not an after-entry win-rate. Some raw early observations before the first completed RTH 5m bar are excluded rather than backfilled using a future price.

**Do not recommend** a price-only trade, loosen extension/news/receipt or broker restrictions, or infer performance from these counts. Exactly **one selected forward day** and zero genuine disjoint 20–30 session holdouts, independent contemporaneous issuer NEWS_CLEAR_ASOF, broker-specific ask/bid, fee/slippage validated fills or live PEA strategy fills are available. No robust after-fee positive forward edge is verified.

## Pre-earnings commissioning context

The sanitized PEA `commissioning-test.json` observed Nov18 shows a one-share **commissioning-only** native bracket parent fill and separately verified independent closing fill with both bracket children cancelled; this test is expressly excluded from strategy profits. The prospective preflight has **150 NOT_ORDERABLE candidates**, including missing original previous-release consensus and comparable actual EPS, issuer release and news evidence. No qualified PEA investment entry/alpha is established.

**Reporting decision:** No new verified robust positive after-fee forward edge, no newly discovered held-position/broker safety failure, and no new owner-action blocker from this census. Preserve the original hourly cadence and notify only if a later independently verified material condition meets the owner's reporting gate.
