# V2 November 9 late-evening: post-signal early-sector predictive precision and anti-churn risk

**Research only. Separate branch `research/rebound-v2-conditional-exits`. NO broker orders, PAPER/LIVE strategy/timer edits, or new predictive Pushover.**

## Research question

The earlier user-authorized 5%/7% extreme-sector alert configuration did reduce *observed* price-event frequency, but only 3 of 26 qualified events preceded another +0.5% same-direction ETF move within the following 60 minutes. Merely observing a prior move creates high false predictive alerts.

This pass evaluated WHETHER an EARLIER 09:35 / 09:45 / 10:05 Eastern Time completed-five-minute sector and peer breadth signal could predict a profitable *future* move, evaluated only AFTER delayed execution. Historical source: 52-week Alpaca split-adjusted five-minute SIP trade bars for SOXX+AMD/MU/NVDA, GDX+NEM/AEM/KGC, XLE+XOM/CVX, XLF+JPM/BAC, XLI+CAT/GE, XLV+UNH/LLY and IGV+MSFT/CRM, through November 6, 2026. Strictly require five PRECEDING fully completed regular-session dates per symbol. Nov9 (known high-up day) was never used as a label in this study.

A signal at 09:35 ET uses the 09:30–09:35 completed bar, can enter only at the 09:40 ET bar-open *price proxy*. Similarly 09:45 -> 09:50, 10:05 -> 10:10. Event qualification is as-of sector ETF open-to-current return, two/three corroborating peers, recent completed-five-minute price momentum, and a cap on already-extended ETF movement. The 60-minute mark is a LATER completed bar and MUST NOT be used to select an earlier event. Horizon to time-flat 14:40 ET = **13:40 America/Chicago** (20m before existing latest-flat 2pm CT) is separately analyzed. Short scenarios assume executable borrow, which remains unverified.

## Selection and forward result

For EACH sector independently, test an earlier-training-only grid of 180 (sectors with 2 peers) or 360 (3 peers) combinations of:
- positive / negative direction
- sector positive signed move >=0.15%, 0.30%, 0.50%, 0.75%, 1.0%
- correlated peer move >=0%, 0.20%, 0.40%; breadth 2/3 or 3/3 when available, both peers for two-peer sectors
- 5m continuation filter none, >=0 or >=0.10%
- no-chase guard prior observed sector rise/fall <=1.5% or <=3%.
- First qualified signal per sector-date only.

Total **1,620** candidate configurations; 250 eligible dates per sector, first 175 for training, later 75 for comparison (later segment starts July 24 2026). Only candidates with >=18 earlier independent signals AND >=8% earlier-date coverage can be selected. Training qualification for *predictive reporting* requires >=65% hypothetical after-30bp profitable **60-minute returns** AND positive mean. **Zero candidates across all seven sectors qualified**. Any "best" row below is a SHADOW POLICY chosen for comparison, not a recommendation, proof of 80% precision, or new alert.

| Sector | Best earlier-selected direction | Later after-30bp profitable / signals | Later mean 60m post-entry return | Later mean through 13:40 CT |
|---|---|---:|---:|---:|
| Semiconductors | DOWN | **6/9 = 66.7%** | **+0.8568%** | +0.9698% |
| Gold miners | DOWN | 8/21 = 38.1% | −0.2968% | −0.5245% |
| Energy | UP | 5/15 = 33.3% | −0.2926% | −0.2514% |
| Financials | UP | 4/15 = 26.7% | −0.2581% | −0.3519% |
| Industrials | UP | 2/15 = 13.3% | −0.5381% | −0.7843% |
| Healthcare | UP | 6/16 = 37.5% | −0.0813% | +0.0316% |
| Software | DOWN | 3/7 = 42.9% | −0.3424% | −0.0530% |

The **semiconductor bearish shadow** required SOXX down >=0.75% from the SAME DAY 09:30 open, each AMD/MU/NVDA down >=0.20%, and SOXX still declining >=0.10% in the latest completed five minutes; it rejected sectors already down >1.5%. Across the earlier 175 days: 11/18 trades won after 30bp (61.1%; +0.2184% average 60m). Across the later 75 days: 6/9 won (66.7%; +0.8568% average). **Only 9/75 later days issued a signal.** Approximate Wilson 95% lower bound for 6/9 is **35.4%**, nowhere near an independently reliable 80% target. One Nov5 2026 winning trade contributed +3.68%; removing it leaves mean +0.50%. No new PAPER short or inverse ETF order is authorized.

For context, blindly shorting SOXX at 09:50 ET on every eligible later date instead of requiring the selected breadth signal: **24/75 after-30bp winners (32.0%), mean −0.1407%**. That suggests selectivity may help, but the small sample and extensive repeated search demand sealed prospective testing and borrow/ETF execution checks.

## Protected next-bar 5m stop vs no-stop sensitivity

A separate offline replay considered fully completed five-minute CLOSE stops at −1.5%, −2.5% or −4% from the delayed-entry ETF proxy. Stop decision uses only the completed candle, and hypothetical exit is at the NEXT five-minute bar OPEN; no same-bar fill, no access to actual NBBO, spreads, borrow or partial-fill handling. Record MAE/MFE using intervening five-minute OHLC strictly as *outcomes*, never predictive input. Otherwise hold to 14:40 ET bar close.

- Semiconductor selected bearish earlier period (18 trades): 1.5% stop triggered 6 times and **reduced** mean after-30bp hold from +0.2146% to +0.038%; 2.5% triggered 4 times and changed mean to +0.234%; 4% triggered once. Later 9 trades: no 1.5/2.5/4% stops triggered, so stopping had no demonstrated effect. Later worst OHLC adverse excursion was ~−1.76% and worst after-30bp hold −1.34%, not guarantees for future losses.
- Gold miners later 21 shadow shorts: 2.5% triggered once; mean −0.522% versus −0.5245% no-stop. The much tighter 1.5% triggered six times and mean remained −0.505%. Neither is profitable.
- Other sectors mostly suffered negative returns irrespective of these fixed-percent stop choices; favorable stops in one regime did not establish a stable benefit. Overnight stop behavior and any hypothetical live broker fills were not tested.

**No deployment GO.** The correct result is an early-bearish semiconductor WATCH candidate for sealed forward shadow logging, not an actionable purchase/short/emergency auto-exit. Avoid a rapid 1m kneejerk liquidation without examining breadth/volatility, but do NOT remove the independent protective-loss hard gate. Existing 2pm Chicago latest-flat objective remains.

## Artifacts / reproducibility
- `research/v2_next_move_first_7sector_walkforward_20261109.py` — input parsing, causally completed 5m signals and delayed entry with outcomes after signal; training grid.
- `research/test_v2_next_move_first_7sector_walkforward_20261109.py` — 8 synthetic time/peer/future-censor tests.
- `research/v2_nextbar_stop_risk_20261109.py` — no-lookahead next-bar hard-stop counterfactual and MAE outcome.
- `research/test_v2_nextbar_stop_risk_20261109.py` — 6 synthetic stop/delay tests.
- `research/results/v2_next_move_first_seven_sector_walkforward_2026-11-09.json` — per-sector training, later events, policy and no-signal counts.
- `research/results/v2_nextbar_stop_risk_2026-11-09.json` — 1.5/2.5/4% stop vs 13:40 CT hold on matched selected events.
- `research/results/v2_early_entry_unconditional_baselines_2026-11-09.json` — always-same-direction at 09:45 baseline, later sample.
- **All 14 new offline synthetic tests PASSED** on isolated /tmp/v2-next-move-walkforward.

## Exact blockers and next work
- Selected historical dataset has been used in prior research, so the later period is chronologically separated but **not genuinely blind**. Commit a sealed timestamped live-forward shadow observation stream *before* scoring outcomes; don't tune on the later months.
- No complete historical executable SIP/BOATS bid/ask NBBO, queue/partial fills, broker-observed V1 matched fills, short eligibility or realized fee/slippage matching this backtest. All 30bp returns are hypothetical round-trip friction, not real profits.
- Missing synchronized prior-evening futures, market-wide breadth and point-in-time earnings/guidance/news coverage prevent high-confidence early overnight direction attribution. The independent minute news observer is READ-ONLY; source categories are NOT verified trading signals.
- The official quiet V2 thresholds remain SOXX day5%/night5.5%; GDX 5%/7%; energy3%/3.5%; XLF/XLI/XLV3%/3%; IGV4%/4%. They are **observed extreme research-only** and must not be bypassed by this exploratory 0.75% semis bearish candidate. Critical operational/broker/position warnings remain separate and preserved.
- Holiday cached unpaused revision2 until Nov13 2026 16:13 Chicago absent calendar edits. Do not alter any V1 PAPER/LIVE monitor, broker order, risk/exit gate or schedule.

**Next meaningful milestone: prospectively seal fresh 09:35/09:45 and 10:05 five-minute signals before outcome, then validate at least 30 genuine independent days for both sides.** Current result is research only.
