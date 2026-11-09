# V2 causal preceding-evening gap risk versus upside — November 9, 2026

**RESEARCH ONLY. No orders, streaming executor, broker-native stop, V1 monitor/timer, or production checkout changes.** Holiday cache: validated unpaused America/Chicago revision 2; strict expiry November 13, 2026 16:13 CST absent calendar invalidation.

## New two-sided independent overnight test

This study asks whether an alert **the preceding evening** could actually have warned about tomorrow's extreme open. It uses the existing 52-week split-adjusted Alpaca SIP 5-minute **bar** files for AMD, MU, SNDK, SOXX, NVDA, AVGO, WDC, TSM, INTC. Only 16:55 ET (completed at **17:00**) and 18:55 ET (completed at **19:00**) bars can issue a warning, relative to the same day's already completed 15:55 RTH bar close. SOXX must move >=0.5% and at least four available peer stocks >=0.75% in the same direction with stock >=1.5%, **or** the target stock alone must move >=2.5%. Symmetric rules detect upward and downward gaps. These are predeclared hypotheses, not tuned using next-session labels.

Each signal also records the cumulative return over the **last five completed RTH sessions only**, including the session that has completed by the evening alert. Signals are withheld if that history is unavailable. All joins to next-session opening, closing, and next-bar prices occur only **after** making the as-of decision; tests alter future opening outcomes and verify the alarm stays unchanged. The original **-2.5% total including -1.0 percentage point in last 15m** strict conjunction is separately measured and never modified or converted to 3.5%.

The audit includes **all 2,244 previously matched semiconductor stock-days**, not just signal days; 2,232 have the complete prior-five close feature. A broader raw clock join adds 39 initial stock-days lacking the original baseline; they were explicitly excluded to keep this comparison identical to prior reports. Both next opening and next closing results are available for 2,244. There are **87 next-opening gaps down >=5%, 94 gaps up >=5%, 209 next-day closing declines >=5%, 254 gains >=5%** (all relative to the preceding close). The separate 250-sector-session baseline remains **118 positive / 83 negative / 49 mixed**; 251 session-calendar entries should not be conflated with those 250 labeled sessions.

## Preceding-evening warning sensitivity and false alarms

| As-of ET | Down severe gap hits / 87 | Other down warnings | Up severe gap hits / 94 | Other up warnings | Evening bars observed / 2,244 |
|---|---:|---:|---:|---:|---:|
| 17:00 | 14 | 26 | 22 | 41 | 2,140 |
| 19:00 | 25 | 47 | 33 | 72 | 2,067 |
| **Either evening (earliest alarm)** | **25** | **54** | **37** | **86** | — |

The union **missed 62 of the 87 major down gaps and 57 of 94 major up gaps**, even after having the completed evening bar evidence. Among 25 predicted major down gaps, **18 were alerted before the individual stock was already down 5% that evening**. Among 37 predicted major gap-ups, 29 were alerted before already up 5%. This is still not a verifiable *executable* escape or entry: the warning may arrive into thin after-hours conditions.

Earliest true severe-down alarm: **AVGO on December 11, 2025 at 19:00 ET**, for a severe down gap the next regular opening. Earliest 17:00 true downside alarm: **INTC on January 22, 2026 at 17:00 ET**. Earliest true upside alarm: **AMD on November 11, 2025 at 17:00 ET**. Relative to the next 09:30 ET open, the preceding-evening alerts have ~14.5-16.5 hours of clock lead time on typical weekday nights (longer on weekends), not automatically sufficient **liquid trading** lead time.

The original strict 2.5% / overlapping 1.0pp last-15m signal appeared only **4 times at 17:00 (1 next-day major-down gap, 3 other)** and **6 times at 19:00 (1 major, 5 other)**. The strict signal cannot by itself solve preceding-evening gap detection; however it must remain an independent candidate rather than be replaced by breadth.

## Does avoiding overnight holding actually help?

Use **the next observed five-minute bar's opening price** after the alarm as a *scenario mark*, deduct an assumed **0.15 percentage-point** friction, then compare to the following RTH open. This is not NBBO, spread, eligible order routing, size, fill probability, broker stop, or actual P&L. Every held position is hypothetical; a user could already own different names.

At the earliest qualifying evening alarm per stock-day, the **DOWN hypothetical sale versus next open averages -0.451pp across all 79 warnings**. Its 25 realized major-gap hits average **+4.443pp avoided**, while 54 other warnings average **-2.716pp**, primarily foregone rebounds. Thus a strategy that only sells the eventual true hits would cheat by using the future outcome. On the upside, early BUY versus next open averages **+0.386pp over 123 warnings**, but splits into **+4.231pp** for 37 realized major-up gaps and **-1.268pp** for 86 other warnings.

The important chronological instability: at **19:00 ET**, mean DOWN early-sale benefit was **-1.235pp in the earlier period** versus **+1.196pp in September–November**. The opposite directional buying rule produced **+0.564pp earlier**, **-0.679pp later**. Do not select the better later regime after observing its result; no locked out-of-sample profitable rule emerged.

Material misses include the **June 23, 2026** severe next-opening declines in SNDK (-11.70%), MU (-10.84%), WDC (-9.15%) and INTC (-7.92%) with **no preceding-evening signal** in this candidate. These remained potentially detectable by a separate next-morning premarket system, but did not receive an advance warning from this fixed evening hypothesis. Prior research's after-the-open 209/209 severe-close hindsight coverage must never be presented as preceding-evening or avoidable-gap protection.

## Why this changes research priorities

This demonstrates a practical failure mode: symmetric, causal evening-bar momentum explains some overnight gaps but **cannot provide reliable prior-evening risk control** with these two snapshots. Increasing 19:00 coverage over 17:00 also raises false warnings and the benefit of selling reverses across chronological cohorts. Immediate WATCH remains separate from any trading recommendation.

The next required data are authenticated **point-in-time full SIP/BOATS NBBO bid/ask and bid/ask size**, broker order eligibility, actual PAPER fills, timestamped company earnings/guidance and news, economic release times, one-minute observations and SOXX/QQQ/futures histories, followed by an independently held-out non-semiconductor sector sample. The prior protected-credential historical quote retrieval was blocked by the environment's safety checks; this run did **not** retry it or access secrets. The main production checkout remains dirty with unrelated changes and the divergent local V2 checkout remains untouched.

## Reproduction

Use the two previously existing read-only split-adjusted SIP bar JSON files plus `/tmp/v2-run10-daily-audit.json` as a fixed universe list, from an isolated scratch checkout:

```bash
python3 -m research.v2_evening_next_open_gap --results /tmp/v2-evening-summary.json --audit /tmp/v2-evening-daily.json
python3 -m unittest discover -s research -p 'test_*.py' -q
```

**198 offline tests passed** on an isolated copy of the earlier V2 research scratch tree (188 existing + 10 new deterministic tests). Output rows and summary were written under `/tmp/v2-run14-evening-gap/`; only new source, tests, JSON summary and this report are intended for the canonical research branch. No new broker permission or host trading action is authorized.
