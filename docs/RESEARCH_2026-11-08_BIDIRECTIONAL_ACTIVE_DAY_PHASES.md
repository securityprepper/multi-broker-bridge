# 52-week semiconductor bullish vs bearish active-day and phase analysis — Nov 8, 2026

**Historical research only. NOT actual account P/L, guaranteed short availability, confirmed premarket fills, or a commissioned algorithm.**

## Source and definitions

Authenticated Alpaca historical SIP five-minute split-adjusted bars, AMD/MU/SNDK/SOXX and held-out NVDA/AVGO/WDC/TSM/INTC. November 7, 2025–November 6, 2026: **251 trading sessions**. Split-adjusted SOXX prevents false signals at its November 5, 2026 3:1 split. SIP five-minute history excludes 8 PM–4 AM BOATS, and OHLC bar touches cannot establish executable bid/ask or real fills.

Previous researched long candidate: Two of AMD/MU/SNDK at least +1.5% vs previous regular close, SOXX >=+0.75%; at least two leaders +0.7% over preceding 15 minutes, SOXX momentum nonnegative, and recent breakout above previous 5m high. Hypothetical limit entry on next 5m candle at completed bar close +0.15%, whole shares <=$2,000 each symbol, 8:30 AM Eastern limit exit based on prior bar close -0.15%. Require entry before exit. Same sector signal extended without changing thresholds to five additional peer names.

Mirrored **bearish simulation**: Two leaders <=−1.5% vs previous close, SOXX <=−0.75%, two leaders <=−0.7% over 15min with SOXX nonpositive, two leaders' closes below prior 5-minute candle lows. Hypothetical short at next 5min candle (signal close less 0.15%), cover at 8:30 AM ET based on prior close plus 0.15%, otherwise proxy at 9:30 opening price. Same 9 symbols. Borrow availability, short-sale constraints, margin, fees and recall risk NOT modeled. This mirror is not an operational short recommendation.

One *active day* is a distinct trading date with >=1 modeled completed trade in the applicable group. Profitable active day = combined hypothetical P/L across all nine symbols strictly positive. **Not** symbol win rate.

## Active days and profitability

| Approach | Active days /251 | Active % | Profitable days | Win % active | Losing days | Modeled P/L |
|---|---:|---:|---:|---:|---:|---:|
| Bullish long | 36 | 14.3% | 26 | 72.2% | 10 | **+$3,532.27** |
| Mirrored bearish shorts | 46 | 18.3% | 13 | 28.3% | 33 | **−$6,043.62** |
| Both activated naively on all dates | 77 unique | 30.7% | 35 net-positive calendar days | 45.5% | 42 | **−$2,511.35** |

For both, **5 dates** have conflicting long and short candidate trades. The naive combined figure is NOT a valid execution strategy: it assumes both long and short same-day entries, ignoring reconciliation, netting, borrow and timing conflicts. It only demonstrates that increasing activity under these rules degrades success rate.

The long strategy did 141 completed modeled transactions on four original stocks and 173 on five peers, total 314; shorts 400 modeled transactions.

## Week context

Weekly market direction was labeled **after the week finished** from prior Friday to current week's final regular close. A positive sector week = >=2 AMD/MU/SNDK up and SOXX up; negative analogous; else mixed. This is retrospective analysis, not an input available to trades on Monday or Tuesday.

Within the 36 long-active trading dates:
- **21 (58.3%)** occurred in weeks that eventually closed up, **15 of 21 (71.4%)** were profitable days.
- **13 (36.1%)** in weeks that eventually closed down, **10 of 13 (76.9%)** profitable.
- **2 (5.6%)** in mixed weeks, 1 profitable.
- **13 (36.1% of all long-active days)** were in up weeks which also **followed an up week** (a strict multi-week continuation); 8 of 13 profitable.
- **8 (22.2%)** were in up weeks following a down week; 7 profitable.
- From **previous already completed week**, known by the next week's Monday: 21 active after an up week (13 profitable, 61.9%); 14 after a down week (12 profitable, 85.7%); 1 after mixed (1 profitable).
- Across the year: 30 positive weeks, 18 negative weeks, 4 mixed according to this sector definition (52 weekly bins; first lacks prior week baseline).

For shorts, **45 of 46** active days have full reliable 09:25/09:30/15:55 comparison bars. Week classification for them: 17 active during rising weeks (4 profitable), 23 during losing weeks (9 profitable), 5 during mixed weeks (0 profitable), 1 unclassified due to incomplete timestamp coverage.

## Premarket vs regular direction

Direction measures:
- **Overnight/premarket**: prior regular-day close -> 09:25 AM ET five-minute bar close.
- **Regular-hours**: 09:30 AM ET opening price -> 15:55 five-minute bar close (~4PM close).
- **Whole day**: previous regular close -> current regular close.
- Sector up/down requires 2 of 3 AMD/MU/SNDK in same direction AND SOXX same direction; otherwise mixed.
- If a signal was detected before 09:25, the observed premarket direction is **partly contained in the signal's own price-above/below-prior-close definition**. Thus premarket-match rates are descriptive and NOT independent forecast skill.
- **Bullish active days (36)**: premarket up **34/36 (94.4%)**, premarket down 2. Regular-hours up **13/36 (36.1%)**, regular down **15/36 (41.7%)**, regular mixed 8/36 (22.2%). Whole-day up **28/36 (77.8%)**, whole-day down 2/36 (5.6%), mixed 6/36 (16.7%).
- Bullish premarket->regular outcomes: up/up **11**, up/down **15**, up/mixed **8**, down/up **2**. Among the 34 premarket-up days, **15 (44.1%)** reversed to regular-hours down.
- **Bearish active days with complete phase coverage (45)**: premarket down **36/45 (80.0%)**, premarket up 8, mixed 1. Regular-hours down **19/45 (42.2%)**, regular up **20/45 (44.4%)**, mixed 6. Whole-day down **24/45 (53.3%)**, whole-day up 12/45 (26.7%), mixed 9/45 (20.0%). One additional short day (2025-12-12) has incomplete bars for phase classification.
- Bearish premarket->regular: down/down **16**, down/up **17**, down/mixed **3**, up/down 2, up/up 3, up/mixed 3, mixed/down 1. Among the 36 premarket-down dates, **17 (47.2%)** reversed to regular-hours up.

**Interpretation:** These strategies largely detect an extant overnight/premarket trend; they do not adequately forecast regular-market direction. Thus 8:30 AM exit may be preferable on those historical occasions, but profitability is not established without executable premarket quotes/fills.

## Alternate mirrored bearish exits

With identical -1.5%/−0.75% breakdown and 15min -0.7% test, same 0.15% buffer, holding other modeling assumptions fixed:
- Breakdown -> cover 7:00 AM ET: 33 active days, 10 winning (30.3%).
- Cover 7:30: 38 active, 12 winning (31.6%).
- Cover 8:00: 44 active, 13 winning (29.5%).
- Cover 8:30: 46 active, 13 winning (28.3%).
- Cover 9:20: 52 active, 17 winning (32.7%).
- All had substantial negative pre-Aug31 P/L (roughly −$4,986 to −$6,903) despite some later positive returns. These negative results are enough to reject this straightforward short mirror for automatic PAPER execution.

## Actionable research conclusion

1. Keep bullish signal for *candidate PAPER shadow checks*, not proven profitability: ~14.3% annual active-day coverage, ~72% historically modeled profitable active days at 0.15%-each-side assumption, but poor opening-fill robustness and some major drawdowns.
2. **Do not trade mirrored short rule**: 28% modeled profitable active days, huge negative training P/L, borrow/margin costs not modeled.
3. Keep bearish signals as a **risk condition** for uptrends (AVOID/REDUCE LONGS), with state transition bearish -> neutral -> bullish; do not make them a permanent veto because real rebounds occur.
4. To increase annual coverage without destroying win %, research **separate regular-session strategies** and **market-open reversal conditions**, not a mirrored overnight short that trades opposite existing momentum.
5. Directional accuracy must be reported separately for premarket, regular session, and complete prior-close-to-close session. Do not claim 94% premarket accuracy as predictive, because the signal itself uses prices from that period.
6. Track *actual* PAPER bid/ask, order placement, fills and volume before treating any OHLC-touch hypothetical P/L as successful.

Working files are on authorized www3 /tmp: `semis_year_day_context.py`, `semis_bearish_mirror_52wk.py`, `semis_bidirectional_results.py` (latter not written due tool restriction). This report preserves only findings, not full source.
