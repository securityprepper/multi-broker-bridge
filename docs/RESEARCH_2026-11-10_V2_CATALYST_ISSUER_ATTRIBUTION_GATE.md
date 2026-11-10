# V2 research — official issuer identity / post-news event timing, November 10, 2026

**Research-only.** No host broker order service, V1 PAPER/LIVE trading rule, timer, or broker order was changed. Historic price-only strategies that failed after-cost tests remain retired.

## Verified failure mode in current live news tags
At about **15:02:26 America/Chicago** on Nov 10, the GET-only Alpaca news observer recorded a headline about FDA approval of **PIMJETMI** tagged to **MRK**. The FDA's Nov 10 approval names **EMD Serono, Inc.** as the applicant (https://www.fda.gov/drugs/cancer-approvals/fda-approves-pimicotinib-symptomatic-tenosynovial-giant-cell-tumor). EMD Serono's parent is **Merck KGaA, Darmstadt, Germany** (https://www.emdserono.com/us-en/company/news/press-releases/fda-accepts-new-drug-application-for-pimicotinib-12-01-2026.html). Separately, **NYSE MRK** is **Merck & Co., Inc.** (https://www.merck.com/investor-relations/investor-resources/). These are different businesses. Therefore, the news tag cannot be used as an MRK BUY catalyst. It is a **verified news-ticker issuer attribution error within this item**, not proof of a live brokerage execution error. The observer has no order credentials.

At the real article receipt timestamp the independently verified issuer identity used in this audit was not yet available in a sealed prospective issuer-verification record; hence the correct **as-of** decision was **UNVERIFIED_ISSUER / no order**, not a hindsight assertion that verification had already occurred. Later official documents let the research audit label it **WRONG_LISTED_ISSUER**. Never relabel the earlier point-in-time decision.

## First novelty trial
A read-only snapshot of the bounded **300 most recent stories at approximately 15:29 CT** contained **two** unverified earnings-release candidates and **one** unverified positive-news candidate; all **three** had been observed after *13:15 Chicago*. By the subsequent 15:32 CT independent test, the rolling window had already shifted to **two** such headlines, both also after cutoff. This is not a full-day count and these snapshots must not be equated with an immutable news-event archive. A generic headline about historical earnings beats was categorized as an earnings candidate, illustrating why headline keywords cannot stand in for primary documents.

We **do not** treat these three headlines as three independent trades, estimate their profitability, or issue BUY alerts. Historical source verification and synchronized post-release executable quotes and 20+ untouched future event days remain missing.

## New pure research gate
Source: `research/v2_catalyst_issuer_gate_20261110.py`. Tests: `tests/test_v2_catalyst_issuer_gate_20261110.py`.
- A news-feed ticker tag is never primary proof of legal issuer identity. Fail closed unless separately observed official FDA/issuer release or SEC filing matches authenticated exchange-listed issuer; production requires reviewed CIK/LEI resolution rather than name matching. Research test keys are illustrative and NOT official corporate IDs.
- Enforce `verified_at <= decision_at` and `news_received_at <= decision_at` with explicit UTC times. Previous consensus and guidance must be frozen before the announcement; compare prior and new numeric figures. Do not equate headline 'earnings beat' with forward guidance raise.
- Prevent post-13:15 CT entry, stale/missing/crossed/wide quote, unsupported session or absent verified protective profit/stop handling. Even a passing result is labeled **RESEARCH_SHADOW_ELIGIBLE_ONLY**: no broker order authorization.
- Prospectively test an independent strategy: official upward-guidance revision, first contained post-news pullback, fresh bid-supported trend resumption, not extended, with actual after-fee future fills and 13:40 CT exit. Retire if it fails; do not tune the old sector-price-only signal grid.

## Separate recommendation-audit blocker confirmed Nov 10
Read-only Percona query on authorized www3 returned **96 total** `sp_live_recommendation_ledger` records, **zero records recommended since 2026-11-09 00:00 UTC** and latest dated Nov 6; latest rows remain `CONDITIONAL_WATCH_ONLY`. The installed recommendation writer explicitly labels itself **review-only** and rejects nonzero quantities/execution authorization. Therefore, its records do **not** establish that today's Alpaca MBB fills came from the four Trading Opportunities tasks; the new recommendation-to-Alpaca PAPER bridge is **not commissioned**. A read-only Alpaca PAPER inventory at **15:28 CT** was broker-verified flat (0 positions, 0 open orders); this is an inventory snapshot, not proof of recommendation attribution or a new trading strategy. No trades or fills were created by this research.

## Next
Preserve task-level hourly Recommendation Audit notification exclusively for genuine newly closed, broker-attributed recommendation fills. Separately build a protected atomic Percona outbox + PAPER-only router with native/session-valid profit and stop protection, full order/fill UUID readback, and independent release tests; do not pretend that a research script can do it.
