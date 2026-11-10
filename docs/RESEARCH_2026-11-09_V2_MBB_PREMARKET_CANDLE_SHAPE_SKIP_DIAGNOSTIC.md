# V2 MBB premarket candle-shape versus early net-breadth research — November 9, 2026

**Status:** RESEARCH ONLY. No V1 PAPER/LIVE strategy, broker, host timers, cash, positions, holiday gate or execution policy changed. Data are 20 *previously researched* market sessions, not new prospective days or independently untouched OOS.

## Critical Nov 9 03:18 CT reconstruction boundary

The authorized `trading-sector-paper-executor.service` journal at **2026-11-09 03:18:41 Chicago** records exactly **candidate_count=7**, **tracked=3**, **gate_allows_new_entries=true**, **feed=sip**, with only **AVGO** and **INTC** buy order requests. Crucially, this historical JSON **does not have** `buy_watch_symbols` or `skipped_buy_reasons`; the new sanitizer independently confirms `DIAGNOSTICS_MISSING`. `candidate_count` counts BOTH BUY_WATCH and EXIT_WATCH, and does **not** prove that AMD was itself a BUY_WATCH. Nothing in this historic line proves whether AMD was rejected by the trend-engine signal, fresh quote, existing position/order, per-order notional, account cash, software-state reservation or another branch.

Read-only inspection of the V1 engine's **preexisting Nov7, 2026 committed code** (trend module) identifies a **material signal mismatch:** historical own-sector AMD/MU/SNDK 3/3 **positive net change** need not satisfy MBB's actual BUY_WATCH predicate. MBB requires **four completed 1m bars with three consecutive increasing highs AND lows** for the target stock, no >2.5% single-bar leap, and >=2/3 qualified *rising-shape* anchors; freshness <=135 seconds. A contemporaneous 3/3 comparison to previous close is **not equivalent**. The read-only `trend.py` comparison confirms that these rising-shape and anchor conditions existed in committed Nov7 code before the 03:18 Nov9 scan. It does **NOT** establish that this was the exact AMD skip reason on Nov9; the actual 03:18 AMD candle history plus broker as-of inventory/quotes or new next-session diagnostics are still required. No fabricated reason.

## Newly tested independent structural question: does stronger 3/3 net breadth imply an MBB BUY?

Archive: authorized prior Alpaca SIP split-adjusted **one-minute trade** data `/tmp/sector_complete_20session_alpaca_mixed.json`, 20 sessions **October 12–November 6, 2026**, AMD/MU/SNDK, daytime input only. Scan 04:00:40–08:35:40 ET, equivalent 03:00:40–07:35:40 CT. Never use a candle beginning after the signal, always require completed candle and emulate MBB `end=now-30sec` 1min feed. Independent comparison rule: AMD and all three named leaders **>=+0.2%** over *their own previous completed regular close*, with last completed SIP print within 10m. Actual MBB-shape rule uses the four-bar highs/lows and its 135-second freshness. One earliest event per day per rule; no future price is used for either qualifying signal.

| Metric | +0.2% own-sector 3/3 net breadth | Exact *signal-shape* MBB AMD BUY_WATCH candidate (before broker gates) |
|---|---:|---:|
| Days with a candidate of 20 | **10** | **12** |
| Dates with 3/3 net breadth but **never** a qualifying MBB AMD shape | **4 of 10** | n/a |
| Total qualifying minute observations across 20 sessions | **2,337** | **39** |
| Among those 2,337 3/3-breadth minutes, no MBB AMD four-bar confirmation | **2,311 (98.9%)** | n/a |
| Both strategies have an earliest qualifying day | **6 days** | **6 days** |

Where both first signals exist, the MBB signal-shape first occurs **4, 19, 27, 135, 189 or 244 minutes** after the 3/3 net-breadth first signal (median **81 minutes**). The net-breadth test can also trigger well before MBB and miss subsequent reversals, so elapsed delay is NOT lost executable profit.

## After-signal price-mark stress (NOT broker fills)

Both isolated rules are simulated as separate AMD-only bullish long signals, buying at the **first later SIP one-minute bar OPEN within five minutes**, then holding without a protective stop until **14:40 ET / 13:40 CT** opening trade mark; subtract hypothetical **0.30 percentage points** roundtrip friction. Not an executable ask/bid fill or safe exit policy. Outcomes counted from *after signal*, not from the previous RTH close, and the first/later 10 splits already explored by earlier research.

| Signal | Scored trades | Positive simulated after 30bp | Mean net per signal | Worst simulated net | Worst intratrade adverse move |
|---|---:|---:|---:|---:|---:|
| Early 3/3 net breadth | **10** | **7 / 10** | **−0.2923%** | **−9.5003%** | **−9.3479%** |
| MBB four-bar shape | **12** | **5 / 12** | **−2.3553%** | **−12.9912%** | **−15.1867%** |

A central negative case was **November 2**, when early 3/3 breadth subsequently reversed (modeled −9.5003% after 30bp) and waiting for the stricter MBB 4-bar shape STILL lost (−8.6588%). This demonstrates that simple earlier positive breadth and a later monotone microtrend are both insufficient as standalone no-stop signals. **Neither** warrants PAPER entry or increasing exposure. Tail outcomes require hard position risk controls; with a working stop they could differ substantially and with illiquid overnight bids could be worse than the illustrative marks.

The analysis identifies a **signal-definition mismatch** explaining why a retrospective earliest sector net-breadth timestamp cannot be equated with an executable MBB BUY_WATCH, but does **not** solve the specific 03:18 AMD skip. Do not conflate source candle price with contemporaneous executable ask, possible broker position, order inventory or cash eligibility.


## Additional true post-signal 15- and 60-minute forward outcomes

A separate replay uses the AMD **last completed one-minute CLOSE available at the :40 scan** as its starting mark, then the latest *completed* SIP close available exactly +15 or +60 minutes later, with stale/missing marks abstained. No past move from previous close is credited, and the 30bp hurdle is hypothetical (not actual ask/bid execution cost).

| First causal signal | Qualified dates | +15m >30bp favorable | +60m >30bp favorable | Mean +15m after 30bp | Mean +60m after 30bp |
|---|---:|---:|---:|---:|---:|
| 3/3 own-sector net breadth | **10** | **3 / 10** | **2 / 10** | **−0.1197%** | **−0.3031%** |
| MBB four-bar AMD rising shape | **12** | **3 / 12** | **4 / 12** | **−0.3231%** | **−0.2140%** |

The stricter pattern does not establish better future edge, and the earlier 3/3 signal does not attain 80% after-cost precision; +60m is 20% for the 3/3 variant at the 30bp threshold. The longer to-13:40 CT nominal hold-win rate 7/10 for 3/3 **must not** be substituted for this actual post-signal 60-minute result. Data are repeatedly researched, not untouched holdout. A severe Nov2 intraday reversal demonstrates why false bullish alerts and protective exits need their own testing.

New code `research/v2_mbb_shape_forward_15m_60m_20261109.py`, 6 additional no-lookahead tests and full JSON under `research/results/v2_mbb_shape_forward_15m_60m_20261109.json`. Total of **26 targeted offline tests passed** (12+8+6).

## Diagnostic solution committed for a future eligible session, no broker/API connections

`research/v2_mbb_next_session_skip_diagnostic_20261109.py` accepts already-collected `journalctl -o short-iso` lines and emits only sanitized symbol/decision codes (no quote, cash, account ID, token or order UUID). It separates:
- `DIAGNOSTICS_MISSING`: historical candidate count does not identify AMD's signal;
- `NO_BUY_WATCH_EMITTED_REASON_UPSTREAM_UNPROVEN`: inspect target and anchor four-bar shapes, stale quotes and sector qualification;
- `BUY_WATCH_SKIPPED_WITH_RECORDED_REASON`: report actual installed `skipped_buy_reasons` code, not speculation;
- `BUY_WATCH_WITHOUT_SKIP_OR_ORDER_CHECK_RESERVATION_AND_BROKER`: inspect atomic reservation state and independently read broker;
- `BUY_ORDER_REQUEST_RECORDED_BROKER_FILL_NOT_PROVEN`: follow with broker fill confirmation, never treat pending_new as filled.

Run read-only on a future eligible date **after** that session's journal exists; verify fresh quotes, broker positions/open orders and account/sector status independently via authorized read-only broker tools. This research task does NOT activate collection or change V1. 26 offline tests (12 as-of/no-lookahead shape/outcome + 8 sanitized diagnostic + 6 strict post-signal horizons) passed on www3.

## Limitations and next test

One-minute trade OHLC is NOT historical NBBO/BOATS ask/bid depth and cannot certify 03:18 executions; the replay lacks broker cash, working order locks, independent prior-five volatility regime calibration, per-account quantity, stop and fee receipts. The 20 days were already researched, so apparent 7/10 favorable trade-count is not prospective 80% reliability (and its average return is negative). Require **20+ untouched future eligible sessions**, holdout post-signal signed returns, executable spreads/filled broker receipts, tail and drawdown comparisons, and safe reentry/stop controls before considering new PAPER GO. No automatic higher-price losing-stop reentry, no short/inverse permissions or LIVE changes.

Research outputs: `research/v2_mbb_early_shape_vs_breadth_20261109.py`, `research/v2_mbb_shape_vs_breadth_forward_20261109.py`, two test suites, `research/v2_mbb_next_session_skip_diagnostic_20261109.py`, JSON and 40-row result CSV under `research/results/`. All scripts run offline; none submits orders.

Holiday: validated unpaused rev2 `next_check_at=2026-11-13T16:13:00-06:00`, coverage through 2036-10-25, no known calendar edit. No schedule changes.
