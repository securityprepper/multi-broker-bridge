# V2 as-of peer warning concurrence versus first-stock BUY admission — November 9, 2026

**OFFLINE RESEARCH ONLY.** The configured holiday cache was unpaused (America/Chicago revision 2), valid strictly before November 13, 2026 16:13 CST absent a known calendar edit. No existing V1 PAPER/LIVE monitor, broker order, production checkout, security timer, or scheduled task was changed.

## Evidence and critical methodological distinctions

The replay examines the existing **2,244 semiconductor stock-days** (nine stock/ETF symbols) over the 52-week split-adjusted five-minute SIP bar sample through November 6, 2026. It includes **209 major losses (previous-close to close <= -5%)** and **254 major gains (>= +5%)**, including all nontriggering days. The previously classified **250 semiconductor sector sessions** remain **118 positive / 83 negative / 49 mixed**. An underlying session-calendar list has 251 entries; do not confuse that with the 250 independently classified sector outcomes.

The input daily audit `/tmp/v2-run10-daily-audit.json` was regenerated in prior research from timestamped observations. This study only uses **as-of timestamps of existing premarket or early-session alerts** and **fully completed price candles** for decisions. Previous-five-session features are not used in the new candidate rules; prior-five evidence from earlier analyses remains separate and was not replaced. Future close labels, next-bar prices, next opening prints and eventual intraday extrema are scored *after* signal generation. The original 2.5% previous-close decline **including** 1.0 percentage point over the prior 15 minutes remains intact and is not silently replaced.

Two research tracks:
1. Preopening downside peer-alarm concurrence: after the target's first warning, require 0/1/2/3 other unique names to have warned. `sticky` retains alarms through the opening; `fresh30` rejects alarms older than 30 minutes. **The confirmed timestamp is the actual latest required peer-warning timestamp**, not retroactively the target's first warning. A first-warning ledger is not necessarily current-price breadth; alarms may have reversed, especially in sticky mode. This study never assumes an unobserved re-trigger. Always preserve immediate WATCH regardless of experimental confirmation.
2. Earlier/later first-stock-only BUY admission: keep the **same first-as-of qualifying stock per independent day**. Veto this candidate, without retrospectively selecting another, if its own warning has already fired, SOXX has already warned, or >=1/2/3 other stocks have already warned. A warning after the BUY timestamp cannot veto it. Use a common 117-day denominator with zero hypothetical profit on abstained days; 97 earlier days and 20 September–November days.

Every quoted return is an assumed **15bp friction/30bp envelope next-bar OHLC proxy**, **not** an observable NBBO fill, order-book simulation or actual account P&L. The preopen SELL score is a hypothetical early sale versus carrying to the **following** regular opening, and not necessarily a sale into an eligible overnight venue. Correlated stocks and event-level overlaps limit effective statistical sample size.

## Track 2 — Peer confirmation does not solve premarket false-alarm economics

| Premarket warning policy | Serious down hits / 209 | Nonmajor warnings | Warnings on eventual major up days | Serious-loss hits before -5% | Hits warned previous evening | Mean modeled early-sale advantage vs following RTH open |
|---|---:|---:|---:|---:|---:|---:|
| Target alarm immediately | **155** | 519 | 22 | **121** | **23** | **-0.540 pp** |
| >=1 peer, sticky | 152 | 508 | 18 | 117 | 19 | -0.540 pp |
| >=2 peers, sticky | 147 | 487 | 17 | 106 | 10 | -0.666 pp |
| >=1 peer within 30 minutes | 130 | 462 | 15 | 101 | 18 | -0.552 pp |
| >=2 peers within 30 minutes | 103 | 393 | 10 | 79 | 10 | -0.663 pp |
| >=3 peers within 30 minutes | 98 | 338 | 2 | 74 | 10 | -0.396 pp |

A 30-minute, three-peer gate reduces the raw nonmajor warnings from 519 to 338, but **loses 57 major-loss warnings**, including **47 that would have alerted before an actual -5% loss**. The small apparent improvement in its mean conditional sale advantage is still *negative*. This gate cannot replace immediate protection.

Earliest serious-loss baseline warning: **WDC, November 13, 2025 at 04:20 ET**. The first serious-loss warning satisfying **>=1 fresh-30-minute peer** is only **November 18, 2025 at 09:15 ET**. Later confirmation can erase critical overnight lead time. Even the baseline preopen alerts cannot be assumed to have prevented gaps already realized before the first observable quote.

## Track 1 — Risk-first veto for early bullish first-stock purchases

| Admission policy, identical 117 first-signal days | Earlier day-equal net | September–November day-equal net | Later buys / 20 | Big losing first-stocks retained, all periods | Big winning first-stocks lost, all periods |
|---|---:|---:|---:|---:|---:|
| First qualifying stock, unfiltered | **+0.381%** | **-0.250%** | 20 | 8 | 0 |
| No previous warning in the *same stock* | +0.250% | **+0.202%** | 10 | 1 | **4** |
| No previous SOXX warning | +0.326% | +0.048% | 9 | 0 | 5 |
| No previous other-stock warning | +0.142% | +0.203% | 6 | 0 | 15 |
| Fewer than three previous other-stock warnings | +0.232% | +0.048% | 9 | 0 | 11 |

As-of **same-stock-clear** admission avoided 7 of 8 major losing first-stock signal-days and preserved 34 of 38 major winning ones, with 73 admissions across 117 baseline days. It improved the **later** return from -0.2497% to +0.2022% per original independent signal day, *but* reduced the earlier return from +0.3806% to +0.2502%. The 10 later trades are too few to establish a profitable strategy, and this specific rule was not the winning earlier-period selector.

The stricter **zero-other-warning** rule avoided all eight major first-stock decliners but also excluded 15 of 38 major winning first-stock days; earlier day-equal return fell from +0.381% to +0.142%. Avoiding realized big losers is not equivalent to maximizing feasible, risk-adjusted returns.

**Selection integrity:** Choosing the highest historical day-equal return **only from the earlier period** would still select unfiltered first-stock admission, which subsequently loses -0.2497% in September–November. The ostensibly positive later alternatives were inspected *after* those outcomes and are not independently out-of-sample validated.

## Actionable implications and unresolved blockers

- **Keep immediate downside WATCH.** Treat peer concurrence as a second-stage *triage attribute*, never a condition for initial severe-risk warning. A moving 30-minute window explicitly loses warnings and early lead time.
- **Advance same-stock risk-first BUY veto to a separately labeled research candidate**, not an automatic buy filter. It is better than broad peer veto at preserving major winners, and was positive in both chronological periods; nevertheless the earlier-period selector would not have picked it, and the later sample is just 20 days.
- Preopen 155/209 severe-loss coverage is very different from the earlier hindsight **209/209 full-day** union, where many warnings arrive after opening; neither proves preceding-evening crash protection.
- A protected-credential quote pull proposed during this run was **blocked by the environment's safety checks before execution**. No quote dataset was retrieved, and no secret was exposed. As a result, full SIP/BOATS NBBO, bid/ask sizes, latency, extended-session limit eligibility and actual partial/unfilled outcomes remain unmeasured. One-minute feed, timestamped futures/news, other-sector 52-week samples and V1 matched fills are also missing.
- **188 offline unit tests passed** (174 existing + 14 new). The new 2,244-row daily outcome audit, preopen event audit and first-only decisions are generated as scratch JSON under `/tmp/v2-run13-*`; all can be regenerated by the committed script.

To reproduce from an isolated research checkout with the prior read-only SIP 5m files and daily audit present:

```bash
python3 -m research.v2_asof_peer_risk_buy_veto --output /tmp/v2-run13-summary.json --audit-output /tmp/v2-run13-daily.json --events-output /tmp/v2-run13-preopen-events.json --buy-output /tmp/v2-run13-buys.json
python3 -m unittest discover -s research -p 'test_*.py' -q
```

**NO V2 trading GO**: no broker-native stop, synthetic streaming replacement, limit-order executor, PAPER buy, LIVE order, V1 strategy, timer or holiday schedule was activated or altered.
