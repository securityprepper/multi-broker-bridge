# November 11, 2026 — V2 research: RTH rapid-loss two-falling-bar compatibility

Independent read-only Alpaca PAPER audit; no active V1 PAPER/LIVE, IBKR, broker-order, stop, timer or holiday changes.

## New evidence

An authenticated PAPER snapshot as of 2026-11-12 01:34:56 UTC contained 124 recent orders (120 filled, four canceled), corresponding in the bounded research cohort to 60 completed round trips over November 9–11 Chicago. One authenticated PAPER account is covered, but its native account identifier is unavailable in the sanitized cache; other accounts remain unknown. The round trips are 51 MBB and 9 FDR. Partial fill activities and order pairs are not double-counted. Historical BUY news: NEWS_UNKNOWN, outcome-only controls, not eligible signals.

**Of 14 MBB regular-session positions filled at a loss within ten minutes, nine (9/14)** had completed contiguous SIP one-minute candles producing two successive lower highs and lower lows within 180 seconds before the actual broker-filled sell. At each qualifying last completed candle, the close was underwater but less than 1% below entry; no observed 0.5%-armed/0.5%-reversed peak trail took precedence. In **four of those nine**, the latest compatible three-bar close-to-close price movement was under 0.10%. Three of the other five positions had fewer than three completed post-entry bars and two had no otherwise compatible recent pattern.

**This is a compatible historical pattern, NOT a verified actual trigger.** Original MBB decision-reason-to-filled-order-UUID evidence is still missing. Do not infer causation from price or fill proximity.

The active host auto_paper.py imports and instantiates TrendMonitor from trend.py. Regular-session trend.py currently permits a two-falling-bars SELL candidate without a minimum loss size or profit precondition. The independent test insists on consecutive minute timestamps. The source helper itself checks lower highs/lows but not timestamp adjacency. This audit excludes premarket, where separate profit-gated rules apply.

## Fixed-boundary quote countercheck

The nine compatible rapid losses realized **-$55.76 gross**. Of them **eight** had fresh, uncrossed SIP quotes with adequate displayed best-bid size at the 13:40 Chicago fixed boundary. Hypothetical sale of those eight at that historical displayed bid totals **+$48.17 gross**, consisting of **5 profitable and 3 losing** positions, versus **-$37.29 actually realized** on those same eight, for an **indicative +$85.46 difference**. The ninth has no usable boundary quote. This is NOT executable or after-fee P/L: the bid may not fill; it does not account for interim adverse moves, stop precedence, fee/slippage, order eligibility or liquidity changes. It does not demonstrate that a hold-to-flat strategy could safely capture the difference.

The compatible set contains APH, DVN, FTNT, OKTA, ETN, TENB, WMB, KMI and SMCI. KMI's fixed-boundary bid produced a worse hypothetical loss than its actual early sale, demonstrating that a universal hold rule is not justified. AMD on Nov 9 was a premarket exit, and CARR's Nov 11 two-minute sale had too few completed post-entry bars for this specific pattern; neither is attributed to the two-bar cause. MCHP's Nov 11 sale was profitable and is outside the underwater-loss denominator.

## Controls and limits

Research-only script research/v2_paper_two_bar_rth_compat_20261111.py and test tests/test_v2_paper_two_bar_rth_compat_20261111.py. Nine offline integrity tests passed, including no post-fill bar leakage, exact 1-minute adjacency, higher-priority -1% watch and trail exclusion, source scoping and zero broker orders. Private broker identifiers, licensed raw one-minute bars and broker credentials remain off GitHub.

Data cover **3 trading sessions**, not the required **20+ untouched days**; no robust held-out parameter comparison or executable after-fee advantage has been established. Actual MBB exit causes remain UNKNOWN without a durable decision-reason/order-ID join. No V2 PAPER release, negative-news eligibility change, routine notification or live trading modification is warranted. Next: read-only immutable reason-to-order join; longer forward-only per-account sample; full quote/slippage/fees and adverse-tail analysis before proposing any exit change.

