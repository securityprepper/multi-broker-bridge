# V2 open-relative crash blind spots and causal admission caps — November 9, 2026

**RESEARCH ONLY.** No broker access, trading enablement, installed V1 changes, host timer changes, or production checkout writes. Validated holiday reference: unpaused calendar revision 2, strictly before Nov 13 2026 16:13 America/Chicago absent calendar invalidation.

## Data and method

Same 52-week split-adjusted Alpaca SIP **five-minute OHLC** history, November 10, 2025–November 6, 2026. **2,244 stock-days** (including no-signal sessions), nine semiconductor symbols including SOXX, **209** close-to-close declines >=5% and **254** gains >=5%. Earlier/later cutoff **September 1, 2026**; sector baseline unchanged at **250 sessions: 118 positive / 83 negative / 49 mixed**. The existing complete daily outcome baseline audit is `/tmp/v2-run10-daily-audit.json`, read only.

The downside candidate tests the **first completed 5m bar between 09:35 and 10:30 ET** whose stock close is at least 1.0%, 1.5%, or 2.5% below the **09:30 stock opening print**, with an optional contemporaneous SOXX opening-to-current decline >=0.25%. This targets severe selloffs that start after positive previous-close gaps. The existing original rule (decline >=2.5% from previous regular close **including** >=1.0pp over previous 15 minutes) is unchanged. Previous-sector breadth and reversal warnings remain available; new opening-relative alarms are additive **WATCH candidates**, not replacements. Never uses the same-day closing outcome in signals.

All evaluated signals use completed candles; only *scoring* uses following five-minute **OPEN** and next regular opening, with 15bp adverse execution assumption and 30bp limit envelope. These are price *proxies*, not executable bid/ask quotes, book depth or proven fills. Missing next-session opens are unscored. No five-minute high/low is treated as guaranteed a fill.

## Track 2 — Previously missed serious downside days

Prior combined premarket/first-hour warning system detected **200 of 209** severe declines, while generating **806 warnings on nonmajor-down days**. An added 1.5%-below-regular-open watch:

| Rule | New alarms alone | Major-down hits in new alarms | Newly caught among 9 baseline misses | Combined severe coverage | Combined nonmajor alarms |
|---|---:|---:|---:|---:|---:|
| No added rule | — | — | — | **200/209** | **806** |
| Opening decline >=1.0% | 1,026 | 169 | 6 | **206/209** | **1,178** |
| Opening decline >=1.5% | 766 | 148 | **6** | **206/209** | **1,032** |
| Opening decline >=2.5% | 409 | 115 | 4 | 204/209 | 878 |
| Opening decline >=1.5%, SOXX down >=0.25% | 644 | 138 | 5 | 205/209 | 957 |

The 1.5% candidate delivers **six genuinely new severe-loss alerts** with **226 incremental nonmajor alarms**, and precedes the baseline alert or newly catches **20 serious down stock-days**. The six previously missed cases (all earliest observed times ET) were: **WDC Nov 20 2025 09:40 (close -8.912%); AMD Nov 20 10:10 (-7.820%); AMD Dec 17 2025 10:10 (-5.224%); INTC May 29 2026 09:45 (-5.115%); MU Jun 16 2026 10:20 (-6.157%); SNDK Jun 16 2026 10:20 (-5.502%)**. All six were warned *before* they were down 5% versus previous close, but **after** the regular-session open. They cannot justify claims of avoidance of the preceding overnight gap.

**Still missed even after the 1.5% addition:** SNDK Mar 5 2026 (-5.357%); SOXX Jun 16 (-5.938%); WDC Aug 5 (-5.359%). Investigate steady declines, delayed deterioration, lack of sector corroboration and late session crashes with a separate 10:30–16:00 causal study.

For the 1.5% rule alone, 618 of 766 warnings were on days **not** finishing down >=5%. Hypothetical immediate exit versus holding until the next regular opening averaged **-0.1021 pp** in the earlier period (654 alarms), versus **+0.6333 pp** later (112). By outcome group, earlier major-down alarms averaged +2.252 pp saved, but nonmajor warnings **-0.6528 pp** lost; later major-down +1.706 pp, nonmajor +0.315 pp. The false-warning opportunity cost remains substantial. This rule is unfit for automatic selling.

The earliest baseline severe warning remains **WDC Nov 13 2025, 04:20 ET**. A regular-open-relative supplement does not improve warnings before market opening. The current 2.5%/15-minute *overlapping* original weakness test remains unchanged.

## Track 1 — Causal per-sector BUY admission cap

The existing first-hour rising-sector strategy emitted **697 buy signals on 117 independent session dates**, including **150 eventually >=5% winners** and **40 eventually <=-5% losers**. To test correlated sector concentration, retain the *first* 1, 2, or 3 as-of candidates across semiconductor stocks per session, sorting by completed-signal timestamp, then current observed stock strength for same-time ties, then symbol. **No same-day final outcomes or future alerts determine rank.** Compare the same 117 independent baseline alert-days, using zero-return when next-five-minute limit-price proxy rejects an entry.

| Entries admitted per signal day | Signals | Major winners retained | Major losers retained | Earlier day-equal mean | Sep–Nov day-equal mean |
|---|---:|---:|---:|---:|---:|
| All candidates | 697 | 150 | 40 | +0.0860% | **-0.6568%** |
| First **1** | 117 | 38 | 8 | **+0.3806%** | **-0.2497%** |
| First 2 | 232 | 69 | 18 | +0.2792% | -0.4948% |
| First 3 | 341 | 92 | 23 | +0.3816% | -0.5226% |

The first-only limit appears to reduce correlated losing exposure while improving the day-equal modeled means in both periods; **however, it excludes 112 of the 150 major winning signal stock-days**, while its later-period average remains negative and selection by earliest event can be arbitrary. Trading costs are modeled, not evidenced. This is an independent **position-concentration risk hypothesis**, not demonstrated V2 outperformance versus V1 or an instruction to change live/PAPER sizing.

## Integrity and remaining gaps

* Re-ran **160 offline research unit tests** including eight new causality and ranking tests. One new helper initially paired date keys with string keys and yielded no next-open scores. The mismatch was corrected **before reporting** and all results recomputed.
* Full year **one-minute bars**, executable SIP/BOATS NBBO and order book sizes, actual historical limit fills, synchronized time-stamped QQQ/futures/earnings/news, independent 52-week non-semiconductor sectors, and matched V1 execution ledgers remain missing. Consequently, no real-world precision, latency, next-open loss avoidance, or broker profitability improvement can be claimed.
* Previously reviewed **all** 2,244 days, including winning/losing untriggered cases. This study specifically analyzes the nine severe-down baseline misses and simultaneously re-evaluates every existing first-hour BUY signal. No new dataset is being represented as BOATS quote-level history.

Run from an isolated research checkout (the old divergent and production checkouts must remain untouched):

`python3 -m research.v2_open_relative_blindspots_and_admission_caps --audit /tmp/v2-run10-daily-audit.json --output /tmp/v2-run11-results.json`

`python3 -m unittest discover -s research -p 'test_*.py' -q`

**Recommendation:** Keep immediate warnings. Research open-relative weakness as an extra WATCH priority and the first-per-sector cap as a risk-budget hypothesis. Do not auto-sell or automatically change buying limits. Next prioritize timestamped actual NBBO/BOATS quote samples and first-hour-versus-after-10:30 loss timing, then holdouts in other sectors.
