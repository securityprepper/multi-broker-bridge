# Historical news, one-minute reversal entries and bearish-sector veto — 2026-11-08

**RESEARCH ONLY. No broker orders submitted or production/PAPER strategy changed.**

## Market data

- AMD, MU, SNDK, SOXX one-minute historical sample for 20 Oct–Nov 2026 sessions; mixed Alpaca SIP + BOATS with Yahoo supplementation for after-hours gaps. Observations are **OHLC**, not tradable bids/asks or actual executions.
- 251 historical trading sessions Nov 7 2025–Nov 6 2026; Alpaca SIP 5-minute and split-adjusted daily bars. SOXX 3:1 Nov 5 split accounted for.
- Day classification: 'broad positive' = at least 2/3 AMD/MU/SNDK regular-session close-to-close positive AND SOXX positive; 'broad negative' = 2/3 negative AND SOXX negative. 118 positive, 83 negative, 49 mixed of 250 days.
- Earliest evening/premarket signals (historical, not full-session forecasts), compare after the day closed to measure true direction. Signal thresholds chosen after studying November 6 and should be forward-tested.

## One-minute timing pattern test (20-session 4–9 AM ET sample)

Only count patterns where current sector strong: at least 2/3 leaders >=+0.5% previous close and SOXX >=+0.25%, plus at least 2/3 leaders >=+0.3% in prior 15 min and SOXX nonnegative.

- One rising close after 1 declining close: 227 overlapping signals; following 30min close positive in 113 (**49.8%**), median future return **−0.002%**.
- One rising close after 2 declining closes: 95 signals; positive in 48 (**50.5%**), median **+0.038%**.
- Three consecutive rising one-minute closes: 136 signals; positive in 75 (**55.1%**), median **+0.087%**.
- Results are forward *prices*, not P/L. One-minute signal is suitable as early alert/potential breakout-limit trigger, not as a stand-alone buy order.

## Independently measured bearish symmetry on 52 weeks

All flags use prior regular close + most recent 15-min momentum from 5-minute bars. Bearish strict means 3/3 AMD MU SNDK lower by >=0.5% vs prior close and all three down >=0.3% over prior 15min, while SOXX down >=0.25% vs prior close with negative 15min momentum.

| Signal | Sessions flagged | Correct closes | Precision | Recall on matching direction |
|---|---:|---:|---:|---:|
| Broad bullish >=0.5%, +0.3% momentum | 137 | 84 | 61.3% | 71.2% of 118 positive |
| Strict bullish same thresholds | 83 | 53 | 63.9% | 44.9% |
| Broad bearish same reversed thresholds | 129 | 63 | 48.8% | 75.9% of 83 negative |
| Strict bearish | 96 | 48 | 50.0% | 57.8% |

Requiring a larger 1.0% price fall and 0.5% 15min momentum for strict bearish: 53 flagged, 33 negative (**62.3% precision**) but only 39.8% recall; includes 13 days that actually closed broadly positive.

Running a bearish alert as a hard veto for an earlier bullish alert within 60 minutes blocked two bullish signal days, **one of which was the Nov 6 rebound**. Hard bearish veto is therefore not recommended; detect bearish->neutral->bullish state transitions.

For the training-selected strict 52-week bullish entry + modeled 9:20 ET premarket exit (hypothetical per-side 0.15% limit allowances), add a veto if two of three leaders had a declining last 5min close:
- Baseline training +$1,777.13, validation +$194.60, validation ex-Nov6 −$206.28, 262 completed modeled trades.
- Bearish veto training +$2,371.13, validation +$205.10, validation ex-Nov6 −$195.78, 231 modeled trades.
- **Fill caveat**: all exits in the original model were hypothetical premarket limit fills, so neither profitability series is validated with broker bid/ask or actual fills.

## Historical news context (case study, not quantified news backtest)

Available timestamped articles were checked to avoid retrospective publication leakage:
- **Oct 27 2026 ~5:53 AM ET** initial Reuters article reported AI-tech optimism and pending Fed policy meeting; later article updates and end-of-day details are **not available** for an earlier signal. https://www.investing.com/news/economy-news/us-stock-futures-muted-as-oil-holds-near-april-highs-ahead-of-fed-decision-4974650
- **Nov 3 2026**: Reuters end-of-day report attributed rebound to AI names buying ahead of midterm results after Nasdaq correction; its end-of-day perspective is not safe to backdate to prior-evening entry. https://www.reuters.com/business/retail-consumer/us-stock-futures-mixed-apple-slides-midterms-loom-2026-11-03/
- **Nov 5 2026 4:07 PM ET** Yahoo Finance reported severe chip losses on data-center/regulation worries and disappointing chip forecasts. It was available before Thursday evening turn upward, and was bearish contextual news, not a bullish prediction. https://finance.yahoo.com/markets/article/qualcomm-micron-arm-stocks-sink-lead-chip-sector-lower-133100607.html
- **Nov 6 2026 4:35 AM ET** Reuters reported Nasdaq futures up 1.48% and broad chip rebound; this supported the direction at 4:35AM but was published **later than** the Thursday evening and 1AM early-buy candidates. https://www.fidelity.com/news/article/default/202611060435RTRSNEWSCOMBINED_L3N46N0QW_1
- **Nov 6 2026 5:24 AM ET** Investing.com reported SOXX +5% and Nasdaq futures +1.3% at publication, also **too late** to justify Thursday 7 PM/Friday 1AM entries. https://www.investing.com/news/stock-market-news/us-chip-stocks-rebound-sharply-after-thursdays-brutal-selloff-5007137

News is worth testing as timestamped inputs (company earnings guidance, policy/regulatory announcements, macro releases, international semiconductor moves, overnight futures), but there is **no quantified 52-week historical headline surprise/sentiment dataset** here, and therefore no evidence yet that adding news increases hit rate.

## Recommendation

1. Split direction **regime** from exact timing **trigger**. Regime uses market breadth, 15/30-minute trend, sector ETF, market futures and *time-valid* material news; short-term timing triggers use first 1-min bar turning up after pullback, but buy only if price then takes out reversal bar high while spread/market depth and position checks pass.
2. Bearish alerts are independent 'AVOID / SHORT WATCH' (not automatically trade shorts or force long liquidation), require sustained downside evidence and keep monitoring for 'END SHORT' / strong confirmed reversal. Do not hard-veto bullish entry based on older bearish alerts.
3. Collect archived news with exact first-publication timestamp and polarity, not retrospective wrap-ups, and run a proper 'price-only vs news-plus-price' rolling out-of-sample comparison, including adverse news whose impact was already priced in.
4. PAPER fill verification and mandatory close are separate broker concerns. No executable order submission based on unverified news sentiment.

**Key result: a single green 1m bar does not materially predict next 30-minute direction; the bearish mirror is not accurate enough to be a day-direction predictor.**
