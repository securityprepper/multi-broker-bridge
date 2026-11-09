# V2 52-week late-session crash coverage and prior-five capped entries — November 9, 2026

**RESEARCH / PAPER SHADOW ONLY.** No LIVE or existing V1 PAPER monitor, broker account, open order, production checkout, or system timer was changed. Calendar cache revision 2 unpaused strictly until November 13, 2026 16:13 CST absent calendar edits.

## Evidence and causal design

Historical source is the existing **split-adjusted SIP 5-minute OHLC** observation sample, November 10, 2025–November 6, 2026: **2,244 individual-stock sessions** including all no-signal days, **209** close-to-close declines >=5%, **254** gains >=5%, and **250** semiconductor sector sessions (**118 positive, 83 negative, 49 mixed**). The reference audit `/tmp/v2-run10-daily-audit.json` includes original alert timestamps and daily outcomes. The new event-level audit `/tmp/v2-run12-late-cap-events.json` includes **1,828** events across three late variants, with first completed-candle timestamp, price, actual eventual close label, regular-session extrema for outcome review, next regular opening comparison and price eligibility proxy. Local /tmp research artifacts may be ephemeral; the committed script regenerates them.

Every late signal observes **only fully completed candles** between 10:35 and 15:55 ET and previous regular-session closes. Test three fixed, additive watch candidates: (a) original overlapping >=2.5% from prior close including >=1.0 percentage-point fall in 15m; (b) >=1.5% below today's 9:30 opening print; (c) >=3% below prior close, SOXX >=1% lower, and >=4 related peers >=1% lower. The first-hour open-relative watch is separately retained. The current day's final outcome, next 5m open and following regular open are scoring labels ONLY. Next-bar limit eligibility assumes 15bp friction, 30bp price envelope: not a quote or verified fill.

## Track 2: Last missing severe-down cases

| Additive system | Major down stock-days detected | Major misses | Warnings on nonmajor-down stock-days |
|---|---:|---:|---:|
| Prior premarket + first hour | 200 / 209 | 9 | 806 |
| Add 09:35–10:30 opening-relative >=1.5% WATCH | 206 / 209 | 3 | 1,032 |
| Add 10:35–15:55 late-session WATCH variants | **209 / 209** | **0** | **1,207** |

The incremental **three** major-loss stock-days were:
- **SNDK March 5, 2026**: first new late warning **12:00 ET**, -3.0039% versus prior close; eventually -5.3568%. Hypothetical next-bar sale versus holding to following open: +5.2853 percentage points.
- **SOXX June 16, 2026**: **10:35 ET**, -2.2118% versus prior close; eventually -5.9380%. Corresponding modeled advantage: +0.4007 pp.
- **WDC August 5, 2026**: **15:25 ET**, -2.7879% versus prior close; eventually -5.3589%. Corresponding modeled advantage: +19.1676 pp (extreme **overnight** price-mark scenario, not a proven executable sale).

All three warnings were **before the stock/ETF had already lost 5%**, but **after the regular opening**, and WDC's was late in the session. As historical hindsight coverage, 209/209 is NOT a prospective premarket hit rate. The final union has **175/209** warnings before the instrument had already declined 5%, while **34/209** are late relative to that loss threshold. Earliest premarket serious-loss warning across the original system remains WDC **November 13, 2025 at 04:20 ET**. No late-session indicator prevents an overnight gap occurring earlier that morning.

As individual candidate rules: 10:35–15:55 strict overlap emitted 398 watches (166 major, 232 nonmajor); open-relative emitted 934 (191 major, 743 nonmajor); sector-breadth emitted 496 (185 major, 311 nonmajor). They overlap; do not add them as independent days. The full late union adds **175** nonmajor warnings beyond the existing 1,032. In an earlier/later split at September 1, 2026, hypothetical late opening-relative sales versus holding to next open averaged **-0.4497 pp earlier, +0.7219 pp later**. Sector-breadth averaged **-0.6795/+0.6274 pp** and strict-overlap **-0.6111/+0.1652 pp**. Such reversals and high false-warning counts preclude automatic selling.

## Track 1: Prior-five completed-session buy admission cap

Keep the earliest as-of opening-momentum signal per independent session; tie-break by strength known at that completed-bar timestamp. Then apply ONLY previous **five completed** daily returns (six strictly prior regular-session close marks, requiring every mark present); missing history rejects the filtered candidate. A rejected first candidate does **not** get retrospectively replaced by a later-day candidate. Compare all rules over the **same** 117 baseline entry-signal dates, zero return on no-trade days, fixed modeled 15bp/30bp entry friction/limit. Earlier period has 97 dates, September–November 20 dates.

| First-only admission policy | Earlier day-equal return | Sept–Nov day-equal return | Later admissions / 20 dates |
|---|---:|---:|---:|
| First qualifying stock (unfiltered) | **+0.3806%** | **-0.2497%** | 20 |
| Only if SOXX five-day decline is less than 5% | +0.2586% | +0.0608% | 14 |
| Only if stock five-day decline is less than 5% | +0.0818% | +0.1146% | 15 |
| Only if stock five-day trend is nonnegative | +0.1354% | **+0.4472%** | **9** |
| Only if stock AND SOXX five-day trends nonnegative | +0.1071% | +0.1063% | 6 |

**Crucial holdout integrity:** Earlier-period selection would choose the **unfiltered first-only** policy (+0.3806%). It returned **-0.2497%** in the later period. The superficially attractive stock-positive rule was not selected in the earlier sample; its +0.4472% on just **nine later admissions** is a retrospective observation, not a validated improvement. The first-only approach still omits 112 of the original 150 major-winning stock-signal days. Filters reduce exposure and opportunity simultaneously.

## Execution, daily review and remaining blockers

- No complete 52-week SIP/BOATS bid/ask NBBO/depth, confirmed 1m stream, extended-hours spread, synchronized timestamped QQQ/futures/earnings/news or V1 matched fills in these replay inputs. A favorable next-bar OHLC mark does **not** establish a real PAPER sale or buy, especially for WDC's 19pp overnight case.
- All 2,244 stock-days remain in the reference audit; the new code covers **every late rule trigger**, not merely days ending at +/-5%. Candidate daily events can be reproduced using the script's `--events-output` option and the original immutable inputs.
- **174 offline research unit tests passed**, including 14 new causal/boundary cases, plus integration checks of the 206->209 severe-case progression and 117 entry-signal dates.
- Next priorities: actual historical quote-level executable prices and BOATS coverage; preceding-evening/early premarket predictors that can protect through opening, independent other-sector 52-week holdouts, and V1 matched PAPER fills. No automatic trades or V1 strategy changes are supported.

Reproduction from an isolated research checkout with existing read-only datasets:

`python3 -m research.v2_late_session_and_prior5_cap --audit /tmp/v2-run10-daily-audit.json --output /tmp/v2-run12-late-cap-results.json --events-output /tmp/v2-run12-late-cap-events.json`

`python3 -m unittest discover -s research -p 'test_*.py' -q`
