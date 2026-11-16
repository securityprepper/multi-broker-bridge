# PAPER-only news-source issuer coverage release — 2026-11-16

## Owner authorization and boundary
Owner explicitly authorized expansion of independently verified issuer/SEC/licensed-news coverage after the 2026-11-16 MBB BUY_WATCH gap audit. Changed **only** the root-owned issuer news-source collector module deployed on www3, not the active Multi-Broker Bridge PAPER executor, any LIVE executor, orders, stops, holiday publisher, schedules, or clearance-publisher eligibility policy. The source collector and clearance publisher remain GET-only/no-order services.

## Before/after
- Original public issuer feed catalog: 6 symbols (AMD, INTC, NVDA, FTV, MRVL, FROG), previously scanned in a static six-name loop.
- Revised catalog: **25 separately checked, issuer-owned HTTPS RSS feeds**, 19 added: ANET, VRT, MU, LITE, META, STX, CDNS, SNPS, ORCL, OKTA, QCOM, NET, CRWV, PG, GIS, APH, BKR, DVN, S.
- Feed endpoints were probed from the authorized www3 host before admission: HTTP 200 XML/rss, >=2 parseable items, publisher dates, official issuer host and no network redirect. Sources returning 403, invalid RSS, unknown DNS, redirects, or untrusted hosts were NOT added (e.g. PANW, SNDK, WDC, CRWD, AMAT, AVGO and others). SEC ticker + CIK + exchange remain independently checked for **each** collected symbol.
- Dynamic bounded (max 32 symbols) read-only selection prioritizes current (<3m) qualified/shortlisted symbols from quality-watch SQLite, then the original six as fallback. Stale/malformed candidate lists fail closed; a signal shortlist is NOT news clearance. Missing issuer feeds remain NEWS_UNKNOWN and cannot receive a clearance.
- Publisher retains **Chicago yesterday+today calendar-date** adverse-news cutoff, original issuer/SEC/licensed-news evidence, first-observed receipts, freshness, contradictory-news REVIEW, and original strict NEWS_CLEAR_ASOF criteria. No existing entry, stop, broker, position, or session guard was relaxed.

## Tests and measured observations
- 12 focused source-selection/security tests passed in isolated scratch.
- All 25 newly configured feeds passed an authenticated SEC+issuer RSS+licensed-news **GET-only preflight**; 25 distinct source bundles produced, 9 hypothetical clearance files produced and 16 withheld for review; elapsed approximately **5.3 seconds**, 0 broker orders. These dry-run outputs were isolated and were not broker orders or proof of profitable signal eligibility.
- Production release was atomic with root owner/mode preservation and a rollback copy in `/var/backups/securityprepper-news-catalog-20261116-092342`.
- Installed source SHA-256: `6e76c4249853343b4ca421703e4aa948103268d57f7a56117a0d740febec4dd4`. Prior source SHA-256: `602c8d6724646fd02da2919d058690e600d2c83249f4582ba6ccfcbd59cbc5f9`.
- A real post-release GET-only collection published 8 fresh bundles; the publisher published 3 `NEWS_CLEAR_ASOF` attestations and withheld 5 for review, zero orders. Systemd's original :15 collection and :45 publication timers remained enabled/active and next automatic cycles completed successfully (service status zero).
- Early Nov 16 broker log study: 81 MBB BUY_WATCH occurrences, 41 distinct tickers; the 25-feed catalog contains **14 of these 41** tickers. Remaining **27** have not been fully independently verified and retain strict NEWS_UNKNOWN/NO BUY until additional reliable issuer feeds/coverage are commissioned; this release does not solve every missing ticker.
- Distinguish issuer-feed catalog coverage, actual source bundles for selected candidates, clearance eligibility, and broker-executable BUY eligibility; these are separate stages.

## Next work
Expand remaining issuer-owned source evidence only when the source can be independently verified without removing any three-source, original-pub-date or first-seen requirement; preserve provider access failures as NO BUY. Independently reconcile results with subsequent MBB qualified signals and broker PAPER order readbacks, without claiming this source release causes fills or profitability.
