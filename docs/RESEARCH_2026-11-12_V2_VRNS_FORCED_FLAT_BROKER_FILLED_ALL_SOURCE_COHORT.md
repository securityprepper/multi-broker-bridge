# V2 research — November 12 VRNS 13:40 forced-flat broker fill and source cohort reconciliation

**Research only.** Observed November 12, 2026 at approximately 14:35–14:38 America/Chicago using an existing authorized GET-only Alpaca PAPER audit, independently published GET-only PAPER account inventory, and the existing production sector-executor journal. This report neither submits orders nor modifies any active V1/PAPER/LIVE code, stops, timers, or holiday rules.

## Newly verified round trip (not a rapid exit)

The authenticated PAPER account's November 12 VRNS BUY was **one broker FILLED order, 40 shares, average $49.09, filled at 08:38:52.190787 CST**, despite producing two underlying buy FILL activity records. At **13:40:29 CST**, the existing `trading-sector-paper-executor.service` journal logged `MARKET_FLATTEN_ACCEPTED_NOT_FILLED:VRNS`, explicitly distinguishing order acceptance from a broker fill. A separately retrieved broker order is **one MARKET SELL order, filled for all 40 shares at average $49.12 at 13:40:32.639094 CST**, after broker submission at 13:40:29.986751 CST. The existing fill audit reports two SELL FILL activity events for VRNS, *not* two independent sell orders. The 13:40:40 sector-executor journal independently reported `FLAT_IN_BROKER_SNAPSHOT`, confirmed by the GET-only account inventory at 14:35:03 CST (20:35:03 UTC) (0 positions, 0 open orders).

**VRNS gross realized PAPER result: +$1.20 before fees**, from the broker-filled averages and 40-share quantity, over approximately **5h 1m 40s**. This is a verified **mandatory 13:40 flatten** exit and does not belong to the under-2/5/10/30-minute rapid-exit cohort. Order acceptance was not counted as fill. Individual activity UUIDs are not reproduced in this sanitized report; the existing read-only fill audit maps activities by broker `order_id` to source-tagged orders. No claim of hypothetical executable profit at alternate times is made.

## Bounded all-source PAPER fill reconciliation

An independent GET-only `trading-sector-paper-fill-audit.service` run after the close-out returned **128 distinct broker orders** since November 9, **277 FILL activities**, of which **244 matched MBB-tagged broker orders** and the other **33 had FDR client-order prefixes**. The audit labels those 33 as `unmatched_fill_activities` *relative to MBB*, **not missing broker order IDs or unknown third-source fills**. No non-MBB/non-FDR fill source appeared in this bounded account audit. This does not establish the completeness of other PAPER account identities or all historical activity.

The resulting previously verified closed-trade denominator is **62 unique round trips across four distinct Chicago trading dates**, **53 MBB** and **9 FDR**. For MBB, **4 source-corroborated mandatory-flat exits**, **1 broker-fill and signal-corroborated trailing reversal (OXY)**, and **48 historical ordinary exit reasons UNKNOWN**; FDR's **9 scheduled preopen exits** were previously source-corroborated. These mutually exclusive classifications total 62 and count actual filled round trips, not fill activity events. The previous 60-trade Nov 9–11 baseline is not treated as an additional set.

The MBB gross realized PAPER outcome through the VRNS close is **-$154.14** (previous 51 MBB trades -$161.12, OXY +$5.78, VRNS +$1.20). The nine FDR trades total **-$118.22**, for **-$272.36 combined gross** over 62 trades, before commissions and other unverified costs. This is neither verified after-fee P/L nor an alternative exit-strategy profit comparison.

## Decision

This confirms one **new forced-flat attribution**, not a changed rapid-exit cause or profitable counterfactual. Only four distinct actual trading days are available, not the >=20 independently held-out dates needed for any exit-parameter release recommendation. Current 100-combination completed-bar price-mark grid still has missing 1-minute/quote paths and zero independently verified alternative broker fills. Preserve current emergency risk protection, 13:15 CT entry cutoff, 13:40 CT mandatory flat, 2pm latest flat and broker safety gates. No PAPER/LIVE execution-rule or timer change is authorized by this research.

The latest independently authenticated PAPER inventory had **zero positions and zero open orders**; the research audit submitted **zero orders**. Recommendation-linked closed-trade user notifications remain the sole responsibility of Recommendation Audit, not this independent all-source research.
