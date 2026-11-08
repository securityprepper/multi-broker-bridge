# 52-week prior-five-session sector context + inverse ETF and opening-reversal research
_Date: 8 Nov 2026. HISTORICAL RESEARCH ONLY; no deployed PAPER or LIVE strategy changed._

## Timing and information integrity

The sector label for each trading day **d** uses exactly the five **completed** trading-day close-to-close returns ending on **d−1**: prior close on trading date d−1 divided by close on d−6. This excludes the day under evaluation and every later day. Sector up = >=2 of AMD, MU, SNDK higher plus SOXX higher; down = >=2 lower plus SOXX lower; else mixed. All SOXX data are split-adjusted (3-for-1 split Nov 5, 2026). First six trading dates may lack a complete prior five-day interval.

Historical sources: Alpaca 5-minute SIP split-adjusted observations Nov 7 2025–Nov 6 2026, and daily observations, for AMD MU SNDK SOXX, five held-out semiconductor stocks NVDA AVGO WDC TSM INTC, inverse semiconductor 3x ETF SOXS, bullish semiconductor 3x ETF SOXL. No BOATS 8 PM–4 AM included in the year-long 5-minute replay; marketable quotes and actual broker fills not available. Single-order budget max $2,000, per-side price buffer 0.15% except indicated stress tests. Signal parameters selected after earlier study of Nov 6. This is not a clean independent holdout.

## Historical long and bearish signals: prior 5 COMPLETED trading days

Long strategy from earlier research: positive breadth + recent breakout; long nine semiconductor names; premarket hypothetical 8:30 AM ET limit exit, 0.15% per-side price allowance. **36 active days**, **26 profitable (72.2%)**. Modeled total +$3,532.27 (314 modeled round trips).

Mirrored bearish rule: short nine semiconductor stocks. **46 active days**, **13 profitable (28.3%)**, approx −$6,043.62 modeled P/L, excluding actual borrowing. It is a diagnostic only, not suitable for trading.

| Prior five-day trend | Long winning/active | Long win % | Mirrored short winning/active | Mirrored short win % |
|---|---|---:|---|---:|
| Up | 9/15 | 60.0% | 7/19 | 36.8% |
| Down | 16/19 | 84.2% | 5/22 | 22.7% |
| Mixed | 1/2 | 50.0% | 1/4 | 25.0% |
| Insufficient history | 0/0 | — | 0/1 | 0% |

For bullish results, opposite prior-five-day direction (signals up after downtrend) was more profitable than alignment: 84.2% vs 60%. For short mirror, opposite direction was also less bad: 36.8% vs 22.7%. This is a descriptive 20-session active-day difference subject to small-sample uncertainty.

## Replace shorting with a real bearish ETF SOXS

SOXS is a daily −3x semiconductor ETF (daily objective, high leverage and reset risk); its price must be modeled directly, not by mechanically multiplying SOXX inverse by three. Direxion: https://www.direxion.com/product/daily-semiconductor-bull-bear-3x-etfs

Same bearish signal timestamps as mirrored shorts, but **buy SOXS** with max $2,000, simulate 8:30 ET extended-hours exit. Five-minute OHLC limit touches are assumed fillable and do not establish actual bids/asks. 0.15% each-side allowance:

- **46 SOXS active days**, **17 positive (37.0%)**, **29 negative**, **−$947.02 total**.
- Training to Aug 31: −$1,242.31; Sept–Nov 6: +$295.29.
- Prior five-day up: **9/19 winning (47.4%)**, +$180.26.
- Prior five-day down: **6/22 winning (27.3%)**, −$1,031.27.
- Prior five-day mixed: **1/3 winning (33.3%)**, −$88.79.
- Unclassified: two days (one win), −$7.22.
- At 0.30% per-side buffer: 15/46 winning (32.6%), −$1,208.61 total.
- At 0.05% buffer: 18/45 winning (40%), −$635.29 total.

Additional SOXS individual-bar confirmation did not solve it. A two-bar rising SOXS signal plus breakout above prior five-minute high reduced to **36 active days, 15 winners (41.7%)**, training −$699.76, later +$127.13 at 0.15% buffer. Thus still rejected for automated PAPER buys.

## Signal frequency and conflicts

Long signal **36/251 = 14.3%** of full-year days; SOXS bearish ETF signal **46/251=18.3%**; naive union **77/251=30.7%**, with **five dates carrying both sequential long and bearish candidate trades**:
- Feb 5, 2026: long triggered prior evening (Feb 4 16:30 ET), bearish at Feb 5 07:45 ET.
- Feb 6: bearish prior evening Feb 5 16:30 ET, long Feb 6 04:15 ET.
- Apr 30: bearish Apr 29 16:15 ET, long Apr 29 18:15 ET.
- Jul 14: bearish Jul 13 19:35 ET, long Jul 14 04:25 ET.
- Jul 30: bearish Jul 29 17:10 ET, long Jul 30 06:20 ET.
These are chronological reversals within an overnight evaluation period, **not simultaneous same-five-minute bullish and bearish indications**. Never double-buy opposite-direction positions without verifying holdings/order status and actual transition conditions.

## Premarket vs regular direction

For 36 long-signal active days:
- premarket up 34 (94.4%), down 2;
- 09:30–close regular-hours up 13 (36.1%), down 15 (41.7%), mixed 8;
- full prior-close–close up 28 (77.8%), down 2, mixed 6.
Among premarket up days, 15/34 (44.1%) reversed to regular-hours down.

For 45 bearish-signal days with complete phase bars:
- premarket down 36 (80%), up 8, mixed 1;
- regular-hours down 19 (42.2%), up 20 (44.4%), mixed 6;
- full day down 24 (53.3%), up 12, mixed 9.
Among premarket-down days, 17/36 (47.2%) reversed up during the regular session.

These are NOT predictions of the premarket direction—price vs prior close is part of the signal itself. Downside direction is less persistent because early declines frequently reverse, especially after extended selloffs. No causal explanation from news was established.

## Separate regular-market reversal exploration

At 9:40 / 9:45 / 10:00 / 10:15 ET, assess previous premarket sector direction and fresh reversal in the first regular-hours 5-minute closes. If previously up and now sector down: buy SOXS; if previously down and now sector up: buy SOXL. Require 2 leaders plus SOXX reversing and an additional five-minute confirmation, limit entry next 5-minute bar, sell at modeled 2:55 PM ET close.

- All combinations were inconsistent. At 9:40 ET and 0.5% opening reversal threshold: **44 active days, 24 positive (54.5%)**, earlier +$793.13 but later **−$46.37**. Direction split: SOXS candidates net +$980.29, SOXL candidates −$233.53 over the whole year.
- At 9:45, 0.5%: 39 active / 17 positive (43.6%), earlier −$647.96, later −$262.09.
- At 10:00, 0.5%: 42 active / 15 positive (35.7%), earlier −$962.76, later −$23.89.
- At 10:15, 0.5%: 37 active / 21 positive (56.8%), earlier +$626.79, later only +$1.74.
- Opening reversal behavior is sensitive to when the entry triggers, spread/volatility, and intraday adverse excursions. No standalone strategy has passed validation. An 8:30 premarket exit also has materially different economics from 2 PM regular-hours flattening.

## Conclusions

- Best *historical* hit rate remains long premarket following **previously falling** five-day sector trends, 16 winners /19 active, but this is too small to consider proven.
- Do not use current trading week's final outcome as a condition: it is future information at the time of a signal.
- SOXS is a better direct long-only instrument to *test* bearish semiconductor opportunities than borrow-and-short stocks, but it fails this strategy's profitability test (37% winning days).
- Wider annual activity through indiscriminately adding bearish trades increases modeled losing exposure and conflicts; instead test separate regular-session models with broker bid/ask/fill evidence.
- Both bullish and bearish early indicators mostly capture existing premarket direction, not necessarily direction from the open to the close.
- Keep side-specific signal and execution tracking separate; state should transition bearish->neutral->bullish only on fresh bars, not simultaneously.

No deployed PAPER trading automation, schedules, existing broker orders or LIVE safeguards modified by this study.
