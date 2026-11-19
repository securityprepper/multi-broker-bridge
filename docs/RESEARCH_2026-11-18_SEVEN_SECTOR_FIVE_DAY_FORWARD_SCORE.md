# November 18, 2026 — five-session, seven-sector immutable forward-score checkpoint (READ ONLY)

This checkpoint evaluates only independently timestamped, earlier-issued forecasts, never the descriptive prior-close-to-final-close direction. It does **not** validate an executable trading strategy or recommend production/PAPER orders.

## Data eligibility and method

- Read only the stored, independently sealed daily `/var/lib/securityprepper-v2-forward-shadow/scores/YYYY-MM-DD/1340CT.json` artifacts on www3. Require `capture_complete=true`, three sealed forecast slots (09:35, 09:45 and 10:05 ET), `missing_slots=[]` and `future_bar_lookahead_in_forecasts=false`.
- Five complete and distinct sessions met the filter: **Nov 12, 13, 16, 17, 18, 2026**. Nov 11 is not counted as complete. The policy is `v2-7sector-forward-baselines-20261111-r2` with SHA-256 `629a5f7dab20d8ba4d5ed1e51b3947f658d4bb4971ffdf5e95ece2078fdf3ff3`.
- Seven contemporaneously covered sector ETF proxies: semiconductor, gold miners, energy, financials, industrials, healthcare and software. Only originally issued UP/DOWN predictions count in `issued`; abstentions are **excluded from directional precision** and included in coverage analysis. Score `60m` and `flat` (13:40 CT) separately; do not conflate them.
- `modeled_after_30bp_pct` deducts illustrative **30 basis points**, not verified bid/ask fills, short borrow, financing, slippage, actual commissions or actual broker profitability. One ETF across three slots and a single market day creates correlated observations; **n forecast rows is NOT n independent trials**. Day clustering is mandatory for confidence.

## Exact count — five complete forward days

| Arm | Horizon | Issued direction rows | Direction hits | Modeled winners after illustrative 30bp | Mean modeled return per issued direction | Days with positive same-arm daily mean |
|---|---|---:|---:|---:|---:|---:|
| Benchmark direction | 60m | 88 | 39 (44.32%) | 24 | -0.2043% | 2/5 |
| Benchmark direction | 13:40 CT | 88 | 39 (44.32%) | 34 | -0.3926% | 0/5 |
| Peer-confirmed direction | 60m | 62 | 25 (40.32%) | 18 | -0.1886% | 1/5 |
| Peer-confirmed direction | 13:40 CT | 62 | 30 (48.39%) | 26 | -0.3434% | 1/5 |

Daily 60m modeled mean percent, benchmark: Nov 12 **-0.4460** (n18), Nov 13 **+0.1883** (n16), Nov 16 **-0.5207** (n19), Nov 17 **+0.1279** (n17), Nov 18 **-0.2914** (n18). Peer-confirmed: Nov 12 **-0.3701** (n12), Nov 13 **-0.1296** (n10), Nov 16 **-0.5026** (n15), Nov 17 **+0.2370** (n13), Nov 18 **-0.1247** (n12).

## Paired-arm comparison to avoid selection bias

Match each peer-confirmed issued 60m forecast on its **exact date, sector, forecast slot and horizon** against the original benchmark's forecast. **All 62 matched rows had the same UP/DOWN direction**. Thus both arms scored exactly **25/62 directional hits, 18/62 illustrative 30bp-positive marks, -0.1886% mean** on the *matched* set. The peer gate **abstains** on some baseline decisions; it did not improve the direction or outcome on any of the 62 observations it admitted. Comparing its own aggregate to all 88 benchmark forecasts without conditioning on matching is not a valid improvement claim.

Exploratory sector-specific peer-confirmed 60m marks: semiconductors 10 hits /13 issued, 9/13 30bp-positive modeled, average +0.686%; software 5/7 hits, 5/7 modeled winners, +0.633%; gold miners 3/11, -0.525%; energy 2/11, -0.534%; financials 1/8, -0.733%; industrials 2/6, -0.732%; healthcare 2/6, -0.521%. Semis/software are **not** qualified as robust profitable strategies: each subset spans at most five trading sessions, shares market-day correlations, lacks tradeable receiving-broker ask/bid/borrow and fees, has no untouched 20–30 day forward validation and was inspected after observing the outcomes. Do not convert these exploratory rows into new trading rules or alerts.

## Decision and follow-up

**NO GO / research only.** There is no newly verified robust positive after-fee forward edge. Freeze original forecast rules; continue the native immutable as-of prospective scorer toward at least 20–30 genuinely untouched trading sessions, record quote spread, fill feasibility, downside tails and abstentions; reject any posthoc sector selection without a distinct future holdout.

No broker calls, real PAPER orders, LIVE orders, Pushover alerts, timers, holiday publisher, V1 safety gate, or production executor modifications were involved. This report is an internal reproducibility checkpoint and **not a recommendation notification**.
