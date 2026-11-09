# V2 Nov 9 PAPER fill anti-churn and 20-session as-of replay

**Research only. Run date November 9, 2026; America/Chicago. No broker POST/PATCH/DELETE, no modification of V1 PAPER/LIVE, active host services, timers, or existing orders. Validated unpaused holiday cache revision 2, next_check_at November 13, 2026, 16:13 CST (unless calendar edited).**

## New broker read-only reconciliation (November 9)

Source: authorized Alpaca PAPER GET activity/order evidence as independently summarized in `trading-sector-paper-fill-audit.service` journal, plus read-only order-fill-averages from `/var/lib/securityprepper-paper-inventory/current.json`. The inventory had 83 recent orders and no open orders as of 13:38 CT; a 13:43 CT read-only snapshot verified **zero PAPER positions and zero open orders**. The earlier 13:33 CT inventory had 12 open XOM shares, so do not backdate flat verification.

| PAPER order family | FILL activity count | Closed quantity-matched position lots | Actual gross realized | Hypothetical HOLD to 13:40 CT, trade close mark | Hypothetical after 30 basis points |
|---|---:|---:|---:|---:|---:|
| MBB sector | **126** | 30 | **−$129.92** | **+$1,697.59** | **+$1,532.21** |
| FDR five-day rebound | **33** | 9 | **−$118.22** | **+$811.62** | **+$762.24** |
| Combined | 159 | 39 | **−$248.14** | **+$2,509.21** | **+$2,294.45** |

The 33 apparently 'unmatched' FILL activities were conclusively matched to **FDR-prefix orders**, not unexplained broker events: 18 filled FDR orders, 9 symbols. Eight ticker symbols were common between MBB and FDR, but order-average FIFO interval reconstruction found **zero simultaneous same-symbol MBB/FDR holdings**. Both are distinct enabled PAPER order-writing families, so future position/order dedup still must reconcile account-wide. A fill activity is not necessarily an order or a separate round-trip position (partial fills occur).

Counterfactual uses the **completed 14:39–14:40 ET SIP 1Min trade bar close = 13:40 Chicago**, not an executable bid. The 30bp illustration is proportional to the $55,125.87 MBB or $16,458.86 FDR entry notional; actual spreads/commission/slippage are NOT established. The 39 same-sized historical quantities were kept from actual observed entries; unrealized shares held concurrently could violate account exposure caps. **These are not earned PAPER profits and are neither a forecast nor a recommended order.** In particular, 13 early/pre-RTH MBB entries contributed +$1,543.42 of MBB's hold-mark result; 17 RTH entries contributed only +$154.18. Single-day Nov 9 market recovery is not evidence of durable profit.

**Safety/tail:** Under the hypothetical hold, observed subsequent SIP 1Min RTH lows would have produced an intrahold adverse excursion of **−4.48% NVDA for MBB** and **−4.09% NVDA for FDR** versus actual entry. Earlier premarket adverse movements, queue fills, borrow constraints, latency and unverified spreads are not included. A 2.5% owner warning would not necessarily imply an authorized or executable sell.

## Independent 20-market-day causal 1-minute policy comparison

Historical inputs: 20 independent RTH sessions **October 12–November 6, 2026**, full 311 per-day SIP one-minute bars in `/tmp/sector_complete_20session_alpaca_mixed.json` for SOXX/AMD/MU/SNDK; prior FIVE completed RTH closes obtained separately from stored 52-week five-minute SIP. No Nov 9 selection/outcome data. **09:35 ET forecast sees completed 09:34 minute only**: SOXX +/-0.20% from prior regular close with >=2/3 peer stocks confirming in same direction; qualified stocks get a hypothetical 09:35 next-bar-OPEN entry. All triggers use completed bars and hypothetical NEXT-bar-OPEN exit. Latest exit mark **14:40 ET = 13:40 Chicago**. Simple 0.30 percentage-point per trade roundtrip friction proxy. No real broker orders, no actual V1 historical fills for these days, no verified short ability or NBBO.

**Critical data-integrity failure caught and corrected BEFORE validation:** SOXX 1m source prices were ~3× the contemporaneous *split-adjusted* 5m prior-close for **18 of 20 sessions**. An initial run (not valid) interpreted the mismatch as artificial 200% bullish opening momentum and produced invalid trade results/major-down labels. The final committed replay normalizes 3:1 using ONLY the **09:34 completed minute and prior completed adjusted regular close**, requires an as-of ratio in the recognized 2.5–3.5 range (or ordinary 0.65–1.45 ratio), and **fails closed** otherwise. All following figures are corrected. Twelve focused tests pass including as-of cutoff, price normalization, negative controls, next-minute fill price and flat clock.

| Fixed hypothetical exit rule | Trades | Profitable after 30bp | Avg return after 30bp per trade | First ten market days | Last ten market days |
|---|---:|---:|---:|---:|---:|
| Hold until 13:40 CT | 54 | **33/54 = 61.1%** | **+0.636%** | **−0.465%** | **+1.737%** |
| Tight opposite-sector/stock 1m reversal | 54 | 14/54 = 25.9% | **−0.284%** | −0.751% | +0.182% |
| Close-based ±1% target/stop, next-bar exit | 54 | 24/54 = 44.4% | **−0.435%** | −0.816% | −0.055% |
| 5m sector-confirmed adverse trend/2.5% emergency | 54 | 17/54 = 31.5% | **−0.442%** | −0.993% | +0.110% |
| Tight 1m exit with one allowed reentry (15m cooldown + as-of breadth) | **108** | **25/108 = 23.1%** | **−0.350%** | −0.579% | −0.122% |

There were **18 forecast/traded days out of 20** and **54 initial stock candidates**: 21 bullish and 33 hypothetical bearish, three correlated stocks per active session. No reentry variant multiplied positions concurrently. Historical return means are trade-equal and do not model portfolio exposure. Earlier versus later comparisons are chronological **stress splits, not a locked optimized policy or truly blind backtest**; all thresholds were prespecified exploratory variants. In particular, the early negative half and large later positive half mean *holding until 13:40 is not established as a reliable strategy*.

### Every-day major up/down audit
Across 60 AMD/MU/SNDK stock-days, the complete-day retrospective labels (>=5% in either prior-close-to-close or RTH open-to-close) identified **8 major upside days and 22 major downside days**. The 09:35 as-of broad-sector direction plus stock-qualification rule pointed correctly on **23/30 major stock-days** and missed **7/30**. The 54 initial entries include 31 without a same-direction >=5% realized stock-day label; these are not automatically unprofitable trades. SOXX itself had 3 >=5% major-down dates (0 major-up) and all 3 were directionally flagged at 09:35. The three AMD/MU/SNDK severe downside days on **November 2, 2026** were **not** flagged by this 09:35 rule (ABSTAIN), proving meaningful crash protection missing from a profitable continuation model. Other misses: SNDK UP Oct 13, MU and SNDK UP Oct 15, SNDK DOWN Nov 6. Latest 20-session daily audit is in `research/results/v2_20session_major_outcomes_2026-11-09.csv`.

## Decision / blockers
* **No V2 PAPER GO** and no V1 alteration: Nov 9 strongly suggests premature exits on that specific rally day, but a 20-day stop-vs-hold stress has only 18 traded days, a severe early/later regime split, correlated names, unverified short execution and bid/ask costs. One reentry increased churn and reduced after-cost precision.
* Do **not** confuse 13:40 ET with the owner's 13:40 **Chicago** risk-management start. The existing time-exit starts 13:40 Chicago and the latest flat target remains 14:00 Chicago.
* To reproduce historical V1-specific exit gains, require multiple dates of broker-observed PAPER fill timestamps, original rule/version decision logs and actual contemporaneous SIP/BOATS executable quotes; one Nov 9 slice cannot measure historical V1 performance. Maintain safe exposure/stop caps and do not place research orders.
* Other sectors and futures/news remain separate tracks; don't extrapolate four semiconductor symbols to all sectors.

## Artifacts (research branch `research/rebound-v2-conditional-exits`)
* `research/v2_20session_anti_churn_replay.py`
* `research/test_v2_20session_anti_churn_replay.py` (12 tests passed)
* `research/v2_20session_major_outcomes.py`
* `research/results/v2_20session_anti_churn_summary_2026-11-09.json`
* `research/results/v2_20session_anti_churn_daily_2026-11-09.csv`
* `research/results/v2_20session_major_outcomes_2026-11-09.csv`
* `research/v2_nov9_broker_hold_1340CT_readonly.py` (requires authorized host's read-only inventory snapshot; no broker order actions). Detailed client order IDs, broker account identifiers and secret material NOT committed.
