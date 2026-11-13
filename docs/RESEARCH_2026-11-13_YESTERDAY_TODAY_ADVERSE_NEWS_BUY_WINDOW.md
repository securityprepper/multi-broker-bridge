# November 13, 2026 — Adverse-news BUY veto narrowed to Chicago YESTERDAY + TODAY

## Latest owner rule — now implemented on www3

The adverse-news exclusion screen is **ONLY the current Chicago calendar date and immediately preceding Chicago calendar date**, from **00:00 local yesterday** until the exact recommendation / PAPER order decision time. It is **not 30 calendar days, 7 days, rolling 48 hours, or two trading sessions**. For a Monday signal, the window is **Sunday and Monday**, not Friday or the prior trading session.

As of Friday, 2026-11-13 around 10:52 CST, the active window started **2026-11-12 00:00 CST** = **2026-11-12T06:00:00Z**. The deadline/time zone automatically adjust across DST.

**Original issuer-specific news published before the beginning of yesterday is excluded from this adverse-news BUY veto, even if the old article described a material problem.** In-window material adverse news still triggers AVOID; serious allegations or contradictory evidence still trigger REVIEW/WATCH. A news item whose original publication or first-observation provenance is unknown **inside the window** is not automatically cleared. Later/unobserved articles cannot be retroactively used at an earlier as-of decision.

Separate buyer controls remain unchanged: 6 consecutive completed one-minute bars/5-minute direction, issuer/ticker verification, price extension, own broker verified positions/orders/cash, holiday, same-broker idempotency, native/protected exits, 13:15 CT cutoff and mandatory 13:40 CT flat. No LIVE authority was added.

## Active code changes

1. **Root-published independently attested issuer/SEC/news clearance**, used by both MBB direct Alpaca PAPER BUYs and the isolated recommendation-to-PAPER bridge: `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/news_eligibility.py`. The exact Chicago yesterday-midnight UTC boundary is computed with `ZoneInfo("America/Chicago")`. The reducer filters older originally published articles **before** considering their classification for BUY eligibility; a verified adverse item from yesterday/today is still hard-veto. Source coverage now needs to be independently proven **from yesterday's midnight**, not for 30 days. The trusted root `NEWS_CLEAR_ASOF` reader still rejects stale, malformed or missing attestations.
2. The **root-only clearance publisher** `news_clearance_publisher.py` now requires the explicit source scope `COMPLETE_INDEPENDENT_YESTERDAY_TODAY_ISSUER_SEC_LICENSED_NEWS`, original verified source receipts, complete source-specific coverage reaching back to the exact local-date boundary, and proper issuer identity. The previous `COMPLETE_INDEPENDENT_30D_ISSUER_SEC_LICENSED_NEWS` scope is **not accepted**. Output manifests contain the verified screening start. Source gap diagnostics now refer to yesterday/today, not 30 days. Timer `securityprepper-news-clearance-publisher.timer` remained **enabled and active**, with the same schedule.
3. The **one-minute quality-stock/news watcher** `/opt/securityprepper/quality-opportunity-watch/quality_watch.py` previously used a **7-day adverse-news query/veto**. Both its targeted licensed-news lookup and cached/recent global news filtering now use exactly yesterday+today in Chicago. Its news cache is invalidated when the local calendar screening boundary shifts at midnight. Its unrelated seven-day lookback for *daily price-close baselines* was intentionally preserved. The enabled/active `securityprepper-quality-watch.timer` remained unchanged.
4. The **four Trading Opportunities scheduled tasks**, plus Trading Strategy Research and Audit Missed Opportunities, received a new controlling prompt override with the same local-date scope, while their current schedules and enabled states were preserved. Recommendation Audit remains dedicated to evaluating closed trades, not issuing new BUYs.

## Evidence and safety regression

Staged and live validation on authorized www3:

- **38** news reducer / root-publisher unit tests PASS, including older material negative news exclusion, exact prior-day midnight inclusive, current-day adverse veto, missing/fresh coverage checks, direct synthetic `NEWS_CLEAR_ASOF` root-file consumption, DST spring/fall, Monday/Sunday window, future data exclusion, symlink/untrusted source rejection, and holiday paused fail-closed.
- **10** new one-minute quality-watcher calendar-window tests PASS, including the midnight news-cache invalidation and unchanged 7-day *price* baselines.
- **27** original quality-watcher regressions PASS.
- **75 tests total for the changed rules PASS.** Installed live module SHA256: root reducer `de5655c08c615d3af3260596cd04de1a3fc066ae82ae88be88bc8ff6026cb933`, root publisher `cb1c80d8938248c1b6699ead70551287b1c5c27c8e6a66e5bd533c6b3b644fe4`, quality watcher `107ce53d85e877c12f9694b3d73c64435419c65c9c3bc0e61af0aedfcb5c9709`. All installed using exact source SHA checks, atomic file replace and backup; unrelated agent source modifications were preserved.

Four PAPER/observer timers — root news-clearance publisher, MBB PAPER executor, recommendation-PAPER router, and quality watcher — were verified **enabled and active**. Neither live broker orders nor V1 execution permissions, exits, stop thresholds or schedule rules were changed in this run. No broker order was submitted by research. Holiday cache rev2 was unpaused and valid strictly before Nov 13 2026 16:13 Chicago, absent calendar invalidation.

## Remaining independent upstream source problem (not falsely declared solved)

The trusted publisher status readback is **`WAITING_FOR_INDEPENDENT_SOURCE_BUNDLES`**, with **zero actual upstream source bundles and zero signed CLEAR files**. The narrowed calendar scope eliminates the previous 30-day completeness requirement, but it **does not fabricate a complete two-day issuer, SEC and licensed-news proof** from the currently partial event-only SEC observer or the most-recent-300-article rolling global news cache. True publisher inputs still require independent source coverage, original receipt/provenance and fully paginated source references for yesterday/today. With these missing, receiving PAPER BUY remains `NEWS_UNKNOWN` and fails closed. The user explicitly changed *time window*, not source authenticity or the requirement to exclude current adverse news.

Do **not** claim that shortening the lookback alone reactivated all PAPER BUYs. Complete two-day issuer/SEC/news source attestation must exist before genuine clean-news files are issued. The owner may choose a different explicit source/coverage policy later, but neither a missing article nor an older negative article is being turned into a new BUY recommendation here.

## Versioned research artifacts

On `securityprepper/multi-broker-bridge` branch `research/rebound-v2-conditional-exits`:

- `recommendation_paper_bridge/news_eligibility.py` and `research/v2_paper_negative_news_asof_gate_20261111.py` — synchronized two-calendar-day evidence semantics.
- `recommendation_paper_bridge/news_clearance_publisher.py` and `research/v2_trusted_news_clearance_publisher_20261113.py` — updated two-day source manifest and root publisher.
- `tests/test_v2_paper_negative_news_asof_gate_20261111.py`, `tests/test_v2_trusted_news_clearance_publisher_20261113.py` — updated 38 tests.
- `research/patches/quality_watch_yesterday_today_adverse_news_20261113.patch` — exact previously reviewed/installed one-minute quality watcher change.
- This report.

All broker and host source evidence remains private; no credential, licensed feed article/body or account identifier was committed.
