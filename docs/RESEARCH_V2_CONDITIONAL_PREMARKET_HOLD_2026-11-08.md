# Rebound Version 2 research: conditional hold after premarket loss
_2026-11-08. This branch is intentionally separate from the ACTIVE V1 monitors and Alpaca PAPER executor._

## Versioning and live safety

- **Version 1 remains active and unchanged:** dedicated Alpaca PAPER five-day rebound runner, separate five-minute observer/Pushover, hourly read-only Task - Five-Day Rebound Alerts, existing company-specific catalyst veto and 8:30 AM ET premarket exit management. V1's existing exit safety and broker reconciliation should NOT be bypassed.
- **Version 2 is historical research only** on GitHub branch `research/rebound-v2-conditional-exits`. Added `research/rebound_v2_rules.py` as a pure causal decision helper; `research/test_rebound_v2_rules.py` (6 tests passed); `research/rebound_v2_conditional_exits.py` exploratory bar replay using the authorized host's existing historical study modules/datasets. No broker orders, V1 files, systemd timers, task schedule or live account state modified.
- V2 should not be enabled to place PAPER orders until it has an independent, broker-reconciled executable implementation and tests of stop and 2 PM CT exit, overlapping strategies, partial fills, and uncertainty.

## Cohort and competing exit policies

Historical 251-trading-session year, AMD/MU/SNDK/SOXX plus NVDA/AVGO/WDC/TSM/INTC, authenticated Alpaca split-adjusted five-minute bars, NO 8 PM–4 AM BOATS coverage for annual test. Exactly five COMPLETED pre-signal trading-session sector returns are down. Nineteen historical qualifying signal days, of which Feb 5 2026 would have been excluded by V1's retrospective company-specific earnings/guidance headline filter. Thus **18 evaluated days**.

Assumption: whole shares, max ~$2k per symbol, up to nine positions. Price allowance 0.15% per side; OHLC next-bar touches for buy and sell, NOT actual broker bid/ask fills or commission. V2 decision made **at 08:30 ET** solely using 08:25-08:30 ET five-minute bar's close (known only at completion) less 0.15% for an approximate sell price. If estimated position gain is positive, use the original premarket sale model. Otherwise leave that specific stock unsold for the RTH test. Each delayed stock then gets a hypothetical time exit at a defined bar CLOSE (availability actually 5 minutes later) or a 2.5% entry-relative stop-market-like trigger after 09:30 ET. These are historical *marks*, not confirmed market sales; overnight losses and gaps between 8:30 and 9:30 are unprotected by this RTH-only stop.

| Historical policy | Profitable days /18 | Model total basket P/L | Worst losing day |
|---|---:|---:|---:|
| V1 all sold at premarket ~08:30 | 16 | +$3,061.63 | −$19.39 |
| V2 hold only loss-making individual positions until 09:30 | 16 | +$3,267.53 | −$19.70 |
| V2 hold losers until 09:45 | 16 | +$3,268.83 | −$109.95 |
| V2 hold losers until 10:30 | 16 | +$3,311.21 | −$183.78 |
| V2 hold losers until 10:30 with 2.5% stop after opening | 16 | **+$3,451.01** | **−$150.30** |
| V2 hold losers until 12:00 with 2.5% stop | 17 | +$3,505.83 | −$150.19 |
| V2 hold losers to 14:55 ET without stop | 16 | +$3,046.44 | −$279.33 |

The 10:30+2.5% hypothetical stop version deferred **25 originally losing individual positions** across the 18 days; 15 eventually produced a positive individual net P/L, 10 remained negative. Their aggregate P/L changed from **−$177.56** (08:30 exit proxy) to **+$211.82** (later marks/stops). 132 other individual positions stayed on 08:30 exit. Only 5 delayed positions activated the simulated stop rule.

**Important risk: March 30** had been a +$13.05 winning basket under V1, but became **−$150.30 under V2's 10:30+2.5% stop**, even as March 4 improved from −$5.57 to +$74.57 and Aug 12 improved from −$19.39 to +$212.94. July 14 +$21.08 became −$41.29, while July 6 +$61.87 improved to +$258.25. Holding losers creates new failed days and is NOT uniformly preferable.

Without the narrow catalyst veto, holding losers in February 5 remained disastrous: 10:30+2.5% stop version February 5 **−$776.45**, and full strategy 17 winners out of 19; the veto is still important.

### Approximate fill sensitivity

For the 10:30+2.5% research version, holding share counts unchanged and charging extra price concessions to both buys and sells (approximate, not actual order-book simulation):
- 0.15% allowance/side: 16/18 positive days, aggregate **+$3,451.01**, worst day −$150.30.
- 0.30% allowance/side: 16/18 positive days, **+$2,600.47**, worst −$201.54.
- 0.50% allowance/side: 15/18 positive days, **+$1,466.43**, worst −$269.86.

This stress remains nominally positive but retains large actual fill and intrabar sequencing uncertainty. The scenario parameters were selected after reviewing known historical dates; no independent out-of-sample evidence exists for this rule.

## Conclusions and next test version

**Research direction supported:** Use the 08:30 ET net-position P/L mark to select whether the specific stock warrants further *RTH exit evaluation*, instead of blindly liquidating all positions or blindly holding everything. A candidate to forward-shadow-test is **positive mark -> request premarket exit; nonpositive mark -> do not add exposure, monitor 09:30+ with controlled 2.5% risk trigger and 10:30 ET latest planned exit**, with broker-confirmed exits and independent 2 PM Central hard-flat guard. **This is NOT the deployed behavior.** Requires a clear rule for overnight/preopen gap and trade/news shocks, and must never let expired or unfilled limit sells accumulate.

Next compare quote-verified spread-sensitive execution at market open, dynamic stop versus time exit, and robust live PAPER order readback. Do not tune the stop to make all 18 historical days profitable; previously positive March 30 demonstrates overfitting risk. The current V1 should remain the reference benchmark.
