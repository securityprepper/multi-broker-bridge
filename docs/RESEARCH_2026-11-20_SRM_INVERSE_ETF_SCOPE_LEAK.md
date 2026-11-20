# Research-only: SRM source admits a leveraged inverse ETF into a stock-oriented sustained-riser handoff (Nov 20, 2026)

## Independently verified new data-quality / possible PAPER admission risk

At approximately 14:25–14:27 America/Chicago on November 20, a trusted unpaused root holiday gate (rev 5449; published 14:25 CT; valid through 14:27:30 CT; boundary 16:05 CT) permitted a **read-only** inspection of the native Sustained Riser Monitor (SRM) source and PAPER handoff receipts.

Native first-party `/var/lib/securityprepper-sustained-riser-monitor/sustained-alerts-2026-11-20.jsonl` has a new 14:02:12 CT (20:02:12 UTC) verified H1 event for `MUZ`: episode `2026-11-20T19:01:00+00:00`, 5m +0.70%, 10m +0.30%, 30m +0.83%, 1h +3.46%. Event key `(MUZ,2026-11-20T19:01:00+00:00,1)` had not previously appeared in the owner ChatGPT hourly sent-event ledger, whereas 42 of 43 historical source events had matching keys (43 sent rows include additional prior-date entries).

**Independent issuer/instrument identity:** authenticated Alpaca PAPER GET `/v2/assets/MUZ` returned `symbol=MUZ`, `status=active`, `exchange=ARCA`, `name=Defiance Daily Target 2X Short MU ETF`, `tradable=true`. The issuer's June 9, 2026 press release describes MUZ as a daily **-200% inverse leveraged ETF on Micron Technology**, not an operating-company common stock: https://rss.globenewswire.com/news-release/2026/06/09/3308531/0/en/defiance-launches-muz-the-first-2x-short-etf-for-micron-technology-inc.html. The independently authenticated Alpaca SIP GET `/v2/stocks/MUZ/quotes/latest?feed=sip` returned valid 14:26:59 CT bid $15.22 / ask $15.23, both above the mandatory $5 floor; this event is **not** a sub-$5 exception.

The authenticated native order-receipt row `SRM-20261120-MUZ-C508EF03E92A` recorded `NO_ORDER_OUTSIDE_RTH_BRACKET_WINDOW`, `paper_order_accepted=false`, `filled=false`, no broker ID. **No PAPER or LIVE trade, accepted order or fill was observed or created by this research.** The blocked event alone does not establish that broker news/position/protective gates would allow this product inside an eligible time window.

## Code-level diagnostic

- SRM's active observer `/opt/securityprepper/sustained-riser-monitor/monitor.py` `observations()` processes Quality Watch's `sustained_riser_research_leads` using source continuity/price and freshness checks but does not explicitly require ordinary-company stock or reject ETFs by broker asset name/type. Its separate `MAJOR_WATCH_EXCLUDED` list mentions many leveraged ETFs but is not a comprehensive authenticated asset-class gate for this sustained-riser flow.
- The existing `/opt/securityprepper/watcher-paper/watcher_paper_executor.py` `eligible_sustained_plan()` validates 60-minute source continuity, quote, and a protected PAPER plan, but does not explicitly reject an inverse/leveraged ETF based on authenticated asset identity. Its subsequently delegated negative-news, holiday, account/quote, session and stop safeguards still apply; do not claim they were bypassed.
- A speculative stock/company annual revenue/EPS fundamentals rating is **not applicable** to this ETF. Do not infer issuer growth from the underlying company or label it GOOD.

## Proposed research-only next step; no production changes

1. Test a **fail-closed, independent instrument eligibility guard** at both discovery and immediately before any PAPER admission, using a broker-certified asset identity and audited ordinary-common-stock criterion. A bare `class=us_equity` is **insufficient** because Alpaca also categorizes this ETF as `us_equity`. Avoid using a fragile ticker blacklist alone.
2. Include regression cases for inverse/leveraged daily-reset ETFs, normal shares, ambiguous asset descriptions, failed/stale asset checks, and already-open-position emergency/protective exit exemptions.
3. Retain the native source event for audit and exactly-once ChatGPT H1 reporting, but **do not present this product as a BUY or an operating-company growth stock**. All additional PAPER release activity, V1 source/service/timer changes and broker orders remain prohibited absent distinct owner authorization.

No production module, service, timer, broker order or permission was changed in this investigation.
