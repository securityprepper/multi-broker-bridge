# November 11, 2026 — all-Alpaca-PAPER post-exit completed-minute diagnostic (V2 research only)

## Scope and provenance
This is an independent *incremental post-exit observation study*, **not** a new strategy, a release candidate, an executable backtest, or a Recommendation Audit duplicate. Input is the locally retained read-only authenticated Alpaca PAPER broker order/fill round-trip cohort collected earlier on November 11: **60 distinct completed positions from one authenticated PAPER account** (51 MBB, 9 FDR), spanning **three** trading sessions (November 9–11, Chicago time). The broker account identifier was unavailable in the bounded source. The previous broker activity-to-order reconciliation avoids counting partial FILL activities as additional round trips. No sector/rebound/recommendation-linked cohort is assumed to be absent from other account IDs or unobserved sessions.

Code: `research/v2_all_paper_postexit_completed_1m_20261111.py`, with nine independent synthetic tests in `tests/test_v2_all_paper_postexit_completed_1m_20261111.py`. The live production checkout, broker state, timers, and V1/LIVE protection settings were untouched. No HTTP, broker position or order action is invoked by this script.

## Newly measured post-exit direction, NOT executable P&L

For each actual **filled exit**, use only later full SIP one-minute trade bars. The last evaluated candle must have completed **after** the broker exit; the exit-containing bar is excluded. Every minute between the first after-exit bar and horizon must be present. The metric is the later completed trade-close mark minus the **actual filled sell price**, times the actual paired share quantity. It measures subsequent price movement, not a plausible guaranteed limit or market fill. Missing bars and horizons at/after the 13:40 Chicago hard flat are UNKNOWN, never wins. A quoted 0.30% hurdle below is an illustrative magnitude threshold; it does not establish that spreads, commissions, slippage or a later bid allowed this amount.

| Cohort, horizon | Usable / population | Later mark higher / lower / equal | Higher by ≥0.30% | Sum of mark-minus-filled-exit × shares |
|---|---:|---:|---:|---:|
| All, 2m | 50 / 60 | 30 / 17 / 3 | 4 | +$55.90 |
| All, 5m | 47 / 60 | 33 / 14 / 0 | 7 | +$118.70 |
| All, 10m | 44 / 60 | 27 / 15 / 2 | 10 | +$98.40 |
| All, 30m | 40 / 60 | 23 / 16 / 1 | 17 | +$133.09 |
| MBB, 10m | 36 / 51 | 19 / 15 / 2 | 6 | +$55.45 |
| FDR, 10m | 8 / 9 | **8 / 0 / 0** | 4 | +$42.95 |
| MBB exits ≤10m after entry, +10m | 15 / 22 | 7 / 6 / 2 | 2 | +$35.65 |
| MBB exits ≤10m after entry, +30m | 14 / 22 | 9 / 5 / 0 | 6 | +$86.13 |

The key new distinction is that **FDR's November 9 premarket scheduled exits**, already shown in a separate journal-source audit to be triggered by the exit schedule, were followed by higher trade-close marks **at +10 minutes in all eight evaluable FDR positions**. This is a bounded one-day association, not a trading advantage; holding could still incur a larger drawdown, a wider spread, an unfilled sell limit, or a subsequent decline. The ninth FDR position lacks complete one-minute bars for that window. Conversely, only **7 of 15 evaluable MBB ultra-rapid exits** had a higher ten-minute later mark, while six were lower and two equal. An across-the-board mandatory delay is therefore *not supported*.

At +10m the 16/60 unevaluable trades comprise 13 missing-contiguous-minute paths and three already at/after the hard flat boundary. The 10m and 30m cohorts have different coverage, so they cannot be treated as matched outcomes or a head-to-head policy experiment.

## Methodological limits and non-eligibility
- Actual exit cause remains UNKNOWN for 48 MBB limit-order exits; no journal entry may be retroactively synthesized from trade price. The separate earlier audit attributed nine FDR exits to the scheduled morning exit, and three MBB market exits to the 13:40 flat period.
- Original BUYs in this historical inventory have not been retrospectively issuer/SEC-news-cleared; record `NEWS_UNKNOWN` and treat as outcome-only historical controls, not new eligible recommendations.
- A SIP completed-minute *trade* close is neither SIP NBBO bid nor executable size. No hypothetical sale at these later marks is claimed. Actual fees and partial-fill uncertainty remain material.
- Historical observations use only three dates and are already research-exposed. Do **not** claim a 20-day or untouched out-of-sample validation, optimize stops/targets based on this result, relax the negative-news veto, or authorize PAPER/LIVE orders.
- The research collector's earlier full-session continuity requirement was too restrictive for independently diagnosing a 2- or 5-minute **post-exit** move. This script checks only the relevant post-exit window, preserving UNKNOWN status for any gap and honoring the 13:40 time limit.
- No input file includes verified broker account IDs across multiple accounts; one authenticated paper-account scope cannot establish completeness of **all** Alpaca PAPER accounts.

## Reproduction and next evaluation
Run the published tests with `PYTHONPATH=. python3 -m unittest tests.test_v2_all_paper_postexit_completed_1m_20261111` or unittest discovery. Run the research-only script against an authorized **private** local broker-lot/SIP cache using `--input PATH --output NEW_PRIVATE_PATH`. Do not commit raw licensed bars, order UUIDs, API keys, account IDs, or private caches. Repeat on independently observed sessions, join durable decision-reason to actual broker filled-order UUIDs, recover genuine as-of executable quote/spread/fees where supported, and evaluate adverse excursions and after-fee broker-like fills over 20+ distinct days before any strategy-change decision.

**Decision:** no change to active V1 or broker orders, no V2 PAPER GO, no predictive BUY alert.
