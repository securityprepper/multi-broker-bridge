# 2026-11-16 09:40 CT — MBB / news-collector candidate-demand mismatch (read-only V2 research)

## New, independently reproduced implementation blocker
The 2026-11-16 PAPER-only issuer-news coverage release expanded independently verified issuer RSS/SEC/licensed news fetch capability from 6 to 25 issuer symbols. But the deployed source collector's **demand selection** reads only the latest `/var/lib/securityprepper-quality-watch/state.sqlite3` quality scan, not the actual MBB `buy_watch_symbols` emitted by `trading-sector-paper-executor.service`. These are distinct signals with different timing and universe. Thus MBB's BUY_WATCH may be withheld for missing NEWS_CLEAR_ASOF **even when the issuer feed is approved**.

## Reproducible observed evidence
- Collected root-owned systemd journal JSON `MESSAGE` and `__REALTIME_TIMESTAMP` for both the PAPER sector executor and authenticated source collector since 2026-11-16 09:25 America/Chicago. No broker writes or active production changes.
- Among 5 nonempty executor events that could be matched to a preceding recent collector, 34 BUY_WATCH appearances were seen; six appearances used an approved issuer feed, and just one appeared in the actual source collector's `selected_symbols`. The other 28 appearances did not have approved feeds; those cannot be made clear simply by improving candidate selection.
- At **09:41:45 CT**, actual executor BUY_WATCH was `MU,SNDK,MRVL,ANET,VRT,ETN`. Four have approved feeds (`MU,MRVL,ANET,VRT`); latest collector selected only `MRVL`, so `MU,ANET,VRT` were **not even independently screened** for that opportunity. `SNDK` and `ETN` still lacked verified issuer feeds.
- Independent as-of replay of the next collector cycle on three completed BUY_WATCH observations with available feeds: actual selection covered 1/6 source-eligible watch appearances, while a causally timestamped merge of the latest completed MBB scan and existing quality selections would have selected 6/6 **in the next collection cycle**. This is **selection coverage only**, not a claim that any candidate would pass issuer/SEC/licensed-news review, be tradable at a verified ask, receive a PAPER fill, or make money.
- Demonstrated no after-fee forward edge from this observation. One directly identified Alpaca PAPER receiving account, verified by GET, was ACTIVE with zero positions, zero open orders and zero distinct FILL activities after `2026-11-13T00:00Z` at the separate current readback. Account coverage must not be generalized to other accounts.

## Safe proposed implementation (NOT deployed)
1. Keep issuer RSS allowlist and original SEC CIK/exchange plus entitled Alpaca-news requirements unchanged.
2. On the collector-side only, read the **last completed, root-backed, timestamped MBB PAPER `SCAN_COMPLETE`** from the specifically named systemd service journal; accept only when `0 <= collector_now - journal_event_timestamp <= 90 seconds` and no future records. Treat the watch symbols as *candidate-demand hints*, never as a news-clearance proof. Validate actual `buy_watch_symbols` list schema, ticker syntax, approved issuer feed membership, deduplicate and cap to 32 selected candidates, then union with quality watch and existing six-symbol fallback.
3. Preserve all publisher `NEWS_CLEAR_ASOF` conditions, full Chicago YESTERDAY/TODAY adverse-news verification, first-observed original evidence, adverse/mixed veto, stale/missing-source NO BUY, actual broker quote and own inventory entry safety. Do not change any broker, LIVE, MBB order executor, protective stops, session guard, timer, Pushover or emergency controls.
4. Commission only after a **separately authorized PAPER-only collector release** with systemd sandbox read verification, unit/integration tests and real no-order acceptance check. Do not infer permission from this research finding.

## Isolated V2 research artifacts
- On authorized www3 research worktree `/tmp/v2-trading-strategy-research`, branch `research/rebound-v2-conditional-exits`, local head `0188e10` (diverged; **not reset, pushed or overwritten**):
  - `research/v2_mbb_news_candidate_replay_20261116.py`
  - `research/test_v2_mbb_news_candidate_replay_20261116.py`
- Ten research-only unit tests passed, including stale/future journal exclusion, invalid status, ticker allowlist and bounded/deduplicated selection.
- Production MBB repository remains independently dirty/unmodified by this research; no order generated.

**Owner intervention to resolve this new specific blocker:** an explicit separately approved PAPER collector-only release to consume time-validated actual MBB BUY_WATCH demand. Until commissioned, preserve fail-closed missing-clearance behavior.
