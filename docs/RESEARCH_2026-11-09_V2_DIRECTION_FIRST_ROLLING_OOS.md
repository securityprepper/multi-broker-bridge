# V2 — Direction-first, causal sector forecasts and serious-move diagnostic
**Run:** November 9, 2026, approximately 12:32–12:45 CST. **Branch:** `research/rebound-v2-conditional-exits`. **RESEARCH ONLY**; no V1, PAPER, LIVE, order, gateway, task schedule, or production checkout changes.

## Clarified objective

The owner's **80%** target is the fraction of correct **sector UP/DOWN calls by that day's close**, not the percentage of trades that finish profitable. Primary outcome: ETF close relative to **previous completed regular-session close**, with `NEUTRAL` ±0.15% and explicit `ABSTAIN`. Evaluate opening-to-close separately. To avoid gaming accuracy through abstentions, count coverage and both UP and DOWN precision. Every issued call is timestamped before the close, but a later correct forecast is **not** a successful premarket forecast. A correct sector direction does **not** guarantee a remaining after-cost trading opportunity.

## Data, causality and thresholds

Seven independent 52-week Alpaca split-adjusted **SIP 5-minute trade bar** cohorts: semiconductors SOXX/AMD/MU, gold miners GDX/NEM/AEM, energy XLE/XOM/CVX, financials XLF/JPM/BAC, industrials XLI/CAT/GE, healthcare XLV/UNH/LLY and software IGV/MSFT/CRM. Each has 248 complete shared regular sessions with strictly five previous completed sessions for as-of calculations; partial/short sessions and missing checkpoints are excluded, creating a potential historical data-availability bias. These are not full SIP/BOATS NBBO, executable quotes, completed one-minute replay, futures, or timestamped earnings/news.

The outcome is computed **after** the checkpoint. A bar timestamp is its **start**: the last bar in a 09:25 ET forecast starts 09:20; no 09:25 or later bar, later close, or subsequent news is used in features. Candidate thresholds 0.10/0.25/0.50/1.0% with ETF momentum and one/two-peer breadth, recent 15m continuation, previous five-day direction and opening continuation are scored independently at preceding evening, 08:30, 09:25, 10:00, 11:00, 13:00 ET. No qualified preceding-evening rule emerged.

Two chronology checks: (1) select a frozen rule using **only dates before 2026-09-01**, then evaluate September–November; (2) monthly walk-forward April–November, reselect each calendar month using ONLY earlier trading days and issue its earliest qualified forecast. No retroactive revisions. Missing/no reliable signals are ABSTAIN.

### Outcomes (monthly rolling April–November 2026)

| Sector | Correct UP/DOWN | Accuracy on calls | Coverage | UP precision | DOWN precision |
|---|---:|---:|---:|---:|---:|
| Semiconductors | 130/153 | 84.97% | 100.0% | 90.9% | 76.9% |
| Gold miners | 130/150 | 86.67% | 98.0% | 85.7% | 87.5% |
| Energy | 118/150 | 78.67% | 98.0% | 81.4% | 75.0% |
| Financials | 116/141 | 82.27% | 92.2% | 83.5% | 80.6% |
| Industrials | 121/152 | 79.61% | 99.3% | 78.5% | 80.8% |
| Healthcare | 119/150 | 79.33% | 98.0% | 81.3% | 77.3% |
| Software | 123/153 | 80.39% | 100.0% | 79.7% | 81.1% |

**Crucial timing:** Semiconductors' 153 first forecasts included only **5 before 09:30 ET**; 136 were at 10:00 and 12 at 11:00. For gold miners, 47 were premarket (7 at 08:30, 40 at 09:25); 67 were at 10:00, 30 at 11:00, and 6 at 13:00. Thus 85% sector sign accuracy is NOT an 85% preceding-evening or premarket crash predictor. Month-level rates vary substantially; policies were adjusted only using earlier data, but the sample is still limited and subject to selection/survivorship and market-regime shift. Rolling Wilson 95% lower bound for semiconductors was 78.45%; gold miners 80.30%. Trading-day serial dependence is not incorporated in Wilson intervals.

The separate **pre-September frozen → September–November holdout** found semis 42/48 (87.5%) at 10:00, gold miners 39/44 (88.6%) at 10:00; financials 38/44 first qualified calls (86.4%), software 39/48 (81.25%). Sector directions are more predictable during the session after movement has become visible. But in the holdout, only **22/48 semis** and **28/47 gold miner** first directional calls were followed by further same-direction ETF movement through that close; mean gross remaining direction-aligned change just +0.136% semis and +0.095% gold miners. These are price marks, NOT after-fee executable trades.

### Session counts (the NEW three-instrument unanimous regime definition)

| Sector | All 3 up | All 3 down | Mixed |
|---|---:|---:|---:|
| Semis | 91 | 74 | 83 |
| Gold miners | 114 | 95 | 39 |
| Energy | 114 | 86 | 48 |
| Financials | 102 | 80 | 66 |
| Industrials | 84 | 71 | 93 |
| Healthcare | 55 | 71 | 122 |
| Software | 73 | 82 | 93 |

**Do not confuse the definitions:** Earlier semis 118/83/49 used SOXX plus a broader peer-majority convention, and earlier gold miners 132/114/6 used GDX plus a different majority rule. The direction forecast labels above are ETF UP/DOWN/NEUTRAL, not unanimous sector-regime labels.

### Large-move sensitivity and emergency false alarms

Rolling first-forecast OOS emergency candidates use current observed same-direction ETF move >= 0.5 × strictly prior-five volatility-derived significance level; historical significant-day labels use >= max(1%,1.5 × mean of previous four completed close-to-close absolute returns) for these regimes. **These are exploratory alert candidates, NOT orders.**

- **Semis:** 40 correctly flagged significant-direction days, **36 false emergency warnings**, 26 qualifying warnings only after the ETF had *already* exceeded its major-move level. 46/46 significant days had first directional sign correct, but this is not a timely emergency-protection result. The selected monthly rule's first true serious warning was **April 8, 2026, at 10:00 ET**.
- **Gold miners:** 36 true significant warnings versus **47 false emergency warnings**; 26 only after severity already reached; 40/41 significant days got first direction correct. First true warning April 8, 2026, at 11:00 ET. These warnings are far too imprecise to generate automatic orders.
- **Full 248-day semis strict >=5% prior-close or open-to-close stress:** 14 large-up and 14 large-down ETF sessions; earliest frozen-policy correct severe-UP signal **February 6, 2026, 10:00 ET**, severe-DOWN **March 30, 2026, 10:00 ET**; 13/14 up and 12/14 down first-sign forecasts correct; three missed/wrong severe cases: **November 20, 2025** (SOXX RTH −7.22% while initial direction UP), **March 9, 2026** (RTH +5.68%, initial DOWN), **July 2, 2026** (−5.43% close-to-close, initial UP). There were **zero** true preceding-evening or premarket warnings from the frozen qualified semis policy. Ten true severe cases were already at or beyond ±5% when first signaled. No automatic SELL/BUY GO.
- **Full gold miner severe-move diagnostic:** 33 significant up and 37 significant down sessions by prior-five regime, with first correct direction for 32/33 and 32/37 respectively. Earliest correct big-UP **November 10, 2025, 08:30 ET**, big-DOWN **December 8, 2025, 10:00 ET**; **46 major-direction first signals premarket** but **zero preceding evening**, and 32 correct significant alerts issued only after severity already crossed. Major-direction misses include 2025-11-20, 2026-01-21, 2026-01-29, 2026-02-26, 2026-08-28, and 2026-09-16.

**November 2 semiconductor warning failure:** At 10:00 ET the frozen SOXX ETF-only forecast was UP on an observed +0.108% previous-close change, while the ETF finished **−3.804%**. Several individual chip stocks lost >5%. Sector-direction confidence alone would have misled a hypothetical bullish entry; retain individual-stock/peer emergency observation separately and acquire genuine earlier futures/news. The historical data ends November 6: **November 9 cannot be scored as a completed day at this run's 12:32 CST start.**

### Overnight hold vs hypothetical emergency sales

For first OOS **DOWN** sector calls (including false alarms), selling at the forecast's 5m trade price minus 30bp, versus holding until the next regular open, had average modeled advantage **+0.302 percentage points on semis** (beneficial in only 10/23 cases) and **−0.557 points on gold miners** (beneficial in only 8/26). These are not executable quotes and not matched to V1 inventory, bid/ask spreads, partial fills, broker-native stops or the protected active order ledger. Conditional results restricted to *later-known* true large down days are hindsight diagnostics, never usable as earlier trade triggers.

## Research-only next actions and GO boundary

Direction detection at 10:00 is promising for semis, miners, and financials, but **BEARISH semis precision is <80%; previous-evening/preopen semiconductor forecasts do not qualify; emergency true/false rates are unacceptable for orders.** Continue rolling direction calibration with causal QQQ/SOXX peer breadth, 1m movements, futures, earnings/guidance, economic calendar and point-in-time company/sector news. Test earlier direction confidence and post-signal continuation separately, including whether a later reversal should retract an alert without spamming the user.

Existing V1 PAPER/LIVE monitors and broker orders must not change. Any PAPER emergency workflow (opposing-position broker readback and close before opening new sector exposure) requires a distinct reviewed PAPER-only commission and dedicated execution permissions; this research task issues **NO broker orders**. No 80%-accurate emergency executor is approved. Preserve the validated America/Chicago unpaused holiday cache revision 2 only strictly before November 13, 2026, 16:13 CST absent invalidation; no schedule changes. Historical executable NBBO/BOATS bid/ask, synchronized one-minute, futures/news and matched V1 order fills remain precise blockers.

## Reproduce
```sh
python3 -m unittest discover -s research -p 'test_v2_direction_*20261109.py' -v
python3 research/v2_direction_walkforward_20261109.py --output /tmp/v2-direction-summary.json --audit /tmp/v2-direction-holdout.json
python3 research/v2_direction_followthrough_20261109.py --summary /tmp/v2-direction-summary.json --audit /tmp/v2-direction-holdout.json --output /tmp/v2-direction-followthrough.json
python3 research/v2_direction_full_history_20261109.py --summary /tmp/v2-direction-summary.json --output /tmp/v2-direction-all-days.json
python3 research/v2_direction_monthly_walkforward_20261109.py --output /tmp/v2-direction-monthly.json
```
Inputs are the read-only split-adjusted local 52-week Alpaca SIP datasets at www3 paths defined in the scripts. **41 targeted offline unit tests passed** in an isolated /tmp/v2-run19-direction-only workspace; no active source, timers or order systems were modified.
