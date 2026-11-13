# Nov 12, 2026 (20:34 CST): active MBB PAPER direct order path lacks explicit prebuy news clearance

**New critical implementation gap — research-only verification; no trade orders or active changes.**

## Source/launcher evidence

Authorized read-only inspection of `www3` found the enabled minute executor service
`trading-sector-paper-executor.service` invokes:

`/usr/bin/python3 -B -m multi_broker_bridge.auto_paper --once --execute`

through a process lock. The installed active source is
`/opt/securityprepper/multi-broker-bridge/multi_broker_bridge/auto_paper.py`
(SHA-256 `38530c3b8ef8ab64db66e98558afd2d84556687f5049633ade784fea12935cab` at inspection).

The active `run()` BUY_WATCH path checks the holiday gate, own-broker position/orders,
SIP quote/spread and completed-RTH-close extension, stale scan, 13:15 cutoff,
prior-entry/reentry eligibility, available cash, and order-size cap.
It then reserves a local idempotency reference and **directly calls**
`paper_api("POST","/v2/orders",payload)` for the PAPER BUY.
`paper_api` sends directly to `https://paper-api.alpaca.markets` through `urlopen`.
Neither the installed `auto_paper.py` source nor its inspected direct BUY path
contains a symbol-specific news lookup, issuer/SEC validation,
`NEWS_CLEAR_ASOF` proof, `NEWS_UNKNOWN` exclusion, or negative-news veto.
A separate V2 research validator exists but is not called in this active route.

**Conclusion:** no explicit issuer-specific negative-news clearance is enforced at
the inspected direct MBB PAPER prebuy POST boundary. This conflicts with the
owner's Nov 11 mandatory negative-news exclusion requirement. It does NOT
prove anything about other unrelated order routes or all broker accounts.
An unseen upstream informational scanner cannot substitute for a mandatory
fail-closed proof on this autonomous POST boundary.

## Real orders, provenance and limitations

The Nov 12 read-only `SCAN_COMPLETE` cohort contains three order responses,
two BUY responses (`VRNS`, `OXY`) and one SELL (`OXY`). Their responses
were `pending_new` (acceptance, NOT fill); the order records lack
`NEWS_CLEAR_ASOF`, issuer evidence or first-observed-news timestamp.
Separate existing GET-only broker audit confirmed both buys actually filled.
It also confirmed OXY's later +$5.78 gross trade and VRNS's mandatory
13:40 CT flat sale +$1.20 gross, not evidence that either was news-eligible.
The material VRNS cash-acquisition event requires independent as-of eligibility
review; its mere existence does not retrospectively establish an adverse-news
classification. No issuer clearance is inferred.

This source-level implementation gap is distinct from strategy exit performance.
The all-source bounded sample remains 62 filled round trips/4 Chicago dates
(53 MBB, 9 FDR), 277 unique FILL activities (244 MBB, 33 FDR).
No 20-day independently held-out executable-cost exit parameter improvement
has been demonstrated, and no new strategy or exit GO is claimed.

## Research control and release boundary

Pure static analyzer: `research/v2_mbb_direct_news_gate_audit_20261112.py`,
synthetic offline tests: `tests/test_v2_mbb_direct_news_gate_audit_20261112.py`.
It never imports live strategy code, fetches credentials, queries brokers, or
places orders. A visible news-related token is not treated as proof of a safe gate.

For a **separately approved PAPER-only release**, require current issuer-verified
`NEWS_CLEAR_ASOF` with first trustworthy as-of observation, adverse-news
veto and stale/unknown fail-closed behavior **at the receiving MBB prebuy boundary**;
recheck on significant pre-submit latency, test open-order/position/holiday,
account and existing execution guards, then validate with simulated and
GET-only broker readback. Do not loosen the 2% extension cap or touch any exit
rules, production V1, LIVE broker account, active timer or orders in this task.

**No source or service change was made to production.**

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]