# November 11, 2026 — owner-authorized PAPER-only loss-aware regular-session exit repair and profit target coverage

**Implementation:** Active host `www3.securityprepper.com`, `/opt/securityprepper/multi-broker-bridge/multi_broker_bridge/trend.py`, imported by the existing `trading-sector-paper-executor.service`. No LIVE code or broker account/order mutation. This is a narrow **active Alpaca PAPER** source change, authorized by the owner's direct Nov 11 instruction; it is **not** a V2 trading strategy release. The GitHub V2 branch holds a reproducible *surgical patch* for the production host revision, rather than replacing the diverged GitHub V2 `trend.py` and potentially destroying prior V2 edits.

## Actual PAPER change

Removed the unconditional RTH `elif _two_falling(bars): reason="two completed bars with lower highs and lower lows"` rule. Two tiny declining candles alone now cause **no SELL candidate**, including when the position is down slightly. Existing independent regular-session `LOSS_WATCH=-1%` and `PROFIT_TARGET=+1%` price gates, existing peak-trailing condition, stronger premarket stop/exit policy, independently commissioned broker safeguards, 13:15 CT entry cutoff and 13:40 CT mandatory flat/14:00 verification remain unchanged. Consequently a >=+1% profit can still trigger the current profit-taking decision; a <=-1% completed-bar price decline remains a loss-watch exit. No new stop, unconditional minimum hold, relaxed risk authorization or native resting take-profit bracket was added.

**Paper sell provenance:** In the existing `auto_paper.py` PAPER order-acceptance journal output, added `exit_signal_reason` from the actual source row and `exit_fill_verified=false`. The original broker order ID remains in the output. This is an **accepted-order request**, not a filled sale; subsequent research must independently join actual filled order UUID and activity fills. The added field does not affect order payload, sizes, prices, stops, risk checks or idempotency. Do not infer historical UNKNOWN causes from newly installed telemetry.

## Retrospective target reachability (descriptive, not execution backtest)

Source: locally retained authenticated read-only PAPER fill-paired lots and split-adjusted SIP **one-minute trade bars** for Nov 9–11. An actual **MBB** RTH entry has filled buy timestamp >=08:30 CT and <13:15 CT. Examine only minutes beginning *after* the filled entry minute and ending by 13:40 CT. **38 distinct broker round trips on three dates** pass this cohort filter (Nov9:18, Nov10:13, Nov11:7). Each input buy/sell pair has distinct broker order identifiers; no partial FILL activity is counted as another trade. Excluded FDR scheduled premarket and MBB premarket entries are not evidence for an RTH target.

| Target | Ever-observed 1m trade HIGH >= target (upper bound, /38) | Completed 1m trade CLOSE >= target (/38) | HIGH reached before -1% completed-close loss watch on observable contiguous prefix | Missing/censored first-event paths |
|---|---:|---:|---:|---:|
| +0.50% | 26 | 24 | 23 | 2 |
| +0.75% | 22 | 22 | 19 | 3 |
| +1.00% | 16 | 14 | 13 | 6 |
| +1.25% | 10 | 10 | 9 | 6 |
| +1.50% | 10 | 9 | 9 | 6 |
| +2.00% | 3 | 3 | 2 | 6 |
| +2.50% | 2 | 2 | 2 | 6 |
| +3.00% | 2 | 2 | 2 | 6 |

A high touch is **not a bid, broker-accepted order, or guaranteed limit fill**; similarly a completed trade close is not a verified executable quote. A target high occurring in a candle with a simultaneous completed-close loss-watch breach is conservatively **loss-first**. A gap in the one-minute path produces UNKNOWN for later events, not an invented victory. No news-history reclassification is permitted: historical new-BUY eligibility is `NEWS_UNKNOWN`, all results outcome-only.

**Research conclusion:** A +0.50% target touches more RTH trades but leaves ~0.20 percentage points after *illustrative* 30bp friction before any additional realized fees/slippage, and could worsen premature profit-taking. A +1.5–2.0% target reaches many fewer trades; +2% only **3/38** upper-bound high touches. Given three already inspected trading days and incomplete NBBO/first-event paths, **retain +1% RTH price-based profit-taking** rather than claim any target is statistically optimal or add a new native target order. The target remains the existing **software exit signal**, not a resting broker-native limit posted when buying.

## Verification and release boundaries

- Copied the 3.3MB dirty production checkout to **isolated scratch**; edited only the PAPER trend reducer's unconditional two-bar branch and audit-output reason fields in the offline copy, preserving all unrelated dirty/agent work.
- **118 Python unit tests passed** in isolated copy, including 3 new loss/profit boundary tests and 1 new acceptance-not-fill provenance test. One unrelated `test_five_day_rebound.py` suite uses pytest, which was not installed in the host's system interpreter; it was not claimed as run. Original installed-file tests also passed: 11 `test_trend`, 7 `test_auto_paper`. Another **8 research-analysis tests passed** for first-after-entry, duplicate broker-order-ID rejection, as-of missing paths and stop-first semantics.
- Applied both exact diffs **atomically under existing broker-execution.lock**, verifying previous production SHA256 and rejecting any unrelated diff. Backups retained in the isolated scratch. Current installed `trend.py` SHA256 `eb847459672b723fdcb2c16f8017fe3848d1a41bb6899b92eef40554297195df`; `auto_paper.py` SHA256 `1a07548b2eabe5d19637cd5b7c7bbfb2639d81d47df9a884cd94f6ab0111a808`.
- **Actual installed code smoke:** two descending candles from 99.95 to 99.85 on a $100 entry returned **no SELL candidate**; completed close at $98.90 returned `loss threshold reached`; close at $102 returned `profit target reached`. No broker calls during smoke.
- `trading-sector-paper-executor.timer` remained enabled/active, original 1-minute cadence unchanged. Holiday cache validated unpaused calendar revision 2, with next boundary Nov13 2026 16:13 America/Chicago at inspection. No systemd edits, LIVE or IBKR changes, broker order creation, position modifications or commissioning of other strategies.
- **Prospective evaluation:** Treat next PAPER executions and SELL reasons as *new evidence*, distinguish actual broker accepted vs filled, and score after-fee outcomes by trading date. At least 20 independent sessions with sufficient bid/ask quality are required before a target or stop policy adjustment. Recommendation-linked closed trades remain solely reportable by Recommendation Audit; all-source PAPER research remains separate and quiet unless material.

Source: `research/v2_rth_target_reachability_20261111.py`, `tests/test_v2_rth_target_reachability_20261111.py`, `research/results/v2_rth_target_reachability_20261111.json`, and `research/patches/v2_alpaca_paper_rth_two_bar_and_exit_reason_20261111.patch`. The patch describes the deployed host baseline, **not** an unreviewed patch to any divergent V2 or LIVE checkout.
