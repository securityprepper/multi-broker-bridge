# November 10, 2026 — midday RTH small-loss churn vs MBB PAPER verified fills (V2 research only)

**Frozen GET-only inventory as of 12:38:55 CST (18:38:55 UTC)** on authorized www3. The snapshot had broker_verified=true, recent_orders_complete=true, paper_only=true and zero open broker orders. This is a bounded intraday observation, NOT the 13:40 CT closeout or after-fee result. No orders were submitted by this research.

## Independent RTH outcome and risk finding

From filled MBB-tagged **regular-session** broker orders on November 10 (Chicago): **12 BUY, 9 SELL, 9 completed round trips; 2 gains and 7 losses; -$68.15 gross realized PAPER P&L**, before commissions, data and any other costs. The seven losing trades individually exited at only **-0.166% to -1.113%** from their actual filled entry price; all seven were shallower than the -2.5% *stock weakness research threshold* and four sold **within six minutes** of purchase. Losing-lot proceeds total -$81.93 gross and two winning closes total +$13.78; no claim these losses were caused by any particular exit rule because exact V1 decision rationale is not recorded in broker fill data.

Three PAPER broker positions remained open: **COP 14, HPE 42 and ETN 5 shares**. Those quantities match today's still-unclosed MBB-tagged BUY order quantities. An aggregate broker-symbol quantity match, however, **does not establish exclusive strategy ownership** when another writer could trade the same security; independent FILL UUID ownership proof remains required for a deployment-level assertion. No same-symbol other-writer RTH filled order appeared in the bounded snapshot. No unrealized results are asserted.

The distinction matters: the installed >=2%-BID-profit routine exit gate applies to *premarket* sells. Today's RTH exits at shallow losses therefore do not by themselves prove a violation of that premarket policy. They do demonstrate that RTH anti-churn research remains important and must be evaluated against a causal hold-to-13:40 control with stops, fill latency and realistic spread rather than hindsight wins.

## Separate executor diagnostics

Read-only 11:30–12:30 CST executor journal: **70 complete scans, 31 repeated BUY_WATCH observations**, including **25 NO_FRESH_BID_ASK** and **5 PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY** skips. HPE was submitted during this hour and independently verified filled in the broker inventory; ETN was also verified as a later 12:33 fill. Counts are repeated candidate appearances, not 31 executable missed trades. The quote skip subtype is unknown without contemporaneous raw quotes; the cross-session tracking restriction remains unresolved and must not be fixed by clearing historical tracking indiscriminately.

## Reproducible research-only analysis

- Pure offline source: `research/v2_rth_small_loss_census_20261110.py`, accepts a previously retrieved verified PAPER broker inventory JSON. **No network, broker commands, credentials, cash details or live modifications.**
- **11/11 unit tests passed on www3** in isolated scratch `/tmp/v2-run12-rth-churn-20261110`: FIFO share arithmetic, local-time RTH boundaries, over-sell/duplicate IDs, cross-writer ambiguity, future fills, broker open orders, verified-snapshot gating and position mismatch semantics.
- Redacted, immutable output: `research/results/v2_rth_small_loss_snapshot_20261110.json`. No account identifiers or client order IDs exported. It explicitly records **exclusive_strategy_ownership_proven=false, exit_reasons_known=false, fees_included=false, end_of_day_outcome=false**.

## Next evidence and GO boundary

Obtain the 13:40 CT mandatory liquidation and 14:00 CT broker verification; reconcile all fills by FILL UUID, strategy order UUID and position ledger. Capture as-of quote/exit reasons so the short-loss exits can be compared with a feasible protected hold policy, not merely historical close prices. Continue 20+ independently untouched forward days with sealed, explicit UP/DOWN/ABSTAIN classifications (today's existing V2 shadow files are feature-only); score **after-signal** returns, costs, false warnings and missed large winners/losers separately. November 9 03:18 CT AMD skip remains unproven, and the 03:18 1m candle must not be treated as complete at 03:18:40. None of the new research qualifies a strategy for automatic PAPER or LIVE trading.

**No active V1 PAPER/LIVE monitors, broker orders, production checkout/database, timers, IBKR Gateway, owner entry cutoff (13:15 CT), mandatory 13:40 flatten / 14:00 verification or holiday rule were modified.** Cached holiday status revision 2 is unpaused strictly before November 13, 2026 16:13 CST absent calendar edits; revalidate at its boundary.
