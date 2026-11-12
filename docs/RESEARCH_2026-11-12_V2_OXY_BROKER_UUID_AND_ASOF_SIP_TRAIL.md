# V2 research — OXY November 12 exit: exact broker FILL and as-of SIP quote corroboration

**Research only; one authenticated Alpaca PAPER account.** No orders, active-source changes, stop edits, production timers or LIVE access. All clock times below use America/Chicago (CST), with UTC source timestamps retained in the sanitized results.

## Newly established evidence

The fresh GET-only account/order/activity read returned **127 distinct Alpaca orders and 275 distinct FILL activity UUIDs** from the bounded November 9 onward history. Every activity's `order_id` mapped to a broker order. November 12 had **3 filled orders and 5 FILL activities**: OXY buy (2 activities), OXY sell (1), and VRNS buy (2). Thus **one new complete round trip** is available in this run, not three trades or five trades. The authenticated account remains PAPER. VRNS is an unmatched open buy in this bounded research inventory, not a completed trade; other accounts are not certified by the check.

The OXY 34-share buy filled **08:48:53.801 CST at $57.64**. Its 34-share sell filled **09:33:50.713 CST at $57.81**. Actual broker-filled gross simulated P/L was **+$5.78**, before unknown fees; holding time **44m 56.9s**. The contemporaneous strategy acceptance journal at **09:33:50.068835 CST** matched the precise sell broker order UUID and reported `exit_signal_reason="trailing peak reversal"` with `exit_fill_verified=false`. The independently retrieved sell FILL activity UUID and quantity matched the final broker-filled order; the interval between journal acceptance and actual fill was **0.644 seconds**. Acceptance was not counted as execution.

## Retrospective, timestamp-limited SIP quote and completed-bar reconstruction

The last **44 fully post-fill, completed** SIP 1-minute bars put the peak high at **$58.175** in the completed **09:19–09:20** minute; a separately returned SIP quote in that minute showed a **$58.17 bid for 200 shares** at **09:19:01.390 CST**. This bid is 0.005 below the trade-bar high, so the high-water reference is not simply an isolated uncorroborated high in this case. It is nevertheless not evidence of a hypothetical fill at that price.

With the recorded +0.5%-from-entry trail arming level and a 0.5% peak reversal, that peak implies a reversal boundary of **$57.884125**. Among the fully completed post-entry 1-minute bars, the first close below that boundary was the **09:32–09:33** bar, closing at **$57.82** at **09:33:00 CST**. The preceding completed bars had not crossed it. The strategy accepted the sell about 50 seconds later. The maximum completed-bar trade high, $58.175, remained below the hypothetical +1% profit target **$58.2164**; this does not establish execution/fill conditions for alternate orders.

Of **610 historical SIP quotes** retrieved for 09:33:20–09:33:51, **560** were valid-shaped, noncrossed and positive-sized as of the journal decision. The nearest at **09:33:50.066255 CST** was only **2.58 milliseconds** before the journal acceptance, displaying **bid $57.80 (200 shares)** / **ask $57.82 (1,300 shares)**, spread **0.0346%**, and a **0.6446% drop** from the $58.175 trade-bar peak. The eventual actual PAPER sell at $57.81 is between that bid and ask. These are *retrospectively retrieved* historical quotes; their original availability to the running strategy, adverse selection, and simultaneous fills at hypothetical alternate limits are not certified.

**Assessment:** one of one newly completed November 12 round trips is broker-FILL-UUID corroborated and has a contemporaneous recorded sell reason independently consistent with completed-bar reversal and fresh historical SIP prices. This is a valid **trailing reversal attribution**, not proof of a software malfunction or evidence that changing exit parameters improves performance. It also falls in the **over-30-minute** cohort, not the rapid-exit subgroup.

## Scope and safeguards

Prior November 9–11 baseline: **60 closed round trips over 3 distinct trading days** (51 MBB, 9 FDR). This study adds one completed MBB round trip on a fourth date. Earlier **48 ordinary MBB** sell reasons remain `UNKNOWN` because original acceptance journals lacked non-null reasons; nine FDR scheduled exits and three MBB time-guard exits were already source-classified separately. More than 20 independently observed sessions, complete quote paths, fees and untouched holdout comparisons are still required to support a parameter change. The retired, after-cost-unprofitable price-only signal and routine-reentry research families are not reopened.

Reproducible pure/offline analysis: `research/v2_oxy_exit_quote_corroboration_20261112.py`; **12 isolated unit tests passed** in a repository-layout scratch checkout. No API calls or broker logic are included in the committed evaluator. All original V1/PAPER/LIVE services, orders, stops, 13:15 entry cutoff, 13:40 flatten and holiday gates were left untouched.
