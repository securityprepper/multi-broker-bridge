# V2 owner thresholds & full-year event counts (2026-11-09)

**Research/alert-policy configuration only. NO orders placed, no broker LIVE/PAPER or V1 timing/strategy changes.** Owner-requested percent levels are set in `research/config/v2_emergency_thresholds_2026-11-09.json` and root-owned on www3 at `/opt/securityprepper/news-watch-v2/sector_thresholds_v2.json`; the four Trading Opportunity task prompts, the read-only Semiconductor Downside Warnings task, and the Trading Strategy Research task have been updated without changing their schedules. The thresholds are not yet commissioned as seven-sector minute-level Pushover or order executor rules. The older independent semiconductor V2 risk sidecar has separate observed-risk criteria, and its V1 safety controls remain unchanged.

## Definitions for historical frequency

* **Day (09:30–16:00 ET):** Start at that regular session's 09:30 opening trade-bar OPEN, and count day as crossed if *any five-minute high/low* touched the signed absolute threshold before 16:00.
* **Day closing movement:** Compare regular-session opening price to final 15:55–16:00 bar CLOSE; this is deliberately narrower than an intraday touch.
* **Night:** Use preceding completed regular-session final close as baseline; examine prior after-hours SIP high/low (16:00–20:00), current premarket SIP high/low (04:00–09:30) and subsequent 09:30 regular opening GAP. 20:00–04:00 BOATS bar history is not complete for these seven ETF inputs, so **night intraperiod touch counts can MISS moves that reverted during BOATS hours**, and may include thin-volume extended trade spikes. The separate next-open gap column is more robust but cannot detect temporary overnight excursions.
* UP and DOWN are counted separately; a violently reversing date can count in both signs, while its overall date counts only once. Only completed 52-week history through November 6, 2026 is included; today November 9 is excluded.

## Counts at requested thresholds (last 52 weeks)

| Sector ETF | Day +/- % | RTH days touched UP | DOWN | Unique RTH days touched | Two-adjacent-5m-close confirmation (unique days) | RTH open-to-close days beyond threshold | Night +/- % | Observed night UP | DOWN | Unique night sessions touched | Next RTH opening gap beyond threshold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SOXX semis | 2 | 73 | 77 | **145 / 253** | **118** | 74 | 3 | 34 | 33 | **66 / 252** | 40 |
| GDX gold miners | 2 | 73 | 83 | **149 / 255** | **126** | 75 | 2 | 72 | 64 | **134 / 254** | 90 |
| XLE energy | 3 | 4 | 6 | **10 / 253** | 6 | 3 | 3 | 6 | 4 | **10 / 252** | 6 |
| XLF financials | 3 | 1 | 2 | **3 / 253** | 2 | 1 | 3 | 0 | 0 | **0 / 252** | 0 |
| XLI industrials | 3 | 0 | 2 | **2 / 253** | 1 | 1 | 3 | 1 | 0 | **1 / 252** | 1 |
| XLV healthcare | 3 | 0 | 1 | **1 / 253** | 1 | 1 | 3 | 0 | 0 | **0 / 252** | 0 |
| IGV software | 3 | 17 | 22 | **39 / 253** | 39 | 20 | 3 | 6 | 7 | **13 / 252** | 5 |

Using only last-bar closing moves rather than high/low touches, some counts fall significantly. Example: semiconductor 2% RTH touched 145 days but only 74 finished >=2% from open; gold miners 2% touched 149 but only 75 ended there. A 2% intraday observed warning is therefore common, NOT a validated forecast of additional movement and NOT sufficient for automatic trading.

## Execution and alert safety

V2 owner policy requests completed-five-minute-price confirmation (preferably two aligned bars), reliable independent sector breadth, fresh quotes, holiday/session source of truth, and independent **after-signal** predictive confirmation before considering EMERGENCY; the raw threshold is WATCH-level factual observation. The independent strict individual stock weakness warning of -2.5% total **including** -1pp in 15 minutes remains distinct and does not authorize auto-sells. No changes to V1 controls, PAPER/LIVE broker orders, installed safety exits or the 2pm Chicago latest-flat objective. The currently installed V2 experimental semiconductor risk sidecar is a different policy and must be reconciled with the owner thresholds before claiming all host notifications use them.

## Reproducibility

* `research/v2_emergency_threshold_full_year_20261109.py` — 52-week SIP split-adjusted completed 5m data audit using 09:30 RTH open, intraday high/low and prior close for night.
* `research/test_v2_emergency_threshold_full_year_20261109.py` — 6 passing tests for day/night reference, signed threshold crossings, reversals, gap-only nights, duplicated signs and owner configuration.
* `research/results/v2_emergency_threshold_full_year_summary_2026-11-09.json` — exact aggregated counts, including both-direction overlap and close-to-close overnight opening gaps.
* Original full daily/night observations on www3: `/tmp/v2_emergency_threshold_full_year_20261109.json`. The 20:00–04:00 missing historical BOATS data and questionable thin extended trades remain important uncertainties.

**Trade origin note:** The connected IBKR app is not an order-submitting tool in this research workflow; its trade/order queries do NOT expose an account number or PAPER/LIVE environment. The IBKR gateway host advertises a PAPER profile, but cannot be matched to the connected plugin account from this evidence. The plugin's observed buy/sell trades are BROKER activity, not orders submitted by research. Verify any QQQ/ANET protective order status marked `REPLACED` directly with IBKR rather than assuming they are currently working.
