# 2026-11-16 22:30 CT — V2 read-only research, no forward GO

**Outcome:** No independently verified profitable after-fee forward strategy. No live/PAPER order, alert, rule, service, timer, or production-source changes.

## Holiday status
On `www3` the root-owned `/var/cache/securityprepper-holiday/task-gate.json` was directly validated at 22:33 CT: `schema_version=1`, `status_valid=true`, `calendar_revision=2`, `calendar_coverage_ok=true`, `timezone=America/Chicago`, unpaused, `published_at=22:33:03 CST`, `valid_until=22:35:33 CST`, `next_check_at=2026-11-20 16:07 CST`. All validations were at this invocation; no historical cache was reused as a current decision.

## New opportunity-cost diagnostic: historical 3,809 event pairs vs SPY

Added an isolated script at `/tmp/v2-trading-strategy-research/research/v2_20261116_2230_preearnings_spy_opportunity_cost.py` and immutable research result `v2_20261116_2230_preearnings_spy_opportunity_cost.json`. It fetched only split-adjusted daily SIP `SPY` historical bars via an authenticated Alpaca **market-data GET**, matched each original Nasdaq retrospective earning event by its existing `prior6_day`, `prior11_day`, `prior16_day` and `last_pre_earnings_close_date`, and compared the existing 5/10/15 trading-session **CLOSE** returns against same-window SPY closes. No missing SPY pairs, 3,809 distinct symbol/year-date events, 16 calendar-week clusters.

| Return window | Ordinary-stock events outperforming SPY | Mean excess vs SPY | Tracked sector events outperforming SPY (138 event instances) | Tracked-sector mean excess |
|---|---:|---:|---:|---:|
| 5 sessions | 2,117 / 3,809 (55.58%) | +0.7112 pp | 56 / 138 (40.58%) | -0.8694 pp |
| 10 sessions | 2,202 / 3,809 (57.81%) | +1.4951 pp | 37 / 138 (26.81%) | -4.8630 pp |
| 15 sessions | 2,218 / 3,809 (58.23%) | +1.6937 pp | 35 / 138 (25.36%) | -7.5255 pp |

A 2,000-draw calendar-week cluster bootstrap for the 5-day *mean excess* across all events gave a 95% interval of **[-0.5607, +1.6986] pp**, crossing zero **before costs**. This is a new descriptive benchmark comparison, not a statistically secure return edge. The 138 sector *event instances* are not the same universe/sample selection as the separate prior one-event-per-sector-symbol 98 replay. Never confuse the two. No market-order or limit-fill price, no noon day-before exit, no spread, fees, GTC stop, issuer-confirmed release or first-seen estimate revision is evidenced. SPY shares are not a risk-free market-neutral hedge.

## New prospective snapshot provenance

Created read-only, O_EXCL, mode 0444 first local research archive `/tmp/v2-trading-strategy-research/research/pre_earnings_forward_baselines/2026-11-16_223600_CT_initial_nasdaq_consensus.json` with 171 symbol/fiscal-quarter/year deduplicated observed Nasdaq EPS consensus values from the existing 20:04 CT collector source. SHA-256: `106056a0204597d5ed883faec92e43e8c0155bda48aba07a8dee87300dbeca33`. It explicitly records collector as-of versus the **later** first research archive time; zero issuer-confirmed earnings dates, zero independent original estimate-observation proofs. These values CANNOT be backdated into historical EPS revisions. Future comparisons require a genuinely subsequent independently recorded observation and unchanged quarter/share basis. Source `latest.json` remains unchanged. No active collector changes.

## Broker ledger and intake checks

The authorized Alpaca PAPER account was checked again with a separate bounded **GET-only** unique FILL activity and partitioned order-window inventory. There remain 277 distinct fill activities from Oct15, on only four distinct filled days (November 9–12), 244 labeled MBB and 33 FDR; no newly recorded fill activity, no missing `order_id` links in that account's bounded window. The gross FIFO closed-lot fragments remain **-$272.36**; no broker-confirmed after-fee P/L, no attribution of each exit cause, and no authority to conclude about other PAPER accounts. The independent Percona `sp_paper_rec_intents` and `sp_paper_rec_events` tables were empty at this check, while `sp_notes_recommendations` had 96 older unauthorized review-only entries, newest from Nov 6. Do not count these as new executable orders or report an unchanged intake blocker. R1M's dedicated Percona ledger recorded no POST attempts; no new exit/commissioning authority is inferred.

## Research decision

Retain the existing guards, 13:15 entry cutoff, 13:40 flat objective, news rule (two local calendar dates), 20 distinct broker-trading day minimum, and genuinely untouched forward holdout. Do not promote the historic SPY-relative descriptive difference to a buy strategy. Recommendation Audit exclusively announces newly closed recommendation-linked PAPER positions. Further work should wait for original independently timestamped issuer-confirmed release dates, same-quarter estimate revisions, native ask/bid noon exits and fill/fee records. No user notification warranted by this run.
