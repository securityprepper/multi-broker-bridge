# November 16, 2026 — V2 read-only issuer-news clearance coverage versus MBB BUY_WATCH

Research-only, America/Chicago, no broker submission or deployment. **Newly verified implementation coverage blocker**, not a profitable trading signal or a proposal to weaken safeguards.

## Exact as-of observation

On Monday **2026-11-16 08:30:00–08:52:00 CST**, inspect completed JSON scan records in `journalctl -u trading-sector-paper-executor.service -o cat`. Across **26 SCAN_COMPLETE records**, **6** contained BUY_WATCH candidates: **81 symbol appearances / 41 distinct symbols** (appearances may repeat; they are **not** 81 fully qualified recommendations, broker orders, trades or trading days). Every one of the **81** corresponding `skipped_buy_reasons` was `NEWS_UNKNOWN_NO_VERIFIED_CLEARANCE`; the records contained **0** orders. An independently fresh authenticated Alpaca PAPER inventory around **08:50 CST** also showed 0 positions/working orders in its bounded receiving account; that snapshot cannot establish other accounts.

The running `news_source_collector.py` has a six-name feed mapping **AMD, INTC, NVDA, MRVL, FTV, FROG**, and `candidates()` literally initializes these six then truncates with `return result[:6]`. Thus its dynamic shortlist cannot expand source coverage beyond the six configured issuer IR RSS identities without a separate reviewed change. Four of the 41 BUY_WATCH symbols (**AMD, INTC, MRVL, NVDA**) were in that configured source universe, but fresh publisher results classified all four as `NEWS_REVIEW_WATCH_ONLY`, not clear. The other **37/41** had **no configured full source-bundle coverage**. Publisher had 6 source bundles, only **two signed NEWS_CLEAR_ASOF files, FTV and FROG**, neither appearing among those 41 candidates. **Verified intersection of BUY_WATCH with NEWS_CLEAR_ASOF: 0/41.** No claim is made that any of the 41 was otherwise eligible to buy, would have filled, or would have made money.

Publisher global diagnostics reported `issuer_ir_yesterday_today_complete=UNVERIFIED`, `sec_all_material_filings_yesterday_today_complete=UNVERIFIED`, and `licensed_news_yesterday_today_full_pagination=UNVERIFIED`, which describe aggregate readiness, not a demonstrated per-symbol failure of FROG or FTV. Per-symbol publisher logic separately requires three original receipts, freshness, coverage and full-pagination/feed evidence; there is no substantiated unsafe bypass in these observed publisher files.

## Attribution and exact safe next steps

The immediate operational constraint is **universe mismatch**: an MBB pre-news BUY_WATCH covering 53 tracked names frequently has no independently verified, same-symbol, current issuer/SEC/licensed-news clearance. Existing **NEWS_UNKNOWN / NO BUY** behavior is correct and **must remain**. This is distinct from the previously researched MBB stale-scan-start quote clock issue.

A separate, approved **PAPER-only** release could extend the configured exact issuer/CIK/exchange + issuer IR directory; feed a bounded, point-in-time source-universe queue from *non-news-qualified* candidate symbols; independently collect complete licensed news, SEC/issuer and immutable first-observed original snapshots over **yesterday and today by America/Chicago calendar**, not a rolling 48-hour or previous-trading-day window; mark contradictions WATCH, material adverse AVOID and incomplete evidence NEWS_UNKNOWN; only sign NEWS_CLEAR_ASOF after valid full coverage. Preserve original last-five-COMPLETED-minutes direction and receiving-broker/holiday/stop/cutoff/flat safeguards. Instrument candidate-symbol/source-symbol/clearance intersections per session and rate limits. Do not permit inferred clearance from no headlines or a historical Friday for Monday.

**No V1/PAPER/LIVE source, systemd timer, brokerage account, order or protective control was changed during this audit.** The blocker remains pending independent design/security/release review, not a request to relax the buy veto.

## Reproduction

- `research/v2_news_clearance_universe_gap_20261116.py`: pure read-only JSONL intersection and reason-counter; no network or broker functions.
- `research/test_v2_news_clearance_universe_gap_20261116.py`: five offline tests; duplicate appearance counting, no false clearance from silence, invalid inputs fail closed, and ignored incomplete scans.
- Original local scratch `/tmp/v2-run-20261116-clearance-gap` is isolated from dirty production and divergent V2 worktrees.
- Sample replay: `python3 research/v2_news_clearance_universe_gap_20261116.py --scans-jsonl scans.jsonl --source-symbols AMD,INTC,NVDA,MRVL,FTV,FROG --clear-symbols FTV,FROG`. The input scan journal is private broker-adjacent operational data, intentionally not committed.
