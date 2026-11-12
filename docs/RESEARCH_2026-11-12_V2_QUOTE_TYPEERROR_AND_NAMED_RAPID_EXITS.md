# November 12, 2026 — PAPER SIP quote parser-error provenance and named rapid exits (research only)

**Scope:** One authenticated Alpaca PAPER account, read-only host evidence from Nov 9–11, 2026 and a fresh GET-only order inventory at 2026-11-12 01:32 CST. The previous exact UUID reconciliation covers 60 broker-filled completed pairs (51 MBB, 9 FDR), 120 filled orders, 270 distinct FILL activity events and 4 canceled buys. No new broker order created at or after Nov 12 00:00 CST was present in that 01:32 check; this is not a forecast of later activity or an all-account census. Original 60-pair broker gross P&L -$279.34 before unverified fees remains unchanged.

## Newly discovered quote-data classification problem

In the first historical SIP as-of 5-second quote collector, the 120 actual filled legs were classified **62 FRESH_ASOF_QUOTE, 33 QUOTE_STALE, 25 HISTORICAL_QUOTE_UNAVAILABLE**. Re-inspection of its preserved error-type field shows **all 25/25 unavailable labels resulted from a Python `TypeError`, not a recorded HTTP/provider rejection**. Among those 25, 21 occurred on Nov 9 and 4 on Nov 10; 11 were BUY legs, 14 SELL legs. Previous collector code performed unchecked conversions such as `float(x["bp"])`, `float(x["ap"])`, `int(x.get("bs",0))`, `int(x.get("as",0))`, and iterated `payload.get("quotes",[])` inside a broad `except Exception` that renamed every exception `HISTORICAL_QUOTE_UNAVAILABLE`. A nullable field, malformed payload or other local type incompatibility could produce this exception.

**What is proven:** the status name was overly broad and should not be interpreted as proof that Alpaca lacked historical SIP quotes. **What is not proven:** which exact field or operation caused any one TypeError, whether new retrieval would yield a valid quote, or whether a hypothetical limit would fill. The raw failed response bodies were not archived, and a new authenticated diagnostic GET was not completed in this research run. Consequently, do **not** retroactively change 62/120 strict-valid quotes or 13/60 strictly two-sided eligible pairs, and do **not** upgrade the other 25 to liquid/executable.

A separate, isolated offline diagnostic `research/v2_quote_quality_20261112.py` now reports malformed payload, invalid records, unresolved pagination, stale/future quotes, crossed/too-wide/insufficient-size versus good as-of displayed quotes distinctly. **14/14 local synthetic tests passed**, including null side-size, nullable ask, quote after fill, quote outside window, insufficient size, and a valid quote alongside a rejected record. It has **no network or order methods** and has **not been installed in active V1/PAPER/LIVE**. Before using its results for execution research, re-fetch the 25 failed intervals using an approved GET-only route and test historical quote completeness/size units; do not print credentials, account IDs, private order UUIDs or private cash.

## Specific held-time/post-exit examples, not trading recommendations

The broker-confirmed completed pairs for AMD (two **independent** source lots), CARR, KMI and MCHP were matched against continuously available **post-fill** completed one-minute SIP trade bars, with no bar after the evaluation horizon and no continuation beyond 13:40 CT. The future mark is 30 minutes after the **actual completed sell fill**; this is not a broker execution, not a counterfactual stop-preserving fill, and not an after-fee profit.

| Filled source/lot | Filled holding duration | Actual gross PAPER P&L | 30m after-sell SIP completed-bar mark vs filled sell | Strict fresh prior NBBO on both original legs? |
| --- | ---: | ---: | ---: | --- |
| Nov 9 FDR AMD | 24.00m | -$17.92 | +0.426% | Yes |
| Nov 9 MBB AMD | 1.98m | -$2.80 | +0.322% | No (exit quote retrieval TypeError) |
| Nov 11 MBB CARR | 2.00m | -$1.44 | +0.608% | No (entry quote stale) |
| Nov 11 MBB KMI | 5.07m | -$0.63 | -0.269% | No (exit quote stale) |
| Nov 11 MBB MCHP | 22.92m | +$8.09 | +0.651% | Yes |

There are **5/5** continuously observed 30m mark horizons in these examples (5 round trips, 4 distinct stocks, 2 distinct trading dates); **4/5** later trade marks were higher and **1/5** lower. However only **2/5** pairs had qualifying as-of displayed quotes at both original fill timestamps, and **0/5** have broker-executable counterfactual fills at 30m or a verified original sell trigger. Thus neither the apparent missed upside nor KMI's further decline establishes a minimum-hold policy. The five examples' actual combined broker gross was -$14.70; do not add any midpoint cost on top of actual fills. Historical as-of issuer negative-news clearance is UNKNOWN.

## Decision / follow-through

Research quote-quality failures are a **data integrity blocker**, not evidence of a broker malfunction or of a superior exit rule. The previously discovered exact MBB sell UUID joins remain 48/48, but 0/48 historical decision-reason fields are non-null; forced 13:40 exits remain the three independently verified XOM/COP/NET market fills. Future prospective research must join source version, decision reason, same-account broker UUID and FILL UUID, and collect contemporaneous 1m SIP NBBO/size/spread and fee evidence. Require 20+ distinct, genuinely prospective dates with untouched holdout before selecting an exit policy. The 100-combination posthoc grid on three days is not a releasable strategy. Do not modify active V1, broker positions or orders, stop policies, timers, LIVE or IBKR access. Recommendation Audit alone reports recommendation-linked closed outcomes.

The repaired classifier lives only on the isolated `research/rebound-v2-conditional-exits` branch; 14 synthetic offline tests passed, no broker orders submitted.
