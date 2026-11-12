# November 12, 2026 — Alpaca PAPER completed-fill hold-time loss concentration (V2 research only)

**New observation, not a causal exit-policy finding or an approved parameter change.** Recomputed solely from the previously authenticated, single-account Alpaca PAPER filled-order round-trip ledger, joining unique broker **entry/exit order UUIDs** and using actual filled prices, quantities, and timestamps. No raw FILL activity is counted as an additional trade; no sell acceptance is treated as a fill. Historical account identity and full UUIDs are not published. Scope: **60 completed round trips over Nov 9–11, 2026 (40/13/7)**, of which **MBB 51 / FDR 9**. This is not a census of other Alpaca accounts. Neither commissions nor data fees were available.

## New duration-cohort result, actual PAPER fills only

| Actual filled entry-to-exit hold | Completed pairs | Winning / losing / flat | Gross realized PAPER dollars, before unknown fees |
| --- | ---: | ---: | ---: |
| <=2 minutes | 4 | 0 / 4 / 0 | -$18.07 |
| >2–5 minutes | 9 | 1 / 8 / 0 | -$58.27 |
| >5–10 minutes | 9 | 0 / 9 / 0 | -$52.42 |
| >10–30 minutes | 25 | 7 / 18 / 0 | -$146.61 |
| >30 minutes | 13 | 6 / 6 / 1 | -$3.97 |
| **All** | **60** | **14 / 45 / 1** | **-$279.34** |

**Within the same MBB source**, rather than confounding it with FDR's independently run rebound strategy, the **22 holds <=10 minutes produced only 1 winner / 21 losers and -$128.76 gross** (median filled-price return **-0.3077%**). The **29 MBB holds >10 minutes** had **13 winners / 15 losers / 1 flat, -$32.36 gross**, median **-0.0593%**. The short-duration group represents **22/51** MBB trips but **79.9%** of MBB's **-$161.12** three-day net gross loss (the ratio describes contributions to a net sum, not an independent loss-risk probability). FDR had **0/9** trips closed within 10 minutes, and all nine FDR trades lost money; do not combine the two source cohorts when interpreting MBB rapid exits.

This rapid-loss association occurred on each of the three dates, not just Nov 9: Nov 9 **12 losses/12 rapid MBB, -$64.68**; Nov 10 **5/5, -$55.32**; Nov 11 **4 losses/5, -$8.76**. By entry session, the 22 rapid MBB round trips were **3 overnight (3 losses), 4 premarket (4 losses), and 15 regular-hours or later (14 losses)**. The rapid-exit loss pattern therefore is not confined to overnight illiquidity, although sample sizes remain small.

Starting symbols remain examples, not inferred trigger evidence: actual MBB AMD Nov 9 held 1.98 minutes and lost $2.80; MBB CARR Nov 11 held ~2.00 minutes and lost $1.44; MBB KMI Nov 11 held 5.07 minutes and lost $0.63; MBB MCHP Nov 11 held 22.92 minutes and earned approximately $8.09 gross. These are **actual broker-fill outcome comparisons**, not alternative executable hold results.

## Interpretation and hard limits

Holding duration is an **outcome of the exit algorithm and of market conditions**, not a randomized treatment. Comparing short with long actual holds cannot establish that forcing a 5/10/15/30-minute minimum hold would improve after-cost outcomes; such a rule may simply retain serious losers. The independent exact broker-order UUID audit found **0/48** usable contemporaneous exit reasons on ordinary MBB sells; three separate forced 13:40 sells are identified, but not the cause of ordinary rapid exits. Therefore none of +1% target, -1% loss watch, 0.5% trailing reversal, two falling bars, emergency stop or trend-disqualification can yet be ranked by trigger frequency. Historical code revisions cannot fill that evidentiary gap.

The previous strict quote study had fresh eligible SIP quotes at **62/120 filled legs, 13/60 complete pairs**. The subsequent wider-window study found **19 stale quotes among 25 previously null five-second legs**, plus six without a quote in five minutes, but none of those 25 added a <=1.5-second eligible quote. Thus the actual fills substantiate realized gross dollars above; **alternative exit fillability, fees, max adverse/favorable executable excursions and a 20+ untouched-day heldout outcome are not verified**. Historical issuer-specific adverse-news clearance is unknown: this is descriptive outcome research, not a BUY eligibility assessment.

**Research decision: NO GO** for longer minimum holds or different stops/targets. Continue read-only versioned exit-decision receipts tied to actual broker order UUID and final fill UUID, fee/quote-path capture, and >=20 distinct untouched days. Do not report this as recommendation-linked trade scoring; Recommendation Audit retains that role. Do not alter active V1 PAPER/LIVE, IBKR, order safety, holiday gate, 13:15 admission stop, 13:40 flatten, or any timer.

## Reproduction

Offline-only `research/v2_paper_hold_cohort_20261112.py` consumes the restricted already broker-verified private 60-pair dataset; validates distinct filled entry/exit order UUIDs, Chicago-session timezone, price/quantity integrity and nonnegative hold durations; prints **only aggregate statistics**, not IDs. `tests/test_v2_paper_hold_cohort_20261112.py`: **16/16 offline tests passed** on the isolated www3 scratch checkout. Structured sanitized result: `research/results/v2_paper_hold_cohort_20261112.json`. No network or broker operations are performed by this script, and no live source or active timers were changed.
