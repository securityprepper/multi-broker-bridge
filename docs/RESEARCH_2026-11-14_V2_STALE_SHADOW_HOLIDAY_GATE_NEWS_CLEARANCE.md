# November 14, 2026 — V2 research-only: stale holiday cache blocks independent PAPER news proofs

## New, independently verified deployment blocker

Read-only audit at www3.securityprepper.com on Saturday, November 14, 2026, approximately 19:30–19:37 America/Chicago. No broker order was sent or modified, no protected source/timer/service was changed, and no LIVE or active PAPER policy was edited.

The trusted holiday publisher completed successfully at 19:30 CST. Its publisher-derived sector-monitor cache, modified at **2026-11-14 17:30:12 CST**, contained a validated **America/Chicago, unpaused, calendar revision 2**, calendar coverage through **2036-10-25**, with a future `next_check_at=2026-11-20 16:07 CST`. The independent news-watch-v2 holiday cache also carried this refreshed unpaused boundary.

By contrast, `/var/lib/securityprepper-v2-forward-shadow/holiday_gate.json` was last modified **2026-11-09 21:18:05 CST**. It is still revision 2/unpaused but has **`next_check_at=2026-11-13 16:13 CST`**, which is EXPIRED. The cache being unpaused historically is not permission to use it after its boundary.

Both existing root-owned, GET-only/evidence-only services explicitly depend on this *expired shadow cache*, rather than the refreshed primary publisher-derived gate:

- `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/news_source_collector.py` sets `HOLIDAY_GATE=/var/lib/securityprepper-v2-forward-shadow/holiday_gate.json`.
- `.../news_clearance_publisher.py` sets `GATE` to that same shadow path; `holiday_allows()` explicitly requires `now < next_check_at`, validated revision, coverage, timezone and unpaused status.

The journals show the transition: at **2026-11-13 16:12:25 CST** the clearance publisher still had six source bundles, two published clearances and four review-only rejects; after the **16:13 CST** boundary, the publisher repeatedly reported `HOLIDAY_FAIL_CLOSED_NO_PUBLISH` and the upstream collector `HOLIDAY_FAIL_CLOSED`. The read-only services were still producing those statuses during the November 14 audit. The V2 forward shadow timer last fired November 13 at 09:05 CST, and is next scheduled November 16 at 08:35 CST; source inspection did not identify an automatic write/refresh of that shadow holiday JSON. Its file modification time remained November 9 despite the shadow timer firing November 13.

## Effect and limits

This is a **fail-closed data availability/liveness problem**, not evidence that an unsafe BUY was executed. It prevents fresh source bundles and `NEWS_CLEAR_ASOF` attestations while the shadow cache remains expired. It can therefore block otherwise independently qualified Alpaca PAPER new BUYs, particularly Monday premarket, **even when the central holiday publisher remains valid and unpaused**. The legacy recommendation-router deployment and other execution preflights have separate controls; their health is not certified by this study. There were **zero broker orders submitted by this research**. Neither the Nov 13 two clearances nor the 4 reviews is a prospective profit result.

The controlling news-veto scope is correctly **yesterday and today in America/Chicago** in the inspected collector/publisher source, not 30 calendar days. The publisher verifies each *individual* bundle's three independent source receipts and two-calendar-date coverage; its generic `UNVERIFIED` status diagnostics are not themselves proof of a falsely cleared symbol. The stale holiday dependency is a distinct problem; do not weaken the issuer/SEC/news or five-completed-minute direction preflights to work around it.

## Research-only proposed release gate (not performed)

A separately approved correction should make both proof services consume a freshly validated holiday publisher decision, or ensure the shadow cache is independently refreshed **at/before every next_check_at boundary**. Require atomic source-timestamped publication; fail closed on missing/invalid/revision-mismatched/paused decisions; verify both services resume evidence collection on a genuinely unpaused, eligible session without accepting older news or touching live broker controls. Test immediately before/at/after expiry and across the Friday–Monday boundary. Do not copy historical `paused:false` to a new expiry or treat weekend hours as a broker-session permission. The active V1 PAPER/LIVE execution, existing orders, 13:15 entry cutoff, 13:40 CT flatten, risk checks, and all timers remain unchanged.

**Research decision: critical future PAPER news-clearance liveness blocker; no trading GO or parameter change.**
