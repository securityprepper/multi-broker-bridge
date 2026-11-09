# V2 semiconductor prior-five volatility-scaled emergency warning stress — November 9, 2026

**Research only. No broker orders, V1 PAPER/LIVE service/timer/config changes.**

## Why this test

A fixed -2.0%, -2.5% or -3.0% from previous regular close is not equally important for every semiconductor. The owner's existing 15-minute weakness rule uses **overlapping**, not additive, tests: total drop >=2.5% **including** at least 1.0 percentage point of decline within the preceding completed 15 minutes. Earlier tests show very high false-positive warning volume. This experiment asks whether the **mean absolute close-to-close % move over the previous five COMPLETED regular sessions** improves serious loss detection and reduces nonmajor signals when used as a dynamic threshold.

## Exact causal methodology

Reuse nine split-adjusted SIP 5-minute histories, AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM, INTC (Nov 2025–Nov 6, 2026). Freeze the same 2,244-row prior stockday cohort, minus 9 rows without sufficient six earlier completed closes to compute five completed close-to-close changes: **2,235 comparable stockdays / 209 final-day <=-5% close-to-close decliners**. Exclude *same-day* close from prior-five features. Signal requires stock threshold total decline AND >=1.0pp stock decline over last 15m AND contemporaneous SOXX down >=0.5% AND at least half other peers down >=0.5%, all using **completed** five-minute bars. Test first qualifying signal per stock-day, including stock-days without major loss; do not use final-day labels as signal inputs.

Compare three fixed levels 2.0/2.5/3.0% to three dynamic thresholds **max(2%, c × previous-five mean absolute return)** at c=.8, 1.0, 1.25, and max(2.5%, previous-five mean absolute return). This is *not ATR* (it does not use high-low ranges). Compare earlier through Aug 31, 2026 and untouched later Sep 1–Nov 6, 2026. Hypothetical exit price is next 5-minute bar **opening**, versus first following regular open, with 30bp/60bp adverse-cost uncertainty. These are prices, **NOT** actual NBBO, after-hours limit fills, or order executions. Preopen alert need not precede the actual overnight loss.

## Later-period results (49 severe -5% stock-days)

| 15-min stock weakness>=1pp, SOXX+peer-confirmed total drawdown candidate | Serious hits /49 | Warnings on nonmajor days | All warnings | Hypothetical early sale better than next open | Mean 30bp modeled benefit |
|---|---:|---:|---:|---:|---:|
| Fixed 2.0% | **40** | 66 | 106 | **42.45%** | **+0.0652 pp** |
| Fixed 2.5% | 39 | 58 | 97 | 40.21% | -0.0321 pp |
| Fixed 3.0% | 39 | **45** | 84 | 38.10% | -0.1108 pp |
| Adaptive max(2.0%, 0.8×prior5 abs) | 39 | 55 | 94 | 37.23% | -0.1913 pp |
| Adaptive max(2.0%, 1.0×prior5 abs) | 37 | 49 | 86 | 32.56% | -0.4767 pp |
| Adaptive max(2.0%, 1.25×prior5 abs) | 34 | 45 | 79 | **30.38%** | -0.5320 pp |
| Adaptive max(2.5%, 1.0×prior5 abs) | 37 | 44 | 81 | 32.10% | -0.5567 pp |

**Conclusion:** A higher threshold predictably cuts warning volume, but even the best tested later-period variant failed a 50% *hypothetical beneficial exit* rate, far below the desired 80% profitable-decision target. Volatility scaling based on five completed closing returns sacrificed severe-loss coverage and produced **worse** modeled exit outcomes. At 60bp adverse cost even the fixed 2% rule's later +0.0652pp mean becomes **-0.2348 pp**. Neither fixed nor adaptive tested threshold justifies an automatic SELL. This does not show whether an alert is useful for risk monitoring.

In the earlier period, fixed 2%, 2.5% and 3% warnings generated **501/453/404** signals and **352/304/257** nonmajor warnings respectively; corresponding modeled early-sale means were **-0.7925/-0.9659/-1.0260 pp**. This opposite-sign or substantially negative earlier performance is another reason not to deploy.

The fixed 2% rule detected **25 of 49** later severe losses while still above -5% at its alert; the fixed 2.5% and 3% rules each detected **23** that early, the adaptive 1.25× only **14**. Early warnings capable of averting already-occurred overnight gaps remain a separate limitation. The earliest severe-loss warning and complete list of missed severe cases for each candidate are available in the committed structured result JSON.

## Data gaps and action status

Historical executable SIP/BOATS **bid/ask quotes** and depth, issuer/futures/news causally synchronized records, session-specific order availability, IBKR/Alpaca position/fill/stop matching and cross-sector independent validation remain needed. Gold/miner companion study (RESEARCH_2026-11-09_V2_GOLD_MINER_SIP_LEAD_LAG.md) independently finds that gold direction does not reliably predict profitable miner purchases. Do not extrapolate this semiconductor threshold to gold miners.

**Action:** Retain WATCH/risk classification and emergency broker safety monitors; do not tighten or disable V1 safety exits. Do not authorize new PAPER/LIVE orders or synthetic stops. Focus instead on fewer high-precision multi-source alerts with verified execution uncertainty and independent day-level out-of-sample holdouts.

## Reproduce

```bash
python3 -m research.v2_semi_prior5_adaptive_alert --output /tmp/v2_semi_prior5_adaptive.json
python3 -m unittest -v research.test_v2_semi_prior5_adaptive_alert
```

Results structured JSON preserves per-candidate earlier/later coverage, false warnings, missed severe examples, first warning timestamp and next-open sell benefit. **7 targeted tests passed**. The script reads the original 52-week SIP input and frozen cohort manifest read-only and never calls a broker.
