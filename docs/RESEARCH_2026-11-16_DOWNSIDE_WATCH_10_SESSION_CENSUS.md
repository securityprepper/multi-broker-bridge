# November 16, 2026 — R1M/V2 research-only downside forward check

**Disposition:** No broker action, production release, alert or strategy-parameter change. **No positive edge established.** Do not circulate as a profitable signal or emergency alert. This isolated research record is intentionally not an owner notification.

## Holiday and data provenance

On November 16, 2026, a live root-owned `/var/cache/securityprepper-holiday/task-gate.json` validation using the production holiday gate reader confirmed `schema_version=1`, `status_valid=true`, revision 2, America/Chicago, current `published_at` within the 150-second interval, `valid_until` in the future and `paused=false`. The task did not rely on a superseded November 13 gate or infer that the V2 shadow recorder's separate legacy holiday-cache fix had been deployed.

Data is **GET-only authenticated Alpaca SIP** `1Day` prior/closing reference and completed `1Min` RTH trade bars; there are **no contemporaneously verified broker executable bids/asks, spread, fill costs, news first-seen timestamps, live arrival timestamps or actual trades** for these hypothetical watch signals. The script first validates the fresh local root holiday gate, never contacts a broker endpoint, never sends Pushover, and never changes service units. The earliest observation time recorded is a theoretical finished one-minute bar time, not verified news/data ingestion.

## Completed November 16 daily two-sided census

The universe contained 227 curated stock and ETF symbols; 225 had complete November 13/November 16 daily close pairs, with zero provider-failed symbols. Among the selected semiconductor, gold-miner, energy, finance, industrial, healthcare, technology, cybersecurity and AI-infrastructure equities, **53 closed at least 3% below** the prior RTH close and **zero closed at least 3% above**. Of the 53 large decliners, 42 had at least one completed one-minute bar meeting both existing *overlapping* weakness criteria (down at least 2.5% from the prior close **including** a loss of at least 1.0 percentage point over the latest 15 minutes); 11 did not. Do not call a missing qualifying price threshold a pipeline defect.

In a **single market-day cross-sectional cohort**, 47 weakness watch marks had a next-15-minute trade-close observation; 41 were lower, but only 16/47 were lower at 60 minutes. These heavily correlated, post-selected observations are **not** a robust 87% predictive hit rate and cannot establish a profitable or executable short, avoid, or exit.

## Frozen-threshold ten-session historical cross-check

The independently coded fixed rule was applied without tuning to **32 preselected symbols**: seven ETFs (SOXX, GDX, XLE, XLF, XLI, XLV, IGV) and fixed same-sector peer anchors, with software anchors CRM/NOW/ADBE for IGV. Ten regular trading dates from November 3 through November 16 were observed, with no missing day-pairs or provider-failed symbols. The rule produced 69 distinct first-watch symbol-day events over nine sessions (November 11 produced no event).

| Future trade-close horizon | Lower after the watch | Denominator | Descriptive rate |
|---|---:|---:|---:|
| 15 minutes | 41 | 69 | 59.4% |
| 60 minutes | 39 | 69 | 56.5% |

These are **retrospective completed-bar outcomes**, not broker fills or a genuinely untouched 20–30-session prospective holdout. ETF and peer events are strongly correlated and must not be treated as 69 independent experimental trials. No real bid/ask entry, slippage/fees, broker execution, matched downside protection or net P/L was verified. This outcome is inadequate for the owner's 80%-plus after-signal predictive criterion or any after-fee profitable edge. **Retire the price-only individual-weakness threshold as a standalone alpha proposition; preserve the existing internal safety/risk-watch criterion and all V1 safeguards.** Do not spend future runs retuning this failed family.

## Separate broker/account verification

Read-only Alpaca PAPER GET of one identified account, fingerprinted rather than exposed, found **zero FILL activities since November 13** at the observed run time. This is *one account*, not proof that other Alpaca PAPER accounts or unlinked strategies had no fills. The repaired R1M Percona executor and R1M audit remained successful; no R1M PAPER attempts were recorded in the Percona ledger. After-cutoff suppressed R1M candidates are not admissions or fill evidence. Recommendation Audit retains sole notification ownership for newly closed recommendation-linked trades. No new broker-safety failure or owner-actionable production blocker was verified.

## Archived isolated research

- `research/v2_20261116_downside_anchor_10session_check.py` — immutable-as-record methodology / replay code, holiday-gated GET-only.
- `research/v2_20261116_downside_anchor_10session_results.json` — exact 10-session dates, symbol set, first completed-bar signals, future marks and missing-data flags.
- Additional comprehensive November 16 227-symbol day census retained on www3 under `/tmp/v2-trading-strategy-research/research/v2_20261116_completed_day_downside_watch.json`; not a deployment artifact.
- The full V2 frozen forward shadow 11/12, 11/13 and 11/16 remains in root host's research-only sealed files, subject to its separate local holiday-cache provenance limitations. The November 16 market result is not a new strategy GO.

**Next work:** move to genuinely different independently timestamped causal information rather than continuing price-only weakness/stop/reentry parameter tuning. Retain the separate 20-day real broker fill/after-fee prerequisite before any execution parameter recommendation.
