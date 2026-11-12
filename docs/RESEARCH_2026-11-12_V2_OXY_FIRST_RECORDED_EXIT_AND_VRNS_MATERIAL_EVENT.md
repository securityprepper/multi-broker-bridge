# November 12, 2026 — PAPER MBB first prospective exit-reason candidate and material-event provenance

## Authorized research boundary

Read-only observations on www3.securityprepper.com during the November 12 09:31–09:42 America/Chicago window. The trusted, previously validated holiday cache remained UNPAUSED revision 2 with next_check_at November 13, 2026, 16:13 CST; no calendar invalidation was known. Neither broker orders nor active services, source, timers, stops, or LIVE/PAPER permissions were modified. No account IDs or credentials are published. This is the independent all-PAPER research task, not the Recommendation Audit notification ledger.

## Fresh PAPER order evidence (bounded inventory)

The existing periodic broker GET-only inventory reported, as of 2026-11-12T15:40:02Z, broker_verified=true, paper_only=true, recent_orders_complete=true, one open VRNS position (40 shares), and zero broker-reported working orders. Zero working broker orders does NOT certify the absence of a commissioned software stop and this research task is not Position Check. The inventory's rolling recent-order collection is not all lifetime account activity.

On November 12, the inventory had **three filled MBB client-order-ID records**:
- VRNS buy, 40 shares at $49.09, actual broker fill 08:38:52.190787 CST.
- OXY buy, 34 shares at $57.64, actual broker fill 08:48:53.801367 CST.
- OXY sell, 34 shares at $57.81, actual broker fill 09:33:50.713050 CST.

Source attribution: both BUY events are explicitly listed in contemporaneous trading-sector-paper-executor.service SCAN_COMPLETE order arrays (broker responded pending_new at submission, not a fill). Their broker client-order IDs carry the MBB 20261112-B prefix. The OXY SELL client ID carries the corresponding MBB 20261112-S prefix. The remaining market-source cohort is not assumed flat or exhausted. FDR supplied no newly verified fill in this bounded sample.

OXY is one *newly completed* filled round trip, not a new 2/5/10/30-minute exit: fill-to-fill 44 minutes 56.912 seconds. Its actual filled-price PAPER gross = 34 × ($57.81 − $57.64) = **+$5.78 before commissions/fees**, which remain unknown. The sell filled approximately 0.634 seconds after its broker submission timestamp. Do not confuse the broker's accepted-order timestamp with the actual fill.

A contemporaneous MBB SCAN_COMPLETE journal recorded one accepted OXY SELL, with exit_signal_reason = **trailing peak reversal** and a broker_order_id. This identifies the *recorded decision reason*, not yet a fully broker-FILL-UUID-certified mechanism: the sanitized periodic GET-only inventory retains the client order ID and filled timestamp but omits the broker order UUID and individual FILL activity IDs. Therefore the strict exact UUID/activity linkage is **UNKNOWN_PENDING_FILL_UUID_JOIN**, not VERIFIED. No other prospective post-reason-instrumentation SELL was confirmed in the sampled inventory. In particular, this case does not prove which historical short-duration exit trigger dominated the prior November 9–11 cohort, nor does it prove a 1% target, -1% watch, or two falling bars. The decision source-version/hash must be recorded and checked separately, not inferred from current HEAD.

## Existing position: material event present as of original purchase

At the 09:40 CST account readback, VRNS remained held at 40 shares bought for $49.09. A previously published October 15, 2026 announcement establishes an agreed Proofpoint/Thoma Bravo all-cash takeover for **$49.75 per VRNS share**, expected to close in the first half of 2027 subject to closing conditions. Relevant independent source: https://www.reuters.com/legal/transactional/proofpoint-buy-varonis-systems-63-billion-all-cash-deal-2026-10-15/ . At the actual $49.09 PAPER entry, the simple agreement-price difference is $0.66/share ($26.40 gross for 40 shares), approximately 1.344% before commissions, time value, taxes, closing uncertainty or deal-break downside. It is NOT an executable price target or expected profit.

The issuer's November 3, 2026 Q3 release, available well before the November 12 order, reports a widened GAAP operating loss ($47.7m versus $35.9m), nine-month free cash flow of $94.8m versus $111.6m, and no updated guidance or quarterly call because of the proposed merger. Issuer release/SEC exhibit: https://www.sec.gov/Archives/edgar/data/1361113/000117184326007078/exh_991.htm . These are material, mixed company-specific facts, not proof of a currently collapsing share price or a completed acquisition. At minimum, issuer-specific pre-buy status should have been **REVIEW/WATCH ONLY** pending documented NEWS_CLEAR_ASOF and an explicit material-event assessment. The active MBB purchase path was separately observed not to demonstrate the required timestamped negative-news clearance. This audit does not claim the trade was automatically forbidden by a verified adverse headline, or that the broker-native/software stops were absent.

## Research changes and limitations

Research-only source: research/v2_exact_exit_reason_fill_join_20261112.py. Synthetic offline tests: tests/test_v2_exact_exit_reason_fill_join_20261112.py, 12/12 passing from a fresh isolated checkout. The helper fails closed unless authenticated same-account order UUID, complete filled quantity, unique FILL activity IDs, correct symbol/side, chronological records, and a nonempty recorded reason all match. An accepted SELL or a favorable price proxy never becomes VERIFIED without those independent fill records. The code is not connected to any broker and submits no orders.

Remaining required: exact OXY SELL broker UUID/individual FILL-activity join, strategy source hash at decision time, at least 20 truly independent post-change trading sessions, complete one-minute post-entry executable SIP/BOATS quote paths, after-fee replay and held-out periods. The 60 older completed round trips were only three dates and only 13/60 had qualifying two-sided executable quote observations in the prior audit. No exit parameter changes are supported or authorized.
