# November 11, 2026 — prospective earnings/news first-seen and deduplication integrity

## Read-only host finding, 01:03–01:07 CST
The originally described absence of **any** SEC verifier on www3 is OUTDATED: `securityprepper-earnings-sec-observer.timer`, `securityprepper-earnings-issuer-attest.timer`, `securityprepper-earnings-event-stage.timer` and `securityprepper-earnings-order-staging.timer` were found **active**. SEC observer last emitted `SEC_FILINGS_VERIFIED_READ_ONLY`, zero confirmed events and zero orders. Root issuer attestation emitted `SEC_PRIMARY_FINANCIALS_EVALUATED`, zero new attestations and zero orders. These services do NOT prove that a complete independent numeric analyst estimate-revision history exists; that missing evidence still blocks the distinct combined issuer-plus-analyst trading hypothesis.

Active GET-only news collector `/opt/securityprepper/news-watch-v2/research/v2_news_watch_readonly.py` persists `observed_at_utc` using its **poll-start** `now`, BEFORE its authenticated Alpaca `/v1beta1/news` GET and any pagination. That can make a news signal appear to have arrived earlier than it actually did, materially overstating entry timeliness. The collector must use **GET response completion** time as earliest defensible local first-seen evidence, not publication timestamp or polling-start clock.

Read-only live state `/var/lib/securityprepper-news-watch-v2/current.json`: schema 1, `seen` history at **4000** IDs, latest `recent` window **300 records but only 292 unique IDs**, all 300 include `observed_at_utc`, **no `poll_completed_at_utc` and no declared receipt-time basis**. The live source uses `list(set(seen))[-4000:]` and therefore evicts arbitrary IDs when bound reached; previously observed IDs can reenter the 12-minute polling window and be misclassified as new. These 8 duplicates are not necessarily financial-signal candidates, and their exact causes are not reconstructable from journal alone; the unordered ID eviction is a concrete source defect.

The 3,141-article THREE-YEAR archive remains retrospective: neither a publisher's `created_at` nor an `updated_at` timestamp proves original local reception. Do not backfill historical `first_seen_at` values or claim news/issuer evidence was available in a broker-time decision.

## Implemented in isolated V2 research branch (NOT production collector)
`research/v2_news_watch_readonly.py`:
- Immediately after news GET completes, capture UTC `received_at`, ensure it is not before poll start, and pass that as `observed_at_utc` to all new records.
- Persist both `poll_started_at_utc` and `poll_completed_at_utc`, provenance basis `GET_response_completed_not_publication_or_stream_delivery`, and `historical_first_seen_backfill_permitted=False`.
- Preserve first-seen insertion order in `seen` with `dict.fromkeys` and deterministic tail truncation at 4,000 instead of nondeterministic `list(set(...))`.
- Preserve GET-only/zero-broker code boundaries and fail-closed holiday gating.
- Add `tests/test_v2_news_first_seen_receipt_20261111.py`: **5/5 passed** on isolated www3 canonical clone. Tests include post-GET receipt time, identical-fetch deduplication, 4,000 cap eviction order, old ID reappearance only after eviction, and holiday fail-closed.

## Remaining research limitations
1. The 4000-ID cap **by design** loses older IDs; strict replay-safe first-seen across years requires a durable keyed append-only archive (e.g. an isolated Percona record keyed by provider+news_id with earliest receipt timestamp) plus revisions retained separately. Neither historical source archive nor bounded current JSON alone provides that guarantee.
2. The active collector on www3 is **unchanged**, so the production current journal still has the old timing/eviction behavior. A separately reviewed, narrow deployment would be required to begin collecting trustworthy post-GET first-seen data; old records cannot be retroactively repaired.
3. Official 8-K/issuer attestations and numeric analyst estimate revisions must be matched by actual company identity, before/after figures, publication/receipt times and current share basis. Without that independent dataset, no recommendation or new PAPER strategy GO is justified.
4. Previous negative gap/price-only research remains retired; no new after-cost profitable strategy or hypothetical fills asserted.

**Safety:** Active Alpaca MBB PAPER, FDR, IBKR Gateway, LIVE, trading orders, all holiday/stop/13:15 entry/13:40 liquidation safeguards, and news alert delivery remain unchanged; research code is not connected to an order endpoint.
