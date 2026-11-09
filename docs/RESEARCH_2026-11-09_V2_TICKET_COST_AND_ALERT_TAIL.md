# V2 research — 2026-11-09: ticket-cost stress and downside warning tail risk

**Status: RESEARCH ONLY — NO PAPER/LIVE ORDER GO.** Source: 52-week split-adjusted Alpaca SIP 5-minute completed trade-bar replays through **Nov 6, 2026**. Candidate signal timestamps and prior-five completed-session features were frozen in preceding V2 replay scripts. This analysis reads immutable signal/outcome event ledgers, **does not recompute signals from future closes**, and splits September 1 onward as a holdout. The earlier-period best *shadow* candidate for each sector is locked before later-period performance is examined; none was approved for automatic trading. Results use next-bar proxy marks, not executable prices or actual fills.

## New result 1 — small tickets make already weak signal economics worse

Model: signal-specific gross percentage return to 14:00 ET; 30 basis points assumed roundtrip spread/slippage, **plus $1 per side per order** as a sensitivity case representing a small fixed-fee broker ticket (NOT a verified fee for every Alpaca/IBKR account). Buy and short-sale shadow policies are studied identically for cost stress; no short order was entered. A one-share entry has large percentage friction in cheap ETFs/miners. This is **not** a suggestion to increase position size: bigger tickets increase exposure and tail risk.

| Earlier-selected shadow sector policy | Later test signals / independent dates | Prior 30bp model: profitable, mean net | +$1 entry/$1 exit, 1 share: profitable, mean net | +fees, 5 shares: mean net |
| --- | ---: | --- | --- | ---: |
| Energy (UP) | 11/11 | 5/11 (45.5%), -0.135% | 0/11, -1.253% | -0.358% |
| Financials (DOWN; hypothetical short) | 14/14 | 2/14 (14.3%), -0.513% | 0/14, -4.107% | -1.232% |
| Industrials (DOWN; hypothetical short) | 13/13 | 7/13 (53.8%), -0.263% | 6/13, -0.594% | -0.329% |
| Healthcare (DOWN; hypothetical short) | 12/12 | 5/12 (41.7%), -0.456% | 3/12, -0.730% | -0.511% |
| Software (UP) | 10/10 | 3/10 (30%), -0.982% | 2/10, -1.633% | -1.112% |
| Gold miners (DOWN; hypothetical short, 30m gold lead) | 16/16 | 3/16 (18.8%), -0.676% | 1/16 (6.3%), -4.656% | -1.472% |

The fully day-clustered descriptive bootstrap 95% range for **1-share software** was [-2.518%, -0.759%]; for **gold** [-6.293%, -2.974%]; these are exploratory ranges not independently obtained predictions. Even ignoring the hypothetical fixed commissions, **all six earlier-selected strategies had negative later mean returns**. The price record does not contain complete consolidated NBBO/BOATS spreads, partial fills, borrow availability/costs or matched V1 executions.

## New result 2 — downside warnings are not proven profitable exits, including at 3%

A fresh cross-checked, day-clustered warning-return stress of the original owner overlap condition (a -2.5% total move INCLUDING -1.0 percentage point in the most recent 15m, with SOXX and peers) against other fixed thresholds, on the same later 49-major-decline cohort:

| Absolute total drop plus 1pp/15m/sector breadth | Major downside stock-days detected (out of 49) | Warnings on nonmajor stock-days | Hypothetical early sale benefits vs next regular open (30bp) | Average sale edge | Missed rebound costs >2pp |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2.0% | 40 | 66 | 45/106 (42.5%) | +0.065pp | 24 |
| 2.5% | 39 | 58 | 39/97 (40.2%) | -0.032pp | 23 |
| 3.0% | 39 | 45 | 32/84 (38.1%) | -0.111pp | 22 |

The **2.5%** sell-edge **day-clustered bootstrap 95% interval is -1.390 to +1.396 percentage points**; the 3% interval -1.533 to +1.619. Thus increased warning severity reduces some false positives but is not evidence of profitable automatic exits. Some warnings occur after severe openings and cannot prevent prior-evening gaps. Under the earlier analysis, the earliest completed-bar strict warning was **Nov 13, 2025 at 08:35 ET**, already too late to protect against preceding evening losses. Sept–Nov earliest major warning in this 2.5% subset was **Sep 10, 2026 09:55 ET**.

Maintain **instantaneous WATCH vs separate confirmed SELL** distinction. The owner overlap condition is exactly 2.5% TOTAL inclusive of the last 15m 1pp movement, not 3.5%. Historical 5m bars cannot establish streaming partial fills, stop availability overnight or prospective news/futures confirmation.

## Event universe and accountability

Earlier audited semiconductor sector sessions: **118 positive, 83 negative, 49 mixed** (250 total). Gold miners: **132 positive, 114 negative, 6 mixed** (252). The five independently sampled sectors have 248 complete historical sessions each: energy 114/86/48, financials 102/80/66, industrials 84/71/93, healthcare 55/71/122, software 73/82/93. These are *different sector labels/cohorts* than the per-stock severe-loss cohort and must not be pooled as independent 52-week trials.

Both new analyses use **completed 5-minute SIP price observations** and preserve no-signal sessions in source audits. There are no full synchronized news/futures, complete NBBO/BOATS quote histories, matched V1 fills, or a completed Nov 9 session; consequently no claim of an 80% OOS after-cost profitable-trade rate. Today's PAPER/IBKR actual order sources require separate broker-ledger reconciliation.

## Files and reproducibility

- `research/v2_ticket_cost_and_alert_tail.py`
- `research/test_v2_ticket_cost_and_alert_tail.py` — **9 offline tests passed**, including duplicate signal-day rejection, training split, cost monotonicity, and cluster grouping.
- `research/results/v2_ticket_cost_and_alert_tail_2026-11-09.json` — results with 15/30/60bps and 1/5/10-share hypothetical tickets, medians, minima, day-cluster bootstrap intervals.

Input ledgers on authorized www3 (read-only, generated in prior V2 runs):
`/tmp/v2-run17-cross-sector-precision/results.json.events.json`,
`/tmp/v2-run17-cross-sector-precision/results.compact.json`,
`/tmp/v2-run18-research/gold_lead_lag.json.events.json`,
`/tmp/v2-run18-research/gold_lead_lag.compact.json`,
`/tmp/v2-run16-semis-atr/adaptive_results.json.events.json`.

Run via `PYTHONPATH=. python3 -m research.v2_ticket_cost_and_alert_tail --output /tmp/results.json` and `python3 -m unittest -v research.test_v2_ticket_cost_and_alert_tail` from research checkout. No network/broker access.

**NO GO** for new strategies. Leave active V1 PAPER/LIVE timers, strategies, broker accounts, protective orders, and the dirty production and diverged V2 working trees unchanged. Next: real NBBO/BOATS quote fill simulations, timestamped prior-evening earnings/futures/news, conservative fixed per-ticket broker fees and sizing, later independent sample/V1 execution matching, and calibrating high-precision entry-only gates with adequate independent profitable trading days.
