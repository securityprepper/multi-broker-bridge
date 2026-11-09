# V2 Seven-Sector 10:05-to-13:30 Replay — November 9, 2026

**RESEARCH ONLY — NO BROKER CONNECTION, NO ORDER SUBMISSION, NO V1 / LIVE CHANGES**

## Question and market time convention
How much did each of seven sector ETFs move after the **10:05 a.m. Eastern Time** observation, through **1:30 p.m. Eastern Time**, on each of the available days, including days without a forecast?

The 10:00–10:05 ET **completed five-minute bar CLOSE** is observable no sooner than 10:05. The 13:25–13:30 ET bar close is the end mark, observable no sooner than 13:30. Return = `100*(13:30 mark / 10:05 mark - 1)`. Bullish signed return = raw ETF return; bearish signed return = NEGATIVE raw ETF return (hypothetical short ETF, not evidence that shorting was possible or profitable). No-signal days are in the complete daily audit and coverage denominator; no position is simulated for them. Daily direction is scored separately using prior regular close versus final regular close. All observations came from split-adjusted Alpaca SIP five-minute trade bars, not executable NBBO. Period approximately Nov 2025–Nov 6, 2026.

The 10:05 rules were selected in earlier research using only the earlier ~70% of dates. This run applies those frozen rules to all 252–254 usable dates, including the later ~30%. These dates and related rules have been repeatedly studied across prior research; **this is not fresh external/prospective validation**.

## Full 52-week sector forecast and 10:05–13:30 results

| Sector ETF | Usable days | Forecasts UP/DOWN | Correct full-day direction | UP signed sum (pp) | DOWN signed sum (pp) | Gross sum (pp) | Gross mean per forecast | Gross compounded* | Sum after hypothetical 0.30 pp per signal |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SOXX semiconductors | 252 | 93 / 70 | 150/163 = 92.0% | +4.487 | +14.095 | **+18.582** | +0.114% | +17.938% | **−30.318 pp** |
| GDX gold miners | 254 | 68 / 65 | 126/133 = 94.7% | −3.847 | +8.188 | **+4.340** | +0.033% | +3.057% | **−35.560 pp** |
| XLE energy | 252 | 48 / 33 | 75/81 = 92.6% | +0.755 | −4.319 | **−3.565** | −0.044% | −3.746% | **−27.865 pp** |
| XLF financials | 252 | 47 / 27 | 65/74 = 87.8% | −7.783 | −1.871 | **−9.654** | −0.130% | −9.331% | **−31.854 pp** |
| XLI industrials | 252 | 45 / 41 | 79/86 = 91.9% | −3.692 | +3.516 | **−0.176** | −0.002% | −0.416% | **−25.976 pp** |
| XLV healthcare | 252 | 51 / 31 | 74/82 = 90.2% | −5.473 | −1.724 | **−7.198** | −0.088% | −7.078% | **−31.798 pp** |
| IGV software | 252 | 45 / 50 | 86/95 = 90.5% | −0.988 | −0.108 | **−1.096** | −0.012% | −1.705% | **−29.596 pp** |

**pp means a sum of individual daily percentage returns in percentage points, not a single-account P&L percentage.** If the same fixed notional were hypothetically deployed on each signal, mean return per forecast is the relevant simple average. *Compounded assumes 100% of capital reallocated sequentially to each signal and reinvested; it is purely illustrative and ignores borrow, margin, orders, market impact and broker constraints.* Cost sensitivity deducts 0.30 percentage points per forecast, an illustrative round-trip friction assumption, NOT measured fills or actual commission accounting. The gap between gross direction accuracy and the 10:05–13:30 return demonstrates that much of the day's move is already over at signal time.

## Later 30% of usable dates, unchanged thresholds

| Sector | Later forecast days | Full-day direction accuracy | Gross signed 10:05–13:30 sum (pp) | After 0.30 pp/signal (pp) |
|---|---:|---:|---:|---:|
| Semiconductors | 53 / 76 | 49/53 = 92.45% | +9.330 | −6.570 |
| Gold miners | 45 / 77 | 45/45 = 100% | −0.622 | −14.122 |
| Energy | 29 / 76 | 27/29 = 93.10% | −0.654 | −9.354 |
| Financials | 19 / 76 | 19/19 = 100% | −3.368 | −9.068 |
| Industrials | 28 / 76 | 25/28 = 89.29% | +0.526 | −7.874 |
| Healthcare | 23 / 76 | 22/23 = 95.65% | −5.307 | −12.207 |
| Software | 27 / 76 | 26/27 = 96.30% | +3.662 | −4.438 |

These differ slightly from the previous report's 75-day holdout because this replay requires exact completed 10:00 and 13:25 bars and uses all qualifying days, independently of availability of the previous 14:00 execution reference.

## Test/data controls
1. Signals use only previous completed close and market bars with start <=10:00 ET, ending by 10:05 ET; gold miner spot/peer confirmations use the same local 10:00 candle. Future 13:25/15:55 data are only outcomes.
2. Read-only analysis in `research/v2_seven_sector_1005_1330_replay.py`; production checkout, broker APIs, current V1 and order safety gates never touched. 1,766 daily sector observations covered. Seven sector consistency checks verified unique date, positive 10:05/13:30 marks, and recomputed raw/signed returns (within source rounding).
3. The result is sector direction from prior close, not probability of an additional significant move after 10:05. Precision on significant emergency moves and trade entry/exits remain separate.
4. Missing or stale intra-session bars should cause abstention in a live implementation. For this replay only exact relevant completed bars are used; sessions failing data prerequisites are excluded, potentially biasing accuracy if data gaps are nonrandom.
5. The models used some later historical dates in prior experimentation, so the holdout should be regarded as retrospectively frozen rather than a truly blind test. A forward-only sealed, timestamped audit is still required before any PAPER emergency automation.

## Artifacts
* Full 1,766 daily outcomes: `research/results/v2_seven_sector_1005_to_1330_daily_2026-11-09.csv`. Includes forecast side, daily final actual UP/DOWN, exact 10:05 and 13:30 price marks, raw and signed move and full-day return, including ABSTAIN dates.
* Summary: `research/results/v2_seven_sector_1005_to_1330_2026-11-09.json`.
* Original read-only results on www3: `/tmp/v2-direction-1005-to-1330-20261109.json`.
* A production-like fill simulation would require historical executable SIP/BOATS bid/ask, order book, borrow/short eligibility, commissions and broker readback; none were established here.

**Decision:** DO NOT activate new buy/sell orders based on these sector-direction observations alone. Improve early directional forecast and forecast of remaining 10:05-to-13:30 movement, validate forward-only, and score emergency alerts separately.
