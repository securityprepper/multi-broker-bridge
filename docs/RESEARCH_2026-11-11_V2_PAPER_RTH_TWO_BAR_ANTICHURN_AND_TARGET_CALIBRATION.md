# November 11, 2026 — Alpaca PAPER RTH two-bar anti-churn correction and target comparison

## Applied PAPER-only behavior and verified boundary

On authorized www3, the **currently installed** one-minute PAPER executor source at `/opt/securityprepper/multi-broker-bridge/multi_broker_bridge/trend.py` no longer has an independent RTH `elif _two_falling(bars)` SELL branch. The single-purpose `trading-sector-paper-executor.service` imports this path from a fresh Python process on each minute; its unit specifies PAPER account credentials, `MULTI_BROKER_ALLOW_PAPER=1`, and a broker-execution lock. The existing unit/timer were **not** changed, restarted or rescheduled in this research run. The source was observed as already installed when this run began (file mtime 2026-11-11 19:52:38 Chicago). This report verifies that state rather than attributing the earlier source edit to this research run.

**Current regular-session behavior:**
- Two slightly falling completed one-minute highs/lows by themselves **do not** submit a sell candidate, whether the position is at a tiny loss or small profit.
- Independent `LOSS_WATCH=-1%` (meaningful adverse move), `PROFIT_TARGET=+1%`, existing peak-trailing reversal, and mandatory 13:40 CT flat remain unchanged. Premarket 2%-gain profit/2.5%-emergency and inherited broker protections are unchanged.
- Current `auto_paper.py` does **not** install a standing native profit-taking bracket immediately at entry. When a qualifying SOFTWARE RTH exit becomes actionable, it separately requests a PAPER limit SELL at fresh bid, with same-broker inventory/session/lock/intent checks. An accepted sell is not a confirmed fill; it is not safe to add an independent resting target without reconciled native OCO/bracket, software-stop arbitration and position/order readback. **No new standing target or any broker order was placed by research.**
- The change has been mirrored as a minimal pure RTH patch on the isolated GitHub `research/rebound-v2-conditional-exits` branch, preserving all other branch code. Ten guard regressions passed against both patched isolated V2 and the **installed** host PAPER module, including tiny declining bars (must hold), +1% profit, -1% loss, peak reversal, unexecutable WATCH, and 13:40 forced flat. Three additional offline target-replay tests passed, including stop-first ambiguity and missing-bar exclusion. No LIVE account/executor was edited.

## Historical target observation — **NOT** fill probability

Input: one previously collected, verified Alpaca PAPER account's **60 broker-paired completed round trips** (51 MBB and 9 FDR), Nov 9–11 Chicago, and licensed split-adjusted historical SIP **one-minute trade bars** after the **actual broker-filled BUY** up to the unmodified 13:40 CT flat. Neither a single intraminute high nor a completed trade-close proves a resting target could fill at the user's size and queue position. Full paths have every post-entry one-minute bar through 13:40; gaps remain UNKNOWN in stop-first replay. All original historical BUY candidates are `NEWS_UNKNOWN`, not eligible as retroactively cleared recommendations.

| Target from actual filled BUY | MBB observed intraminute-high >= target (n=51) | MBB at least one completed 1m close >= target (n=51) | FDR high >= target (n=9) |
|---|---:|---:|---:|
| +0.5% | 39 | 37 | 9 |
| +1.0% | 28 | 26 | 9 |
| +1.5% | 22 | 21 | 8 |
| +2.0% | 15 | 15 | 8 |
| +3.0% | 14 | 14 | 7 |
| +5.0% | 10 | 10 | 6 |

For **22 MBB trades sold within ten minutes**, the later-after-actual-exit window still printed at least one price above original filled entry by +1% in 13/22, +1.5% in 10/22, and +2% in 8/22. Their actual realized gross outcome was -$128.76; the high-touch statistics are hindsight upper-bound potential only.

### Conservative stop-first sensitivity (same 33 MBB trades with complete paths)

For this *illustrative* replay assume a standing target and -1% stop from actual filled entry, target or stop triggered by later **one-minute historical high/low**; **stop executes first if both are touched in the same minute** (ambiguous true order). For positions otherwise unresolved, use the historical **fresh indicated SIP bid** near 13:40; subtract illustrative 0.30% of entry notional. This is **neither a quote-level executable order simulation nor observed after-fee P/L**, and the stop model differs from actual software-stop timing.

| Target | Target touched before stop | Stopped first | Indicated flat bid | Hypothetical net P/L on 33 |
|---|---:|---:|---:|---:|
| +0.5% | 22 | 7 | 4 | -$127.49 |
| +1.0% | 15 | 9 | 9 | -$80.52 |
| +1.5% | 11 | 10 | 12 | -$20.24 |
| +2.0% | 4 | 11 | 18 | -$101.20 |

+1.5% was *less negative* on this already research-exposed, only-three-day cohort; no target was proven profitable. Its difference from +1% was especially influenced by the favorable Nov 11 observation (six complete MBB trades: +1% scenario +$58.52 vs +1.5% +$107.73); Nov 9 and Nov 10 were both negative under either target. Adding a 2% target sacrifices most observed potential MBB target touches.

**FDR caution:** despite 9/9 FDR trades printing a +1% historical trade high at some later time, six of the seven fully observed FDR paths touched a -1% stop **before** a +1% target. It is unsound to equate late-day highs with safe attainable profits.

## Decision and next validation

**Keep the PAPER regular-session +1% software profit trigger, do not raise it from three exposed sessions.** At this point +1% is the highest tested target with >50% observed MBB high-touch coverage, while +0.5% leaves little margin after costs. Track +1.5% as a **shadow comparator only** on 20–30 new distinct sessions, matched per true PAPER account, source strategy/version, actual order and FILL IDs, real as-of bid/ask and commissions, protected entry/exit, minimum-hold/stop-first, forced 13:40 flat, per-session tail and actual net P/L. Retain the negative-news veto for *new BUY recommendations*. Do not reoptimize after observing each day's results or assume recommendation-linked subsets cover the MBB/FDR/sector-rebound whole account. Recommendation Audit remains the sole notifier for recommendation-linked closed trades.

The delivered behavior change is limited to the RTH two-bar exit. **There is no proof yet that the more selective exit will profit over 20 independent sessions, and no new broker-native take-profit order was added.** Preserve V1 LIVE, existing PAPER emergency protections, broker orders, timers, holiday gates, 13:15 entry cutoff, 13:40 forced exit and 14:00 latest-flat verification.

Reproduce without touching brokers: `python3 research/v2_paper_rth_target_capture_20261111.py --fills /path/to/authorized-private-GET-only-broker-and-1m-cache.json --flat-quotes /path/to/authorized-private-indicative-flat-quotes.json`. Script outputs aggregate counts only; raw licensed market data, order UUIDs, credentials, and identifiable account details remain private. Pure RTH guard tests in `tests/test_rth_two_bar_loss_guard_20261111.py`; stop-first replay integrity tests in `tests/test_v2_paper_rth_target_capture_20261111.py`. Both were verified with **13 tests passed** on both isolated and installed imports. Production repository remains dirty with unrelated agents' work; no commit, reset, forced push or active source overwrite attempted there.
