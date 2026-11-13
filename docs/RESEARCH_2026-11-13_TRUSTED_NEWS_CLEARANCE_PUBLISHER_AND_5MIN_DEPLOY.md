# 2026-11-13 — Verified PAPER news-clearance publisher installed; upstream evidence coverage remains incomplete

## Direct answer

**MBB = Multi-Broker Bridge**. The specifically authorized MBB minute executor submits **Alpaca PAPER** orders in response to strategy signals; it is not the same thing as an independently qualified Trading Opportunities recommendation.

**What was actually fixed on www3:**

1. Active MBB PAPER direct BUY_WATCH route now enforces trusted issuer/SEC/licensed-news `NEWS_CLEAR_ASOF` **and** rising price movement over the six most recent consecutive completed one-minute observations (five-minute change). A candidate with flat, falling, stale, incomplete or gapped direction remains WATCH/AVOID/NO BUY. The exact condition is checked again immediately before a PAPER BUY post. Existing SELL logic, broker protections, 13:15 CT entry cutoff and 13:40 CT flatten were untouched. 29 offline tests passed (13 MBB integration, 16 independent news/direction tests). No LIVE authorization.
2. Active separately commissioned recommendation-to-Alpaca-PAPER bridge now also requires the completed five-minute direction in preflight, prior to reservation and again before POST, **in addition** to its already existing root-protected `NEWS_CLEAR_ASOF`, nonextended price, receiving-broker-only positions/orders/cash/risk, native bracket, holiday and 13:40 hard-flat controls. Verified 8 completed-direction tests, 7 optional-other-broker boundary tests and 4 router transaction tests on installed source; 60 staged broker-free tests passed excluding one preexisting database integration script requiring an independently configured DB. Four Trading Opportunities task prompts updated with the same no-news/last-five-minutes requirements; schedules/enabled states retained.
3. Root-owned trusted source-to-clearance publisher installed at `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/news_clearance_publisher.py`; new `securityprepper-news-clearance-publisher.timer` enabled/active once per minute, `securityprepper-news-clearance-publisher.service` successful. Trust boundaries: source input `/etc/securityprepper/recommendation-paper-bridge/news-source-proofs/` (root/sectorread 0750), protected output `/etc/securityprepper/recommendation-paper-bridge/news-clearance/` (root/sectorread 0750), status `/var/lib/securityprepper-news-clearance-publisher/status.json`. Publisher has no network/broker/order/Pushover interface. It checks holiday revision/boundary, strict root-owned input, original source receipts/hashes, issuer/exchange/CIK match, fresh three-source 30-day category coverage, point-in-time adverse-news veto and resulting `NEWS_CLEAR_ASOF`, then atomically writes root-owned, group-readable evidence only if genuinely validated. Stale, missing, contradictory, symlinked, or untrusted evidence publishes **no clearance**. 11 root-only offline tests passed including a synthetic valid clearance consumed by the existing PAPER root file validator, adverse evidence rejection and missing-source cases. **Synthetic test files were never deployed to the protected live directory.**
4. Active GET-only Alpaca news collector's historical **scan-start first-seen timing and nondeterministic ID eviction** were corrected without undoing its independent six-minute partition / strict GET pagination handling. New articles now carry actual **GET response completion** time as earliest defensible local observation, `original_receipt_verified=true`; legacy rows remain explicitly unverified, with no invented history. `first_seen_time_basis=GET_RESPONSE_COMPLETED_FOR_NEW_RECORDS_ONLY` and `historical_first_seen_backfill_permitted=false` are in the live state. 15 tests passed, and a manual GET-only service run returned status `READ_ONLY_NEWS_WATCH_OK`, zero broker orders. Collector's existing timer remains enabled and active.

## The unresolved real source blocker — do not mislabel it as fixed

The root publisher ran under its actual service account and reported:

```
status: WAITING_FOR_INDEPENDENT_SOURCE_BUNDLES
source_bundles: 0
files_published: 0
orders_submitted: 0
```

Source audit found **two narrow SEC earnings-event proofs** in the existing SEC observer, **zero** complete issuer financial attestation files, and the licensed Alpaca news cache retaining only its most recent **300** articles. Its previous first-seen timestamps were poll-start approximations; the new clock fix is prospective only. None constitutes **complete, independently proven 30-day issuer IR release, all-material SEC filings and licensed news article coverage**. No source collects and stages a complete per-issuer root-owned independent attestation into `news-source-proofs/` yet. The publisher cannot legitimately sign NEWS_CLEAR from these partial sources, and root write permissions do not repair missing market information.

### Data/source work needed before the first real clearance

- **SEC**: issuer-verified CIK/exchange identity and actual all-relevant recent 8-K, 10-Q, 10-K, 424B/prospectus and other material filing coverage via point-in-time, fully paginated SEC submissions/exhibits, including receipt/version hashes, not only events matching current earnings headlines.
- **Issuer IR/company releases**: independent original official issuer press releases, investor relations announcements and updates, full 30-day coverage and first local receipt, including original document hashes and official updates. No standardized complete issuer IR source was found configured for the whole MBB universe; one-off event-specific SEC earnings proofs cannot stand in for continuous IR completeness.
- **Licensed news**: authenticated issuer-filtered last-30-days full-pagination coverage including negative analyst revisions, lawsuits, guidance cuts, regulatory/export constraints, dilution, debt/liquidity and major developments. Current 300-article global recent window is not verified comprehensive. Persist provider first seen from GET completion or original stream delivery, and retain revisions/dedup without backdating.
- Root-owned source-specific collectors must commit independent verified `issuer_ir`, `sec_edgar` and `licensed_news` receipts with source references, full coverage flags and original SHA256 before the new publisher can make the genuine `NEWS_CLEAR_ASOF` file (60-second freshness). Missing one source still produces `NEWS_UNKNOWN` and NO BUY.

**No verified clean-news certificate exists as of this research run**, so no new MBB or recommendation-PAPER BUY is permitted by these strict latest owner instructions. This is an intentional fail-closed outcome while source entitlement/completeness is unresolved, not claimed successful trading eligibility. No artificial clearances, fake headlines, forged timestamps, skipped news checks, broker trades, LIVE modifications, changed stops or altered task timers were used.

## Code/test provenance

GitHub isolated branch `research/rebound-v2-conditional-exits` now stores:

- `recommendation_paper_bridge/news_clearance_publisher.py`, `research/v2_trusted_news_clearance_publisher_20261113.py`, `ops/securityprepper-news-clearance-publisher.service` and `.timer`, `tests/test_v2_trusted_news_clearance_publisher_20261113.py`;
- `recommendation_paper_bridge/recent_direction.py`, `multi_broker_bridge/paper_buy_safety.py`, and related targeted tests;
- the source history and this report. Installed source changes were made only with exact pre-change SHA checks and readback; backups retained under private host scratch. No unrelated production dirty checkout was reset or force-pushed.

**Current decision: preserve missing-news NO BUY.** Fixing the underlying data-source completeness (including trusted original issuer IR releases and independently complete recent licensed news) is necessary before any clearance may legitimately be issued. The publisher is ready to consume verified source bundles as those collectors/entitlements are commissioned; its mere successful execution does **not** mean any stock was cleared.
