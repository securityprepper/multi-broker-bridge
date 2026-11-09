# V2 Research — 20-session anti-churn stop stress and PAPER source attribution (2026-11-09)

**RESEARCH ONLY. Do not change live V1 PAPER/LIVE monitors, orders, exits, host timers or strategy activation.** Holiday-cache state remains unpaused revision 2 valid only before November 13, 2026, 16:13 America/Chicago absent calendar edits.

## Important correction: profitability is only AFTER signal

Previous 10:05 ET sector full-day classification was 88%–95% accurate largely because some of the move was already visible. This research deliberately measures **prospective returns after an as-of-09:35 signal**, and separates real broker filled-order attribution from hypothetical simulations. It is not a trading GO.

## 20 actual historical market sessions, both directions

Oct 12–Nov 6, 2026; Alpaca SIP one-minute historical trade bars for SOXX/AMD/MU/SNDK. Forecast at 09:35 ET using only completed 09:34 ET bar and the previous five completed regular-session daily closes. Qualify SOXX +/-0.2% from previous close with >=2 of three peers confirming +/-0.2%. Trade the qualifying stock symbols at the 09:35 **next-minute OPEN proxy**, directional short exposure on DOWN dates is simulated and not verified borrow. All stops inspect completed one-minute close and fill at **following one-minute OPEN**. Final flat proxy is 14:40 ET = 13:40 Chicago, 20 minutes before owner's latest 2pm CT flat objective. The 20-session universe yields 18 signal days and 54 hypothetical first entries (27 in first 10 trading days, 27 in last 10). Research data are SIP trades, **not NBBO executable quotes, actual fills, liquidity, partial fills or stock-borrow verification**. Cost stress subtracts 0.30 percentage points round-trip per trade, then 0.60 in sensitivity.

| Causal exit policy | 20-session winners after 0.30pp | All trades mean after 0.30pp | Earlier 10 mean | Later 10 mean | Worst trade after 0.30pp |
|---|---:|---:|---:|---:|---:|
| Unconditional hold until 13:40 CT | 33/54 (61.1%) | +0.6361% | −0.4645% | +1.7367% | −5.5987% |
| 1-minute sector/stock reversal | 14/54 (25.9%) | −0.2844% | −0.7508% | +0.1820% | see original comparison |
| +/-1% target/stop on completed price | 24/54 (44.4%) | −0.4351% | −0.8156% | −0.0546% | see original comparison |
| 5-minute trend-aware/emergency exit | 17/54 (31.5%) | −0.4417% | −0.9934% | +0.1099% | see original comparison |
| 1-minute stop with one same-day reentry | 25/108 (23.1%) | −0.3504% | −0.5790% | −0.1218% | not directly comparable trade count |
| **New** hard -1.5% stop | 21/54 (38.9%) | −0.0996% | −0.7961% | +0.5970% | −2.9191% |
| **New** hard -2.5% stop | 29/54 (53.7%) | +0.1476% | −0.9148% | +1.2100% | −3.5894% |
| **New** hard -4.0% stop | 31/54 (57.4%) | +0.3487% | −0.4020% | +1.0994% | −4.9613% |
| **New** hard -6.0% stop | 33/54 (61.1%) | +0.4952% | −0.5439% | +1.5342% | −6.5540% |
| **New** +1% profitable-arm, 1.5pp trailing stop | 28/54 (51.9%) | +0.3569% | −0.6000% | +1.3137% | −5.5987% |
| **New** +1% profitable-arm, 2.5pp trailing stop | 33/54 (61.1%) | +0.6856% | −0.4379% | +1.8092% | −5.5987% |

Of the new candidates, the **2.5-point trailing-from-peak after +1% open profit** modestly outperformed unconditional holding across both halves (+0.6856% vs +0.6361% full). But the earlier half remained negative (−0.4379%) and the **−5.6% worst trade** remains. It had only 54 observations, not 80% hit precision, and risk could be much greater under real spreads/gaps. At 60bp illustrative friction, full mean falls to +0.3856%. This is a **candidate for further offline/shadow validation, not deployment**. Tests of new variants were conceived after viewing earlier results; later10 is therefore not a truly blind untouched validation set.

Original comparison generated 54 hypothetical first entries across 20 sessions; the reentry version doubled tickets to 108 and worsened results. Rapid 1-minute exits averaged ~4.65min in position; unconditional holds ~305min. The 20-day sample is too small to support switching production behavior, especially across volatile market regimes.

### Broker-verified Monday 2026-11-09 PAPER order-source review

Read-only inventory snapshot at **20:03:34 UTC (14:03 CST)**, `paper_only=true`, `broker_verified=true`, `recent_orders_complete=true`. **80 filled broker order records** for Nov 9, with clear prefixes:
* **MBB**: 62 orders = 31 buy + 31 sell, 31 symbols, labelled `sector_or_other`.
* **FDR**: 18 orders = 9 buy + 9 sell, 9 symbols, labelled `rebound`.
* **Other IDs**: zero among 80 orders; zero duplicate client-order IDs in this snapshot. Flat positions and no open orders at snapshot time.
* Eight symbols overlapped between the two strategy lists (AMD, AVGO, INTC, MU, NVDA, SNDK, TSM, WDC), but **zero simultaneous holding intervals** from paired filled-order timestamps. AMD had a ~5.5-minute gap between separate strategy exposures. This does not rule out working-order overlap, partial fill activity overlap or writers not represented in the sampled order history.

**Critical count distinction:** Earlier activity audit counted **122 MBB fill activity events + 33 other/unmatched fill activity events**. A single filled order may generate multiple partial FILL activity events; the later 62/18 figures count completed **orders**, not individual activity events. The complete order snapshot provides a plausible source for additional activity events—9 FDR rebound round-trips—but the exact 33 activity IDs have **NOT** been joined to order IDs. Therefore neither 'all 33 are FDR' nor 'unknown third executor' is proven. To close this, perform a read-only activity-to-order UUID join on the broker FILL ledger and compare working orders during overlapping exposure.

### November 9 hypothetical hold stress — not an order recommendation

Earlier read-only matched PAPER filled orders (30 closed MBB lots eligible before 13:40 Chicago):
* Actual matched MBB realized PAPER P&L: **−$129.92** before commissions/data; retrospective hold of same filled entry quantities to SIP 13:40 CT **trade price mark: +$1,697.59 gross**, or +$1,527.12 after a hypothetical 0.30% of exit notional (NOT observed fill costs).
* **13 premarket entries** account for +$1,543.42 of the +$1,697.59 hindsight hold gross. The **17 regular-session entries** accounted for only +$154.18. This premarket concentration makes replacing instant exits with holding especially dangerous without gap/risk controls.
* Nine FDR rebate/rebound filled round-trips separately realized **−$118.22** with +$811.62 hypothetical 13:40 CT gross hold mark. FDR amounts are NOT part of the −$129.92 MBB strategy P&L.
* These numbers **cannot be treated as verified alternative strategy profits**. They omit intraday risk limits, interim drawdowns, adverse bid/ask prices, order fill probability, minimum price/lot constraints and scenario-specific exit rules. Some premarket entries predate regular-session data used for the final mark.

## Immediate conclusions / next tests

1. **Main quality failure:** The one-minute reversal and +/-1% exit strategies lose most of the measured continuation after earlier BUY/SHORT signals; one reentry increases transaction count and loses more. Blindly riding every signal with no stop is not safe either; first 10 days lose money and historical worst trade is material.
2. Risk-aware holding longer with a loose trailing gain-protecting stop deserves expanded >52-week and more frequent regime-shift walk-forward, risk/MAE stress and actual brokerage execution validation, but cannot be adopted now.
3. The FDR order family exists separately from MBB and shares symbols, yet the broker-verified snapshot has no simultaneous filled exposure across the eight overlapping names. Exact source of the **33 other FILL activities** remains unresolved until activity/order UUID join.
4. Continue both-sign daily audits and comparison to V1 actual fills, conditioning on known-at-entry breadth, position sizing, broker session-eligibility and 2pm CT flat. No research module may place orders or modify V1.

## Files/tests

New code: `research/v2_20session_stop_risk_stress.py`, `research/v2_order_source_collision_audit.py`; 12 new targeted unit tests passed. Structured historical summary `research/results/v2_20session_stop_risk_stress_2026-11-09.json`; 378 individual strategy-event rows `research/results/v2_20session_stop_risk_stress_daily_2026-11-09.csv`; sanitized read-only broker attribution `research/results/v2_broker_source_collision_audit_2026-11-09.json`. All committed to **research/rebound-v2-conditional-exits**, and no production or broker resources mutated.
