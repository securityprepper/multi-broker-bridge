# Sustained Riser H1 alerts — before-and-after outcome audit

**Historical session:** Friday, November 20, 2026 (America/Chicago). **Research-only / no orders.**

## Event definition and audit method

- **H1 trigger:** the first-party Quality Watch/SRM source verified a 60-minute price path with more than +1.5% change, at least 61 completed positive-volume one-minute bars, at least 9 rising five-minute intervals, and four positive fifteen-minute segments. It does **not** require 60 consecutive green one-minute bars.
- **Before:** native recorded signed 5m/10m/30m/1h percentages, previous 3:00 p.m. CT regular close (Alpaca SIP **split-adjusted**, critical for the split), and an actual BOATS completed one-minute trade close within ten minutes after 12:00 a.m. CT, when available. The midnight baseline timestamp is in the CSV; missing means UNKNOWN, never zero.
- **At signal:** original first-party SRM issued_at timestamp and recorded quote midpoint, or latest completed one-minute bar close where no quote was available. Native event time and later ChatGPT message-prepared time are distinct. The latter is **not** evidence of user receipt.
- **After:** actual subsequent volume-positive completed one-minute SIP/BOATS trade closes at +5m/+10m/+30m/+60m and each later integer hour, with the first bar closing at or within 125 seconds after the exact horizon. Percentages are relative to the original source event price; these are **not executable bid/ask fills**, and no fees or slippage are modeled.
- **Close:** 3:00 p.m. CT regular close and 7:00 p.m. CT extended-session close are recorded only with a completed minute bar ending within 125 seconds before the exact close. Close before the alert is NA, not a forward outcome.
- **Midnight following Friday:** no completed trades around 12:00 a.m. CT Saturday were found; Friday trading had ended. All midnight outcomes are UNKNOWN/NO TRADE rather than falsely showing a carried-forward price or 0%.
- **Security/instrument:** one leveraged inverse ETF was analyzed only as a rejected historical instrument case, and one sector ETF was separate. Neither is counted among 35 ordinary-stock events. This report recommends no trade.

## Stock-only results

| Forward horizon | Eligible | Observed | Up | Down | Flat | Mean return | Median return |
|---|---:|---:|---:|---:|---:|---:|---:|
| +5m | 35 | 35 | 10 | 24 | 1 | -0.50% | -0.19% |
| +10m | 35 | 35 | 10 | 25 | 0 | -0.56% | -0.16% |
| +30m | 35 | 35 | 8 | 27 | 0 | -0.58% | -0.42% |
| +60m | 35 | 35 | 7 | 28 | 0 | -1.51% | -0.83% |
| RTH_CLOSE | 35 | 31 | 0 | 31 | 0 | -4.47% | -2.66% |
| AFTERHOURS_CLOSE_7PM_CT | 35 | 18 | 4 | 14 | 0 | -4.03% | -2.72% |
| MIDNIGHT_FOLLOWING_DAY | 35 | 0 | 0 | 0 | 0 | NA | NA |

**Scope warning:** One trading date, correlated signals, some repeated tickers, and no independently verified after-fee trading simulation. These are descriptive first-party event-to-market-bar changes, not an out-of-sample strategy win rate.

**SPY matched one-minute control (stock events only):** At +5/+10/+30/+60m, respective counts outperforming contemporaneous SPY trade-close returns were **8/35, 16/35, 14/35, 17/35**. Median excess returns were **−0.097, −0.022, −0.191, −0.033 percentage points**. These are research comparators, not costs-adjusted tradable spreads.

## Every recorded H1 event (percent)

| Symbol | Event time CT | Since prior close | Since midnight | Pre 1h trigger | +5m | +10m | +30m | +1h | RTH close | 7pm |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MU | 08:09:12 | -3.30% | -0.61% | +2.12% | -0.07% | -0.16% | -3.52% | -2.83% | -10.92% | -8.49% |
| NVDA | 08:27:12 | -1.43% | +0.50% | +2.31% | -1.58% | -1.92% | -1.72% | -4.21% | -12.58% | -9.66% |
| NBIS | 08:28:12 | -2.21% | +0.92% | +5.01% | -5.78% | -5.13% | -1.57% | -5.87% | -14.12% | -10.74% |
| AVGO | 08:28:12 | -1.18% | +0.67% | +2.23% | -1.73% | -1.05% | -1.80% | -6.48% | -11.19% | -9.05% |
| MRVL | 08:30:12 | -3.71% | -1.05% | +1.68% | -2.17% | -3.26% | -0.10% | -4.38% | -8.23% | -5.67% |
| MSTR | 08:32:12 | +1.46% | +2.36% | +3.91% | -0.86% | -2.01% | -3.10% | -6.16% | -10.80% | -9.01% |
| SNDK | 08:33:12 | -6.17% | NA | +3.32% | -0.73% | -2.52% | -1.46% | -7.28% | -10.46% | -8.07% |
| MSFT | 08:36:12 | -0.49% | +0.45% | +2.03% | +0.14% | +0.49% | +1.16% | -0.05% | -2.13% | -1.25% |
| TSM | 08:38:12 | -4.03% | -1.16% | +2.20% | -0.44% | +0.26% | +0.77% | -2.37% | -5.48% | -2.73% |
| GOOGL | 08:39:12 | +1.92% | +2.29% | +3.03% | +0.63% | +0.45% | +1.00% | +0.74% | -4.34% | -2.71% |
| GOOG | 08:44:12 | +2.17% | +2.59% | +3.53% | +0.00% | +0.46% | -0.05% | -0.54% | -4.49% | -2.94% |
| GAP | 09:29:12 | +16.59% | NA | +9.34% | -1.11% | -1.61% | -1.79% | -2.45% | -4.97% | NA |
| PAYX | 09:31:12 | +3.07% | NA | +2.04% | -0.08% | -0.11% | -0.36% | -0.42% | -1.89% | NA |
| CTAS | 09:33:12 | +3.28% | NA | +1.62% | +0.21% | +0.10% | -0.42% | -0.02% | -2.66% | NA |
| PLD | 09:33:12 | +1.75% | NA | +1.51% | +0.16% | +0.10% | -0.30% | -0.21% | -2.35% | NA |
| CPRT | 09:36:12 | +2.80% | NA | +1.68% | -0.02% | -0.06% | -0.24% | +0.08% | -1.94% | NA |
| ACN | 09:37:12 | +4.26% | NA | +2.93% | -0.20% | -0.12% | -0.07% | -0.50% | -2.98% | NA |
| INVH | 09:38:12 | +2.82% | NA | +1.57% | +0.00% | +0.02% | -0.97% | -0.50% | -2.22% | NA |
| KMB | 09:39:12 | +3.56% | NA | +1.53% | -0.17% | -0.08% | -0.58% | -0.73% | -2.36% | -2.07% |
| COST | 09:40:12 | +2.35% | NA | +1.88% | +0.02% | +0.08% | +0.05% | -0.13% | -1.39% | -1.49% |
| VMRK | 09:40:12 | +3.20% | NA | +1.55% | +0.09% | -0.04% | -1.00% | -0.92% | -2.37% | NA |
| GIS | 09:51:12 | +5.09% | NA | +1.54% | -0.19% | -0.15% | +0.36% | +0.08% | -1.42% | NA |
| CHKP | 09:59:12 | +1.65% | NA | +1.67% | -0.70% | -0.42% | -0.82% | -1.37% | -1.85% | NA |
| TSN | 10:37:12 | +2.65% | NA | +1.52% | -0.43% | -0.46% | -0.50% | -1.20% | -0.62% | NA |
| HUM | 11:01:12 | +5.55% | NA | +1.82% | -0.24% | -0.22% | -1.19% | -1.49% | -2.81% | NA |
| LSCC | 12:37:12 | -9.05% | NA | +2.07% | +0.13% | -0.30% | +0.29% | -0.83% | -2.59% | NA |
| AMKR | 12:39:12 | -8.74% | NA | +2.07% | -0.87% | -0.66% | -0.50% | -1.52% | -3.02% | -1.46% |
| PWR | 12:39:12 | -4.51% | NA | +1.55% | -0.37% | -0.23% | -0.14% | -0.99% | -0.26% | NA |
| CEG | 12:41:12 | -2.58% | NA | +1.58% | -0.41% | -0.44% | -1.01% | -2.01% | -3.22% | NA |
| IR | 12:57:12 | -0.54% | NA | +1.51% | -0.41% | -0.21% | -1.27% | -1.20% | -2.22% | NA |
| HCA | 13:23:12 | +4.04% | NA | +1.51% | +0.07% | -0.10% | -0.73% | -0.29% | -0.63% | NA |
| MUZ¹ | 14:02:12 | +26.42% | +20.09% | +3.46% | +1.29% | +1.09% | +1.95% | -0.63% | +1.03% | -4.87% |
| NVDA | 15:57:12 | -11.58% | -9.85% | +3.27% | -0.17% | -0.46% | -0.00% | +0.13% | NA | +0.71% |
| MU | 15:58:12 | -12.21% | -9.77% | +2.93% | +0.05% | -0.44% | -0.07% | +0.47% | NA | +0.79% |
| INTC | 16:02:12 | -5.28% | -2.64% | +1.91% | -0.21% | +0.36% | +0.39% | +1.23% | NA | +0.61% |
| NBIS | 16:03:12 | -13.32% | -10.54% | +2.95% | -0.12% | +0.36% | +0.77% | +1.49% | NA | +0.69% |
| SOXX² | 16:03:12 | -8.60% | -6.54% | +1.55% | +0.02% | +0.17% | +0.67% | +1.08% | NA | +0.32% |

¹ Historical leveraged inverse ETF; excluded from ordinary-stock statistics and no trade candidate. ² Sector ETF, reported separately.

## Full hourly chronology

The companion [hourly forward CSV](SRM_20261120_HOURLY_FORWARD.csv) contains **469 event×hour observation rows** through midnight with observed timestamp, feed, trade volume, actual completed trade close, and explicit NO_FRESH_COMPLETED_1M_TRADE when no recent trade exists.
The companion [signal summary CSV](SRM_20261120_SIGNAL_SUMMARY.csv) contains all before/after changes, original source quote evidence, split-adjusted reference times, native event and ChatGPT preparation times, and each horizon status.

## Safety conclusions

- Recalculate returns on at least 20 distinct completed sessions with genuinely untouched forward time windows before adjusting signal or execution policies. A single severe market-down session is insufficient to infer a durable negative or positive predictive edge.
- Verify receiving-broker executable spreads, fill IDs, fees and slippage separately before claiming a profitable strategy; research never places or modifies PAPER/LIVE orders.
- Keep the native SRM event deduplication ledger and reporting-owner mandate intact. This retrospective outcome audit does not synthesize H2 events or rewrite sent-event keys.