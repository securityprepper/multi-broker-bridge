# V2 low-false-alert threshold calibration — November 9, 2026

**Status: V2-only restrictive configuration applied on authorized www3 and research branch. No V1 PAPER/LIVE changes, no broker orders or strategy activation.**

## Owner requirement
Avoid noisy false predictive stock/sector alerts. A price threshold can screen for a **rare factual extreme**, but its mere breach is not evidence of additional profitable movement. Preserve genuine position-risk, failed protective exits, broker/data-integrity failures and owner-required individual-stock 2.5%-total INCLUDING 1.0pp/15m warnings separately.

## Newly selected quiet sector screening levels

| Sector ETF | RTH day % from 09:30 open | Night % from previous RTH close | Historical daytime confirmed events | Night observed 2-bar SIP confirmations |
|---|---:|---:|---:|---:|
| SOXX semiconductors | **5%** | **5.5%** | **11** | **7** |
| GDX gold miners | **5%** | **7%** | **4** | **4** |
| XLE energy | **3%** | **3.5%** | **2** | **6** |
| XLF financials | **3%** | **3%** | **1** | **0** |
| XLI industrials | **3%** | **3%** | **1** | **1** |
| XLV healthcare | **3%** | **3%** | **0** | **0** |
| IGV software | **4%** | **4%** | **7** | **3** |

52-week split-adjusted Alpaca SIP 5m historical data through Nov6, 2026; approx 250 days per sector with strictly 5 prior completed RTH days for signals. One first signal per sector/day, ETF threshold requires **two consecutive completed five-minute closes** in same direction (NOT intrabar high/low); same-timestamp breadth must agree for at least two of three stocks or both of two. Observed after-hours and premarket overnight 5m SIP two-bar counts exclude 20:00–04:00 BOATS and can miss events. Day and night counts are distinct sessions, not cumulative counts of opportunities.

## Why simply changing percentages DOES NOT ensure predictive accuracy

With a new signal at the completed 5m bar boundary, measure future price change from **that** observed ETF mark to its 60-minute-ahead completed bar. Additional same-direction gross +0.5% follow-through occurred on:

| Sector | Confirmed RTH extreme alerts | Additional 0.5% same-direction within 60m |
|---|---:|---:|
| Semiconductors | 11 | **2** |
| Gold miners | 4 | **0** |
| Energy | 2 | **1** |
| Financials | 1 | **0** |
| Industrials | 1 | **0** |
| Healthcare | 0 | — |
| Software | 7 | **0** |
| **Total** | **26** | **3** |

That is **3/26 (11.5%)**, and that's before any execution costs, spreads or slippage. These are repeatedly researched historical in-sample or partially explored later dates, not genuinely untouched prospective performance. The **factual breach** may have been accurately observed, but claiming that it forecasts further gains/losses would create many false alerts. A +0.5% gross future move is also neither verified execution nor assured profitability.

**Enforced low-noise policy:** Raw extreme crossings are retained INTERNAL/RESEARCH ONLY; no price-only predictive push or automatic BUY, CLOSE, SHORT from new threshold config. Future actionable forecast alerts require independently tested positive *post-signal* forward precision and after-cost edge plus verified quote freshness, breadth, calendar, broker protective stops and cross-strategy order dedup. Always preserve critical safety/exit/fill/data errors. One alert maximum per sector + direction + session if eventually commissioned. Do not suppress existing V1 safety warnings or falsify their meaning.

## Scope and operational verification
- Config GitHub: `research/config/v2_emergency_thresholds_2026-11-09.json` (schema v2). Installed root-owned as `/opt/securityprepper/news-watch-v2/sector_thresholds_v2.json`; previous config backed up to `/tmp/v2_thresholds_pre_low_noise_backup_20261109.json`.
- Four Trading Opportunity prompts plus Semiconductor Downside Warnings, Five-Day Rebound Alerts and Trading Strategy Research task prompts updated; all schedules and enabled states preserved.
- The existing news monitor is a separate read-only GET-only service and its timer remains enabled.
- The independent existing V2 `semis-downside-v2-warning` sidecar still uses its **separate factual safety-warning** criteria and cannot be represented as already using these new screening percentages. It does not place orders. Its low-specificity Pushover `sector_watch` was previously muted; stock-urgent and severe-risk paths remain for safety. V1 remains untouched.
- No 7-sector predictive Pushover publisher or automatic trade executor was commissioned. This V2 threshold policy is the valid configuration for V2 research and task filtering; additional independently reviewed implementation is needed before claiming full host publisher deployment.
- Host regression: six synthetic no-lookahead tests passed, including missing future bars remaining unscored and prior five completed days. 52wk results are stored in `research/results/v2_low_noise_alert_precision_2026-11-09.json`, replay in `research/v2_sector_alert_precision_grid_20261109.py`.
- Holiday cache revision2 unpaused until Nov13 2026 16:13 CST absent calendar edit; no schedule/holiday gate changed.
