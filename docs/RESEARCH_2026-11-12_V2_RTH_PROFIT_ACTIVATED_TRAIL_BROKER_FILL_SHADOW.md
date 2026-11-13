# November 12, 2026 — Four-session Alpaca PAPER RTH trailing-exit shadow (no trading change)

## Outcome

**NO GO** for changing the active PAPER profit target or trailing-reversal threshold. The user-authorized research continued with a source-only V2 simulator, 13 passing offline regression tests, and separately collected read-only Alpaca PAPER broker fills and licensed one-minute SIP historical bars. The currently installed RTH PAPER rule remained **+1% profit close; −1% loss close; +0.5% peak activation and −0.5% retracement; no independent two-falling-bars exit; forced 13:40 CT flat**. No broker orders, live/LIVE changes, host active executors, timers, or existing safety gates were modified.

The most important structural result: with the immediate **+1% profit exit still in place**, replacing the trailing rule with **arm at +1%, allow 1% or 1.5% peak retracement** gave **identical decisions and P/L** to removing trailing entirely on this 31-trade sample. The profit exit normally acts first. To test genuinely riding gains, the hypothetical policies must explicitly **change or suppress** the immediate +1% exit; such changes are **RESEARCH ONLY**, not approved PAPER changes.

## Exact coverage and inclusion

- One previously authenticated Alpaca PAPER broker order exporter; **account identifier is absent**, so this does not prove account-wide completeness across unknown Alpaca accounts. Sources: broker-paired trades and original filled quantities/timestamps, 60 completed positions dated Nov 9–11 plus 2 Nov 12 = **62**, of which **53 MBB** and **9 FDR**. Partial fill activities were not treated as distinct positions. One post-change date (Nov 12) is genuinely later than prior rule-fix testing; other dates have already been researched repeatedly.
- Only **40 MBB entries placed during regular hours between 08:30 and 13:15 Chicago** are comparable to the RTH `trend.py` decision order; **13 MBB premarket entries and 9 FDR premarket entries were excluded**, not assumed losses or wins.
- Only **31/40** RTH entries had a complete, continuous **post-entry one-minute SIP path through 13:40 CT** and usable scenario exit marks under all policies. **9/40 were censored** for minute gaps. Equal-sample actual broker-filled gross P/L was **−$18.18** on those 31 trades. Because 2026-11-09/10/11 live code and broker circumstances differed, actual gross P/L is **not** an A/B treatment estimate.
- Date distribution of the **31** common results: Nov 9 **16**, Nov 10 **8**, Nov 11 **6**, Nov 12 **1**. Nov 12 other verified trade VRNS had **30 missing minutes**, and is censored in the matched exit replay; its actual broker fill remains valid.
- Original BUYs are `NEWS_UNKNOWN` and are **historical controls only**, not cleared new BUY candidates or automatically executable recommendations. No connected broker order tool was invoked.

## Causal, conservative but non-executable simulation

1. Use original broker FILLED BUY price and quantity as the baseline. Skip the BUY-containing one-minute bar; each subsequent completed bar is first observable only after its minute closes. Before every decision, maintain the running high through **already completed** bars. No future bar enters signal or trailing-peak construction.
2. Model the actual order of RTH software signals: **loss if completed close ≤−1%**, then **profit if completed close ≥the selected target**, then **peak-trailing** if armed; otherwise keep holding. The already-disabled two-down-bars exit is never reintroduced. These are close-based SOFTWARE signals, not standing native orders, and no intraminute high is used to assert a fill.
3. For hypothetical exits use the **next one-minute OPEN trade mark** (not guaranteed marketable bid, order acceptance or a fill). If still holding at 13:40, require the historical fresh/tight size-qualified SIP **displayed bid** at that fixed time. No quote means UNKNOWN; the 31 common trades require all variants to be evaluable. Subtract **illustrative** 30 or 60 basis points of entry notional for friction. These proxies are NOT actual net P/L.
4. Maximum favorable/adverse excursions are censored at the hypothetical exit decision, never computed from later prices. The reported modeled realized-P/L drawdown is based on chronological completed *scenario* trades, not continuously marked portfolio equity or true account drawdown.
5. Existing receiving-broker protective stops, premarket emergency policy, prior-five context, negative-news eligibility veto, cash/positions/open-order and holiday protections remain separate and untouched.

## Comparable results — same 31 RTH broker entries / 4 dates

| Research-only RTH signal / trailing policy | Wins after 30bp | 30bp illustrative total | 60bp illustrative total | Mean holding minutes | Worst 30bp trade | Max modeled realized drawdown |
|---|---:|---:|---:|---:|---:|---:|
| **Existing**: +1% profit; 0.5% armed/0.5% retrace | 17/31 | **−$47.53** | −$225.77 | 78.55 | −$28.84 | $163.47 |
| +1% profit; 1% armed/1% retrace | 17/31 | −$51.71 | −$229.95 | 93.90 | −$28.84 | $194.35 |
| +1% profit; 1% armed/1.5% retrace | 17/31 | −$51.71 | −$229.95 | 93.90 | −$28.84 | $194.35 |
| +1% profit; **no trailing** | 17/31 | −$51.71 | −$229.95 | 93.90 | −$28.84 | $194.35 |
| +1.5% profit; 1% armed/1% retrace | 15/31 | −$22.40 | −$200.64 | 108.61 | −$28.84 | $217.03 |
| +1.5% profit; 1% armed/1.5% retrace | 16/31 | −$11.89 | −$190.13 | 109.45 | −$28.84 | $206.52 |
| **No immediate target**; 1% armed/1% retrace | 15/31 | −$23.62 | −$201.86 | 135.64 | −$28.84 | $215.16 |
| **No immediate target**; 1% armed/1.5% retrace | 15/31 | **−$5.99** | −$184.23 | 145.16 | −$28.84 | $139.01 |

All modeled 30bp and 60bp totals remain **negative**. The absence of an immediate profit exit adds considerable exposure time and can allow a previous favorable move to reverse. It is not a GO signal. The 1.5%-target policy gives fewer 30bp wins and a larger modeled drawdown than existing. All strategies preserve the −1% completed-close loss signal and the 13:40 CT flat; neither guarantees a realized −1% loss cap.

### Per-day stability of existing vs no-immediate-target/1.5%-wide trail

| Date | Common trades | Existing after assumed 30bp | No immediate target / trail 1.5% after assumed 30bp |
|---|---:|---:|---:|
| Nov 9 | 16 | −$76.04 | −$47.94 |
| Nov 10 | 8 | −$38.64 | −$42.35 |
| Nov 11 | 6 | +$66.57 | +$50.40 |
| Nov 12 | 1 | +$0.58 | +$33.90 |

This alternative is **worse on Nov 10 and 11**; apparent improvement is concentrated in Nov 9 and one particularly favorable Nov 12 trade. Nov 9 was researched before policy specification, so none of these rows is untouched independent holdout evidence. No policy is selected.

### First prospective observation, OXY (Nov 12)

OXY actual Alpaca PAPER BUY **34 shares at $57.64, 08:48:53 CT**, limit SELL **34 at $57.81, 09:33:50 CT** for **+$5.78 broker-filled gross**. The exact MBB order-intent reason was `trailing peak reversal`, corroborated by broker FILLED status, not merely order acceptance. The complete post-entry SIP minute path until 13:40 had no -1% entry-based low touch; minimum was about **−0.295%**.

- The historical causal current-rule *next-minute-open proxy* exits about 09:33 CT (gross **+$6.46**, **+$0.58** after illustrative 30bp), close to—but not identical with—the broker fill.
- Suppressing sub-1% trailing while preserving +1% profit exit causes a 10:12 CT hypothetical profit exit (gross **+$20.40**, **+$14.52** after 30bp).
- Disabling the +1% immediate exit and using 1%-activated, 1.5%-wide trail reaches 13:40 CT and the contemporaneous indicative bid of $58.81 (gross **+$39.78**, **+$33.90** after 30bp). This is **not a promised fill** or a recommended change.
- VRNS actually exited at 13:40 CT for +$1.20 gross but is not complete-path evaluable.

## Evidence and reproducibility

Published isolated **V2 branch** `research/rebound-v2-conditional-exits`: `research/v2_paper_rth_trail_shadow_20261112.py`, `tests/test_v2_paper_rth_trail_shadow_20261112.py`, and sanitized `research/results/v2_paper_rth_trail_shadow_20261112.json`. **13 tests passed** on authorized www3 isolated scratch, including exit precedence, causal completed bar/next-minute latency, drawdown excursion censoring, −1% loss priority, missing-bar exclusion, scope and duplicate order ID rejection, and no trading operations.

Reproduce by passing two previously authorized, securely stored local archive pairs:
```bash
PYTHONPATH=. python3 research/v2_paper_rth_trail_shadow_20261112.py \
  --cache /private/nov09_11_filled_and_sip.json /private/nov09_11_flat_bid.json \
  --cache /private/nov12_filled_and_sip.json /private/nov12_flat_bid.json \
  --output /private/fresh_report.json
```
The tool refuses to overwrite an existing report. Source caches were preserved on the private host; no raw broker order/client IDs, licensed SIP bars, API keys, or actual account identities were committed. The output contains aggregated cohort results only.

**Decision:** Do not change live RTH exit thresholds, broker-native protections or timers. Add future independent sessions to the frozen comparison, target **20+ dates**, and measure actual filled risk/reward and negative-news eligibility separately. Recommendation Audit remains the sole recommender-linked closed-trade notifier; the all-PAPER research includes unlinked strategy activity without duplicating its alerts. The authenticated holiday rev2 gate was unpaused and valid strictly before **2026-11-13 16:13 America/Chicago**, absent calendar edit.
