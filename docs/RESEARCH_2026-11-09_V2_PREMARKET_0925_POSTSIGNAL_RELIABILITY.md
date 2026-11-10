# V2 09:25 ET premarket breadth — actual **post-signal** reliability (2026-11-09)

**Research only, not an execution authorization.** This is a new 52-week Alpaca adjusted SIP 5-minute study of all seven sector ETFs and their own stock peers through **2026-11-06**. Prior work's 10:05 ET same-day-direction scores were retrospective and inflated by price moves *already observed before the signal*. This study uses the **09:20–09:25 completed ETF candle**, observable at **09:25 ET (08:25 America/Chicago)**, to forecast what happens **after** the signal. A hypothetical entry is then marked at the next regular-session **09:30 ET open**, and exit at **14:40 ET (13:40 Chicago)** to respect the owner's 2 p.m. latest-flat objective.

## Causal admission and outcomes
- ETF and stock previous-close references use **strictly prior five fully completed RTH sessions**; the preceding completed session must be identical for ETF and every required peer.
- Signal on the completed 09:20-09:25 SIP 5-minute ETF bar only, price `>=0.5%` above/below previous RTH close, same direction confirmed by **two peers** moving `>=0.25%` in the same direction. Require each peer's last completed 5m SIP price to be <=10 minutes stale at 09:25; for the two-peer sectors, both must confirm. Unavailable 09:20 ETF bar produces **ABSTAIN**, not a dropped eligible day.
- Score prospective **UP/DOWN from 09:25 signal-mark to 14:40 ETF mark**, `>=0.05%` same direction counts as forward-direction hit; tiny moves below that are not hits.
- Separate hypothetical stock/ETF directional entry at 09:30 RTH open ETF mark and 14:40 completed 5-minute ETF mark exit minus **illustrative** 0.30 percentage-point friction roundtrip. Shorts are directional price proxies, **not** borrow-approved short/inverse executions; actual bid/ask, fills, fees, and brokerage constraints are unavailable. Cash/no-trade benchmark is zero.
- Historical 70/30 chronological split is only an exploratory **reused** later period. This history has been examined repeatedly and is **NOT genuinely unseen out-of-sample validation**; the 0.5% threshold is a descriptive common-screen comparison, not a live-locked strategy.

## 0.5% own-sector signal: last approximately 75 reused historical days

| ETF sector | Alerts/eligible days | Future correct >=0.05pp | Illustrative after-30bp winners | Mean after-30bp modeled trade |
|---|---:|---:|---:|---:|
| SOXX semiconductors | 63/75 | 31/63 | 30/63 | **−0.2111%** |
| GDX gold miners | 48/75 | 23/48 | 17/48 | **−0.4016%** |
| XLE energy | 53/75 | 16/53 | 10/53 | **−0.5595%** |
| XLF financials | 17/75 | 6/17 | 5/17 | **−0.6000%** |
| XLI industrials | 14/75 | 6/14 | 3/14 | **−0.3779%** |
| XLV healthcare | 20/75 | 9/20 | 7/20 | **−0.4911%** |
| IGV software | 27/75 | 16/27 | 14/27 | **+0.0387%** |

Software is a **weak, not validated apparent exception**: its 0.5% screen was **−0.1889%** mean in the earlier period. A higher 0.75% software gate was **−0.2816%** earlier, **+0.0906%** later (11/22 illustrative after-cost wins). No threshold has demonstrated independent >=80% after-signal precision or dependable positive after-cost expectancy. Other sectors' 0.5% mean modeled return was negative in both earlier and later periods. A strict 09:25 buy/short based on sector movement should remain **research-only, no PAPER activation**.

## Premarket data availability is itself an important failure mode

Over **1,743 fully prior-five-eligible sector-days** (248–250 per sector), exact 09:20 ET ETF SIP bars were available on: SOXX 246/248, GDX 248/248, XLE 241/250, XLF 220/250, **XLI only 80/250**, **XLV only 125/249**, IGV 196/248. Also, gold miner sector had all required fresh peers on 191/248 days. A monitoring agent MUST abstain on these missing quotes, rather than using stale prices or relabeling zero trade activity as flat. Missing after-20:00 ET SIP coverage is not BOATS evidence. Full NBBO and BOATS quote tapes remain necessary.

## Two-sided realized daily sector outcomes (for auditing misses; NEVER used to make signals)

The accompanying **1,743-row daily CSV** records a completed RTH 15:55 ETF close, previous-close-to-close percentage, open-to-close percentage and >=3% actual sector move separately from the causal 09:25 signal. Thus every significant up or down day is auditable, including **days with no alert**. From these eligible days:

| Sector | >=3% up close-to-close days | <=−3% down days | No 09:25 signal on these large-move days |
|---|---:|---:|---:|
| SOXX | 32 | 39 | 3 |
| GDX | 42 | 41 | 17 |
| XLE | 4 | 7 | 2 |
| XLF | 1 | 1 | 1 |
| XLI | 3 | 3 | 4 |
| XLV | 3 | 0 | 1 |
| IGV | 19 | 16 | 14 |

These descriptive same-day large-move labels **do not measure post-signal correctness** and must never be used as the numerator of forecast precision. A sign can appear correct against the previous close yet be a losing subsequent trade. Same-session charts and executed marks are not necessarily fillable.

## Validation / operational boundaries

Nine new synthetic tests PASS: five prior completed days; same-day future-value mutation cannot affect the signal; missing exact premarket bar must count as abstention; two-of-three peer confirmation; quote freshness; after-cost trade and forecast price references kept separate; tiny post-signal move is not a hit. All branch modifications are under `research/` and `docs/`. Production `/opt/securityprepper/multi-broker-bridge` and the divergent older research checkout remain unchanged, and **no Alpaca or IBKR order, account, permission, V1 service/timer or holiday gate** was changed.

New source: `research/v2_premarket_0925_after_signal_seven_sector_20261109.py`.
Tests: `research/test_v2_premarket_0925_after_signal_seven_sector_20261109.py`.
Full grid: `research/results/v2_premarket_0925_after_signal_seven_sector_2026-11-09.json`.
All-day detailed audit: `research/results/v2_premarket_0925_after_signal_seven_sector_2026-11-09_daily.csv`.

**Next:** Collect genuinely new forward untouched trading days, snapshot exact as-of 09:25 ETF+peers with timestamp and freshness, add point-in-time SIP/BOATS executable NBBO and news/futures provenance, apply **PAPER-only staged release and independent review** before permitting new orders. Preserve the MBB diagnostic investigation of its November 9 03:18 AMD skip until prospective `buy_watch_symbols`, `skipped_buy_reasons`, account, quote, position and sector status evidence exists. FDR new entries remain paused. Existing 13:15 Chicago entry cutoff, 13:40 flatten and 14:00 verification for previously approved strategies remain in force.
