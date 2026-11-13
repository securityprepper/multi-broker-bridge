# November 12, 2026 — First post-change Alpaca PAPER RTH anti-churn forward observation

**Scope:** retrospective **read-only** inspection after the first trading session subsequent to the November 11 installed PAPER-only regular-session two-bar correction. **No PAPER or LIVE order, service, timer, protective stop, or profit target was modified in this research run.** This is **one genuinely later day of observation, not a 20-day or independent multiweek performance validation.**

## Authenticated filled-order evidence, one account only

The existing authorized `/var/lib/securityprepper-paper-inventory/current.json` Alpaca PAPER exporter was broker-verified and marked `recent_orders_complete=true`; captured at 2026-11-13T01:05:05Z. It covers an authenticated PAPER account whose account ID is **not contained in the research data**; it must not be presented as all Alpaca accounts or compared across unidentified accounts. The recent-order horizon began 2026-11-10T01:05:05Z and thus covers the date studied.

| Source, Nov 12 CT | Actual broker BUY filled | Actual broker SELL filled | Time held | Qty | Gross realized P/L | Verified sell origin |
|---|---|---|---:|---:|---:|---|
| MBB OXY | 08:48:53 @ $57.64 | 09:33:50 @ $57.81 | 44m57s | 34 | **+$5.78** | Broker FILLED limit sell; matching MBB journal records `exit_signal_reason=trailing peak reversal` (not merely order acceptance) |
| MBB VRNS | 08:38:52 @ $49.09 | 13:40:32 @ $49.12 | 5h01m40s | 40 | **+$1.20** | Broker FILLED market sell in required 13:40 CT flatten interval |
| **Total for this one account/session** | 2 BUY orders | 2 SELL orders | | | **+$6.98 gross** | Both broker-filled; zero RTH two-lower-bar sell reasons |

The journal also recorded the MBB OXY sell as initially `pending_new`: this is **not** itself proof of execution. Broker independently reported the actual FILLED SELL and weighted fill price, which is the P/L basis. No round trip under 30 minutes appeared in this eligible PAPER cohort on November 12. Other strategies/accounts are **UNKNOWN outside this scoped exporter**, not claimed to be flat or absent.

The active `trading-sector-paper-executor.timer` remained enabled/active, and the imported installed PAPER `trend.py` (SHA256 `eb847459672b723fdcb2c16f8017fe3848d1a41bb6899b92eef40554297195df`) preserved +1% RTH profit, -1% loss, the existing 0.5% peak-reversal rule, 13:15 CT entry cutoff and independent 13:40 CT flatten. A pair of trivially falling one-minute bars alone no longer generates RTH SELL. No live V1 or IBKR changes.

## Opportunity cost — OXY actually exited on the remaining trailing gate

Using GET-only licensed split-adjusted SIP **completed one-minute trade bars**, OXY had **291/291 continuous post-BUY minutes** through 13:40 CT. Its fully observed lowest trade was **$57.47**, or **-0.295%** from the broker's $57.64 entry; no minute range touched a -1% entry stop. This does **not** prove that the spread, marketable size, or a synthetic protective stop were always executable.

OXY's actual trailing-reversal SELL filled at 09:33:50, for **+$5.78 gross**. Subsequently, completed one-minute bars showed:
- **+1% from entry** first touched at 10:11 CT,
- **+1.5%** at 10:49,
- **+2%** at 11:10,
- maximum **trade high $58.895 at 13:16 CT**, implying **+$42.67 gross at the per-trade hindsight high**, not an executable result.
- The historical **SIP displayed bid was $58.81, age 0.18 seconds, displayed size 300 versus held 34**, just before fixed 13:40 CT flat. This marks a **+$39.78 gross counterfactual hold-to-flat**, still subject to queue/microstructure, actual fill, software risk, liquidity and fees. The true trade realized +$5.78.

This is one specifically documented **post-sale missed favorable follow-through caused by the surviving trailing gate**, not by the removed two-lower-bar rule. It motivates **research-only** comparison of trails that activate after material verified unrealized gains, but **does not justify weakening a PAPER protective exit on only this favorable date**.

VRNS observed 271/301 potential one-minute post-entry bars and has 30 minute gaps; its maximum *observed* trade high $49.19 equates to only +$4.00 gross at perfect timing, but it **cannot be entered into complete stop-first simulations**. Its last historical SIP quote prior to 13:40 was **15.48 seconds old** (stale for our strict high-freshness comparator), although an actual broker market sale filled at $49.12. The actual broker profit of +$1.20 is independently valid regardless of SIP quote completeness.

## Frozen target comparison versus prior evidence

The previously committed read-only `research/v2_paper_rth_target_capture_20261111.py` (rules defined before November 12) re-ran unchanged on new private November 12 snapshots. Only **OXY 1/2** had a complete one-minute path; VRNS remains UNKNOWN. With conservative stop-first when both high and low touch in a minute, a presumed -1% resting stop (not identical to deployed software exits), flat-only SIP-bid proxy and **illustrative 0.30% round-trip friction**, hypothetical OXY outcome by target:

| Target from filled entry | Complete OXY path target touch before stop? | Hypothetical P/L after illustrative 0.30% friction |
|---|---|---:|
| +0.5% | Yes | +$3.92 |
| +1.0% | Yes | +$13.72 |
| +1.5% | Yes | +$23.52 |
| +2.0% | Yes | +$33.32 |

**No row proves a standing profit-target order would fill.** High/low touches are not bid/ask executable fills, and no such new order was placed. One favorable day cannot override the earlier 33 complete-path MBB historical trades, where +1.5% produced fewer target touches than +1% and neither showed profitable after-cost expectancy. **Do not change the approved active +1% RTH software profit trigger.** Continue to measure the existing trailing gate separately, including its avoided losers, not just missed subsequent highs.

## Sealed supporting private data, reproduction, and next constraints

Saved read-only collector result on www3 only, owner-only permissions (directory 0700, files 0600): `/tmp/v2-paper-forward-nov12-20261112-private/fills_1m_private.json` and `flat_quotes_private.json`. The collector queried **Alpaca DATA GET only**, **no broker API POST/DELETE**. Private fill/order IDs, licensed quote bars, API credentials and account details were **not** committed.

- Cached fills+one-minute bars SHA256: `34864190ff05f65669bdd02f34740306c92acecdc1897511cd2f4bcd20a653fb`.
- Cached flat-quote marks SHA256: `d39703862a0d93530935f11537729e2fdb9495bcf058d8d681a538fe4dcb18fd`.
- Target replay (pre-existing V2 branch): `python3 research/v2_paper_rth_target_capture_20261111.py --fills /path/to/authorized_private_fills_1m.json --flat-quotes /path/to/authorized_private_flat_quotes.json`.
- Research methodology remains strict: confirmed broker FILLED timestamps, one verified account, no duplicate order/partial activity counting, completed bars *after* entry, stop-first ambiguous minute ordering, no retrospective negative-news BUY clearance, 13:40 CT latest flat, and `NEWS_UNKNOWN` on historical buy-candidate news eligibility.

Prospective score: **1 post-change independent session**, **2 broker-verified completed PAPER positions**, **both realized gross winners**, **zero two-bar-only exits**, **one other-trigger early exit followed by meaningful favorable movement**. This is **not** proof the new exit rule improved outcomes versus a contemporary A/B control, or that a trailing-stop change would be safer. Maintain the same frozen exit rules through at least 20 distinct future sessions before any parameter selection. The existing Task - Trading Strategy Research should evaluate new PAPER closed fills independent of recommendation linkage without duplicate notifications from Recommendation Audit. Do not alter scheduled tasks or LIVE permissions. Holiday validated cache revision 2 was unpaused until strictly before November 13, 2026 16:13 Chicago, absent calendar invalidation.
