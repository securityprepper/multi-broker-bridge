# November 12, 2026 — FDR issuer-news coverage blocker (research only)

**New source-level PAPER reactivation blocker, not an active order incident.** This research covers the independently paused five-day rebound strategy (FDR), in addition to the previously identified active MBB direct-buy missing-news-gate issue. The existing `trading-five-day-rebound-paper.timer` remains active, but November 12 `trading-five-day-rebound-paper.service` journals show `NEW_ENTRIES_PAUSED_PENDING_VALIDATION` with `orders: []`. No PAPER or LIVE order was submitted by this study.

## Read-only evidence and reproduction

The installed FDR entry module `multi_broker_bridge/paper_rebound_runner.py` defines a nine-symbol intended basket: **AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM, INTC**. Its news request, `_fetch_causal_news`, selects only three imported sector `ANCHORS` (**AMD/MU/SNDK**), not the six remaining basket symbols. The matching `rebound_catalysts.screen` logic checks only those anchors, looks for negative earnings/guidance-like headline language, and uses `minimum_distinct=2` by default. It does not require every purchased issuer's own verified `NEWS_CLEAR_ASOF`, issuer/SEC filings, first reliably observed news version, or a single independently confirmed material adverse event veto.

Pure offline test with invented headlines and no broker calls:

- One clearly adverse AMD quarterly earnings/revenue/guidance headline: **veto false**.
- Two distinct such AMD headlines: **veto true**.
- Two adverse NVDA earnings/guidance headlines: **veto false**, because NVDA is not in the anchor filter.

Those examples are **synthetic, not actual issuer-news facts**. They demonstrate that a news request's successful return and absence of two matching headlines is not equivalent to clean, issuer-specific news clearance. No claim of a mis-executed FDR order is made; new FDR entries are currently paused.

A separate fail-closed, source-only reproducer `research/v2_fdr_news_scope_audit_20261112.py` parses source text using the Python AST without importing production trading code. Its current result identifies **6/9 basket symbols outside the news-veto roster**, a two-distinct-headline minimum, and no `NEWS_CLEAR_ASOF` or `first_observed_at` requirement in the inspected FDR runner. `tests/test_v2_fdr_news_scope_audit_20261112.py` passed **7/7** offline tests in isolated `/tmp/v2-fdr-news-scope-20261112` on www3. This is a static safety-scope audit, not a live or after-cost trading backtest.

## Release decision

**NO GO for new FDR PAPER purchases.** Retain the existing FDR entry pause, exits and holiday/13:40-flat safeguards. Before any separately authorized PAPER-only reactivation, require broker-scoped prebuy `NEWS_CLEAR_ASOF` for **each** basket issuer with exact identity, trustworthy first-observed timestamps, SEC/issuer corroboration, a one-event hard veto for verified material adverse developments, stale/unknown fail-closed behavior, and a fresh pre-submit check. Sector-anchor adverse news can remain an additional basket-wide veto, never a substitute for basket-symbol checks.

This is not a demonstrated profitable exit-rule change. The bounded recent authenticated Alpaca PAPER denominator remains **62 completed round trips across four distinct Chicago trading dates** (53 MBB, 9 FDR) and **277 fill activities** (244 MBB, 33 FDR). No additional completed trade, executable alternative fill, or 20-day held-out exit improvement is established here. Active V1, LIVE, broker orders, exits, stops and timers were left unchanged.
