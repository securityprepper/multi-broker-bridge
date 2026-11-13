# November 13, 2026 — Actual issuer/SEC/licensed-news clearance source pipeline fixed and verified

## Resolution

**The publisher was functional but had no upstream collector** capable of producing its required independent, root-owned source bundles. At the start, `/etc/securityprepper/recommendation-paper-bridge/news-source-proofs/` contained **zero** files, so the minute publisher correctly reported `WAITING_FOR_INDEPENDENT_SOURCE_BUNDLES` and signed no files. An earlier 12-minute rolling news observer and SEC earnings-only observer did not constitute current, complete, issuer-specific source proof for the owner's **yesterday + today (America/Chicago)** adverse-news BUY veto.

### Installed and active

1. `recommendation_paper_bridge/news_source_collector.py` installed on www3 under `/opt/securityprepper/recommendation-paper-bridge/`. GET-only collection of **SEC EDGAR submissions** matching CIK/exchange, official issuer RSS feeds, and **authenticated fully-paginated Alpaca licensed issuer-specific news (including full article content where supplied)** for yesterday midnight Chicago through current observation. SEC filing timestamps are interpreted in Eastern time when the SEC field lacks an offset. No trading/broker POST API, no Pushover or LIVE access. Real provider GET-completion/first-seen timestamps and original byte-response SHA256 are saved; raw licensed responses remain private in root-owned gzipped content-addressed archive.
2. `securityprepper-news-source-collector.service` and `.timer` installed, enabled/active, scheduled once per minute **at :05**. Fixed input universe of six independently verified issuer-owned feeds: **AMD, INTC, NVDA, FTV, MRVL, FROG**. Unsupported tickers (including DDOG and AMAT whose investor pages returned HTTP 403 from www3) remain `NEWS_UNKNOWN` and are *not* certified.
3. Existing root `securityprepper-news-clearance-publisher.timer` continues at **:25**, reading only root-owned trusted evidence bundles and writing protected `news-clearance/{SYMBOL}.json` when all source, identity, freshness and in-window news conditions are genuinely satisfied. The root publisher was amended to **revoke previously signed files immediately** if source manifests turn stale, disappear, or include adverse news. Verified by three offline tests.
4. Narrow deterministic `verified_nonadverse` original evidence classification added for genuine **upward analyst price-target revisions while rating is maintained**, documented and checked against the issuer. For FTV a single original fiscal.ai full-content article explicitly stated the price increase and unchanged rating; for FROG the equivalent fiscal.ai content and matching independent Benzinga action corroborated the analyst/rating/target. Any unclassified/mixed material or newly material SEC 8-K/quarterly filing/issuer release remains **REVIEW**, never silently `NEWS_CLEAR_ASOF`. Original publisher/hash/receipt proof and source scope remain mandatory. A stock with good news but failing as-of last-five-minute price direction remains **NO BUY** in the separate existing PAPER receiver.
5. All original backups and other host V1 and LIVE settings preserved. No broker orders, position updates, protective-stop changes, unauthorized LIVE access, or previous task timer modifications. Publisher and collector share the existing validated holiday pause gate: cached rev2 **unpaused only strictly before 2026-11-13 16:13 Chicago** absent an edit.

### Latest real active end-to-end readback, Nov 13 2026 at approx. 14:50 Chicago

The source collector and root signer each had `Result=success, ExecMainStatus=0`. Both new source timer and existing root publisher timer were **enabled and active** and had run again automatically.

| Actual symbol | Verified SEC/issuer/Alpaca source bundles | In-window items | Original news materiality | Root clearance |
|---|---:|---:|---|---|
| **FTV** | 3 sources | 1 | Corroborated nonadverse rating-maintained price-target raise | **NEWS_CLEAR_ASOF** |
| **FROG** | 3 sources | 2 | Matched analysts/ratings/target raise with independent licensed-source corroboration | **NEWS_CLEAR_ASOF** |
| AMD | 3 sources | 28 | Not independently adjudicated; includes mixed/other company news | **REVIEW / NO BUY** |
| INTC | 3 sources | 12 | Unclassified potential material content | **REVIEW / NO BUY** |
| MRVL | 3 sources | 9 | Unclassified issuer and market news | **REVIEW / NO BUY** |
| NVDA | 3 sources | 168 | Material/contradictory and mixed new issuer news | **REVIEW / NO BUY** |
| DDOG, AMAT and rest of universe | One or more complete/official sources missing | Unknown | Incomplete issuer-specific coverage | **NEWS_UNKNOWN / NO BUY** |

**Source raw readback** for FTV and FROG: each of its three independent original GET responses was preserved and the SHA256 reverified from the private archive. Data covered from **2026-11-12T06:00:00Z** (midnight Thursday Chicago). The protected files were also read as the actual unprivileged `alpacafeed` service user, which returned `NEWS_CLEAR_ASOF` for FTV and FROG, and `NEWS_UNKNOWN / TRUSTED_CLEARANCE_UNAVAILABLE` for the four still under review and unsupported symbols.

The *news clearance* is **one safety prerequisite**, **not** a trade signal. PAPER BUY eligibility still requires the independent latest **six consecutive completed one-minute marks (five-minute rising direction)**, price nonextension, fresh executable bid/ask, correct receiving PAPER account complete positions/open orders/cash/protective orders/idempotency/holiday/session and **latest 13:15 CT entry cutoff**. All special positions must be flat by **13:40 CT**. No trade was placed from this task.

### Tests & limitations

- **24** new upstream source/analyst-evidence/revocation regression tests PASS, including strict origin, no HTTPS redirect, no fabricated source coverage, no automatic favorable-news classification, independently matched analyst revisions, and immediate stale/absent/adverse signed-file revocation.
- **38** previously installed root news eligibility/publisher regression tests still PASS.
- Total **62 offline tests passed**. Plus actual authenticated Alpaca, official SEC, official issuer RSS source reads, signed protected file and consuming-user readbacks.
- Limited to 6 approved issuer feeds. Do **not** misrepresent this as an all-stock clearance solution yet. For broad watcher universe, add authentic original issuer IR feeds with coverage and negative-news review; any unsupported stock remains fail closed. Increasing the universe also requires fair provider rate limits and a sustainable publisher cadence.
- Another operational limit: original source news classification is conservative. A positive-looking headline alone is insufficient to label other ambiguous articles nonadverse. In particular, the four reviewed symbols must not be blindly approved based on favorable market direction or headlines. Missing data remains distinct from negative proof.
- At inspection time the **cached holiday gate was valid only until Nov 13 16:13 CT**. Post-boundary publication is fail-closed until its trusted publisher refreshes the gate; do not claim future operation when that condition is unknown.

### Research version-control evidence

All changed code & reviews were committed solely to `securityprepper/multi-broker-bridge` branch `research/rebound-v2-conditional-exits`:
- `recommendation_paper_bridge/news_source_collector.py`
- `recommendation_paper_bridge/news_clearance_publisher.py`
- `recommendation_paper_bridge/news_eligibility.py`
- `ops/securityprepper-news-source-collector.service`, `ops/securityprepper-news-source-collector.timer`
- `tests/test_v2_news_source_collector_20261113.py`
- `tests/test_v2_nonadverse_analyst_revision_20261113.py`
- `tests/test_v2_news_clearance_revocation_20261113.py`

No original licensed news content, SEC raw document archive, secrets, account identifiers or broker orders were committed.

**Outcome:** Original broken empty collector/publisher link **fixed and verified with real signed FTV and FROG clearances**. Full-universe issuer feeds and the careful classification of ambiguous in-window adverse news remain distinct coverage blockers; never broaden BUY permission by fabricating proof.
