# V2 as-of 5-minute entry and exit confirmation — November 9, 2026

**RESEARCH ONLY.** This is an offline study; no broker connection, streaming subscription, order, installed V1 file, host timer, or execution policy has been changed.

## Source and causal protocol

Study 2,244 split-adjusted SIP 5-minute semiconductor stock-days, November 10, 2025 through November 6, 2026 (AMD, AVGO, INTC, MU, NVDA, SNDK, TSM, WDC, SOXX). Previous sector baseline: 250 sessions (118 positive, 83 negative, 49 mixed). Outcomes include 254 gains >=5% and 209 declines <=-5%.

At signal time, only the last **completed** five-minute bar, its immediately preceding completed bar, the previous regular-session close and, for the regime filter, the **five completed days before the target session** are used. A test first briefly exposed a same-day-final-close reference bug in the new research script; fixed it **before final testing** by enforcing strictly earlier session dates, and added a regression test. The original overlapping downside rule remains 2.5% total from prior close **including** 1 percentage point in the last 15 minutes. The new five-minute rules are optional, additional experimental gates, not replacements.

PAPER price calculations assume 15 bp per side adverse execution friction and a 30 bp limit envelope. The next five-minute opening print and following regular-session opening marks are **retrospective scoring proxies**, never considered live inputs or actual executable bid/ask fills. No missing or unscorable next open is fabricated. Correlated stocks are grouped by independent calendar day.

## Track A — Causal admission filters for existing 09:35–10:30 rising-sector BUY signals

Baseline: 697 alerts, 150/254 major winners caught, **40** major decliners among buys. The baseline's day-equal hypothetical net return to 14:00 was **+0.0860% through August**, **−0.6568% September–November**.

| Post-signal filter, evaluated at original decision time | Retained BUY signals | Major winners retained | Major decliners bought | Earlier day-equal net | Later day-equal net |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline, unfiltered | 697 | 150 | 40 | +0.0860% | −0.6568% |
| SOXX's just-completed 5-minute move >=0 pp | 668 | 143 | 38 | +0.0803% | **−0.7666%** |
| Stock and SOXX recent 5-minute move >=0 pp | 650 | 134 | 36 | +0.0614% | −0.7915% |
| SOXX 5-minute move >=+0.20 pp | 602 | 126 | 36 | +0.0651% | −0.8823% |
| SOXX previous five **completed** days >−5% | 504 | 99 | 33 | +0.0357% | **−0.4002%** |
| Both SOXX 5m >=0 and prior-five not weak | 478 | 95 | 31 | +0.0325% | −0.4909% |

For fair comparison, the day-equal metric averages over the **same baseline alert dates** with zero modeled return on a date when a filter vetoes all buys; it is not an average limited to selected winning dates. A separate equal-weight-per-signal metric is in structured JSON.

**Finding:** A previous-five-day weak SOXX veto improved the *later* modeled drawdown by 0.2566 percentage points per baseline alert day, but reduced the earlier result by 0.0503 points and **excluded 51 of the 150 baseline major-winner signals** (also vetoing 7 of 40 eventual major decliners). A short recent SOXX acceleration filter worsened later returns. This remains retrospective, correlated, and does not justify automatic buying or replacing V1.

## Track B — Following-five-minute confirmation before acting on broad downside warnings

Baseline union combines original strict previous-close weakness, completed premarket sector breadth, and first-hour reversal. It detects **200/209 major declines**, misses **9**, and generates **806 other warnings** (including 37 eventual >=5% winners). Original earliest severe warning is **November 13, 2025, 04:20 ET**.

At the original warning, keep the **WATCH** signal immediately. For hypothetical SELL permission, require one more entire completed five-minute bar and either stock falling at least 0.10 pp of prior close, sector SOXX nonpositive for 5m, or both. This creates a five-minute minimum delay and is not a synthetic-stop activation.

| SELL confirmation after 5m | Serious-loss hits / 209 | Nonmajor warnings | Eventual >=5% winners warned | Mean bounded sale benefit vs following regular open |
| --- | ---: | ---: | ---: | ---: |
| Original immediate union | **200** | **806** | 37 | **−0.0824 pp** |
| SOXX following 5m <=0 pp | 134 | 450 | 21 | +0.1205 pp |
| Stock following 5m <=−0.10 pp | 92 | 311 | 14 | +0.1874 pp |
| Stock and SOXX following 5m <=0 pp | 96 | 352 | 13 | +0.2757 pp |
| **Stock AND SOXX following 5m <=−0.10 pp** | **75** | **231** | 10 | **+0.6615 pp** |

The strict confirmation removes 575 nonmajor warnings and improves the **conditional** historical sale-benefit mean. However, it also **misses 125 serious-loss stock-days previously warned**, including abrupt crashes where a five-minute delayed confirmation may not arrive before the damaging move. Preopen warnings fell from 674 to 173; **preceding-evening warnings from 60 to just 9** (these are all warnings, not necessarily major-loss hits). The earliest serious-loss qualifying confirmation is **November 13, 2025, 09:45 ET** — far later than the original warning at 04:20.

For the strict confirmation, the average modeled sell benefit versus the following open was +0.3465 pp in the earlier period and +1.8293 pp in the later period. **These are selected-signal averages, not proof of greater overall account returns or risk control**. The primary research problem remains preventing severe losses without filtering away warnings until after the sell would matter.

## Daily outcome auditing and integrity

The command below generated a **2,244-row** local complete daily audit at `/tmp/v2-run10-daily-audit.json`. It includes **all** covered stock-days, including nontriggers, close outcomes, regular-session extremes for outcomes only, original first alerts, hypothetical next-open results, new confirmed warning timestamps and entry-veto decisions. Intraday lows/highs are **outcomes only**, never inputs to any earlier signal. No broker orders were placed.

Run in an isolated clean research environment with existing read-only files at the exact `/tmp/semis_*` paths:

`python3 -m research.v2_causal_entry_sell_confirm --output /tmp/v2-run10-causal-results.json --audit-output /tmp/v2-run10-daily-audit.json`

**152 offline research unit tests passed**, including nine new tests for fixed previous-close reference, overlapping time windows, five-minute causality, and unavailable observations. Source: `research/v2_causal_entry_sell_confirm.py`; tests: `research/test_v2_causal_entry_sell_confirm.py`; structured summary: `docs/RESEARCH_2026-11-09_V2_CAUSAL_ENTRY_SELL_CONFIRM_RESULTS.json`.

## Unresolved evidence and next step

Full one-minute **SIP/BOATS historical NBBO quotes, bid/ask size, latency and fill evidence**, synchronized timestamped QQQ/futures/earnings/news, independent sector datasets, and matched V1 broker executions are not available in this replay. These are material blockers to claiming improved executable profitability, preceding-evening crash protection, or superior V2 performance versus V1.

**Do not deploy an automatic sell, live stream-to-order connector, or BUY selection change based on these results.** Preserve production V1, broker state and existing holiday gates. Next test realistic quote-level rejections, overnight gaps and false-positive costs using point-in-time records and cross-sector holdouts.