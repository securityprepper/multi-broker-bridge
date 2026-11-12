# November 12, 2026 — V2 research: active PAPER exit-source drift and reason provenance

## Scope and verified observation

This is an **authorized read-only source/journal inspection** at www3.securityprepper.com, with no PAPER/LIVE orders, service/timer modification, protective-stop modification or active source edit in this research run. The audited host's current time was November 12, 2026, 07:43 CST; the pre-existing holiday cache was unpaused revision 2, with the next strict refresh boundary November 13, 2026, 16:13 CST, absent calendar invalidation.

The systemd `trading-sector-paper-executor.service` runs `multi_broker_bridge.auto_paper --once --execute` in `/opt/securityprepper/multi-broker-bridge`. The timer was enabled and active when inspected. The production checkout was on `main`, HEAD `809ec3f` (November 7), but both `multi_broker_bridge/trend.py` and `multi_broker_bridge/auto_paper.py` were **locally modified and uncommitted**. This describes the host checkout, **not** its approval or authorization status; separate release provenance was not established.

- `trend.py` modified November 11, 19:52:38 CST; SHA-256 `eb847459672b723fdcb2c16f8017fe3848d1a41bb6899b92eef40554297195df`.
- `auto_paper.py` modified November 11, 20:25:43 CST; SHA-256 `38530c3b8ef8ab64db66e98558afd2d84556687f5049633ade784fea12935cab`.
- Structural AST audit of the currently present source: **no independent regular-session two-falling-bars exit** remains. RTH retains the separate -1% loss-watch, +1% profit-target, trailing-peak reversal, and mandatory flat paths. A two-falling-bars call remains in the distinct **premarket substantial-profit** branch. Thus, evaluating historical 2026-11-09 to 11-11 fills against today's source would conflate two different source-policy regimes. The earlier historical 9/14 compatible RTH cases do **not** prove their actual exit reasons.
- The currently present `auto_paper.py` records `exit_signal_reason` and explicitly `exit_fill_verified=False` **when reporting an accepted SELL order** with a broker order ID. This is submission evidence, not evidence that a sell filled. Actual fill UUID/time and source-account joins remain independently mandatory.
- From November 11 20:26 CST to the read-only audit, **808** `SCAN_COMPLETE` journal records contained **0 recorded order submissions**, therefore there is **0/0 prospective filled SELL cohort** on which to validate the new reason field, and no measured improved trading outcome. This executor-journal boundary cannot certify whether other independent Alpaca writers made orders.
- Independently, the periodic GET-only PAPER inventory at November 12, 07:35:01 CST reported **0 current positions, 0 open orders and 83 recent orders** in its rolling window. The 83 count must not be confused with the older 124-order bounded November 9–11 analysis or interpreted as all historical activity.

## Interpretation and next research gate

The 48 ordinary MBB sells in the historical three-session cohort still have **UNKNOWN verified decision triggers**; code compatibility and prices cannot retroactively label them. Nine FDR exit causes were separately verified as the scheduled premarket flatten. Three MBB 13:40 flatten sells had been separately verified. Earlier bounded 60 PAPER round trips have only 13 fully qualifying two-sided fill quotes, and three dates are less than the minimum 20 independent untouched sessions; none of the exit-parameter grid is executable-after-fees validated.

The **new** issue for research integrity is active-source policy-version drift and missing release provenance. Before any V1-to-V2 outcome comparison, bind each fill/order UUID to the actually deployed strategy source hash/policy revision at decision time. Verify the source edit's separate approval/release record through authorized channels; do not presume the edit was unauthorized merely because the checkout is dirty. For new SELL events, join the order-ID-bearing `exit_signal_reason` to a separately authenticated broker FILL activity, including partials, before classifying a cause. Broker account identity and all-writer coverage must be explicitly proven. Continue sealed no-lookahead prospective study until at least 20 distinct sessions and materially better SIP/BOATS executable quote coverage; do not change current V1 or LIVE.

## Reproducibility

Pure read-only source parsers: `research/v2_live_exit_source_drift_20261112.py`; offline tests: `tests/test_v2_live_exit_source_drift_20261112.py`. **8/8 synthetic tests passed** on isolated host scratch (including detection of a restored RTH independent two-bar clause and prevention of treating sell acceptance as a fill). AST parsing does not import or execute live strategy modules or call a broker. Source files, private journals, keys, broker order UUIDs and licensed quote payloads were not uploaded to GitHub.

**Decision: research-only; NO PARAMETER GO, NO BROKER/PRODUCTION CHANGE.**
