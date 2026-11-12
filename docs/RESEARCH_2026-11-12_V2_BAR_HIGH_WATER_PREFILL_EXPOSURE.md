# November 12, 2026 — MBB high-water source and prefill-bar exposure

Research-only readback on authorized www3, approximately 10:30–10:38 America/Chicago. Prior validated holiday status remained UNPAUSED revision 2 before November 13, 2026, 16:13 CST, absent a calendar edit. No orders, active V1 source, protective stops, timers, service settings or LIVE permissions changed. This is NOT a recommendation performance notification.

## Newly established implementation provenance

Active MBB `auto_paper.py` uses a `tracked.entry_time` timestamp initialized at scan/request time, prior to a broker-confirmed filled buy. It persists `highest` as the maximum of 1-minute SIP **trade-bar HIGH** observations whose minute-bar start is at or after that stored timestamp. `trend.py` calculates the RTH trailing reversal from the latest completed **trade-bar CLOSE** divided by the persisted trade-bar high, with +0.5% arming and -0.5% reversal. The actual SELL limit uses a separately obtained fresh bid, but the historical high-water used to trigger that exit has **not** been independently established as an executable bid for the quantity. This is a *source-level potential false-peak mechanism*, not proof of a false sell or of profitable alternative fills.

The active code no longer has an independent RTH two-falling-bars exit, but it retains +1% profit, -1% loss, the 0.5% trail, and premarket/mandatory flat safeguards. Historical Nov 9–11 trades must be attributed to their THEN-active code; do not retrospectively assign today's mechanism to them.

## Actual PAPER order timestamp exposure, bounded 72-hour GET-only inventory

The 2026-11-12T16:30:02Z authenticated PAPER snapshot was complete for its stated rolling order window (63 orders: 62 filled, one canceled), with 30 filled BUY orders. Relative to the stored scan-entry timestamps, **2/30** buys crossed into a minute-bar interval starting before their fill and ending after it:
- PANW: scan timestamp 2026-11-09 16:49:40.187Z, broker buy filled 16:50:43.110Z; eligible 16:50 SIP minute interval could contain 43 seconds of pre-fill prints.
- S: scan timestamp 2026-11-11 15:10:30.197Z, broker buy filled 15:11:16.906Z; eligible 15:11 interval could contain 17 seconds of pre-fill prints.

**0/30** had a FULLY completed one-minute bar between these scan timestamps and the broker fill. These are possible partial-bar high-water exposures; no impact on a specific exit was established. This 30-buy rolling-window sample includes both November 12 new buys and some earlier sessions; it must not be confused with the prior 60 completed round trips or represented as all Alpaca PAPER activity.

## OXY as newly instrumented trailing-exit case

OXY's actual PAPER buy 34 at $57.64 filled 08:48:53.801 CST; sell 34 at $57.81 filled 09:33:50.713 CST. Gross realized PAPER P/L was +$5.78 before unknown fees. Its contemporaneous exit journal recorded `trailing peak reversal` tied to the accepted SELL broker order UUID, but the historical activity FILL UUID join is still outstanding; do not upgrade the reason to independently verified from order acceptance alone.

Read-only persisted high-water was **$58.175**, approximately +0.928% above its actual $57.64 buy fill. A 0.5% decline from this bar high corresponds to completed-bar close <= **$57.884125**. The actual SELL fill $57.81 was below that boundary, but a broker fill is **NOT** the prior decision-time bar close and is not evidence of the exact trigger. The high $58.175 is a trade-bar high, not an established fresh bid quote; no high-time executable NBBO proof was available. OXY's buy filled before the next eligible minute start, so this case has NO observed prefill-bar interval exposure.

## Actionability and no-GO

New source provenance is credible; benefit of a bid-confirmed high watermark is **not** established. Do not change current exits. Before a parameter or source release, acquire complete one-minute SIP/BOATS bid/ask quote sequence and exact broker FILL activities, distinguish high-water trade prints from executable bid highs at the as-of decision time, quantify any premature exits and avoided losses across >=20 truly separate trading days and heldout periods. Quote gaps, missing decision-time bar closes, and unknown fees remain UNKNOWN rather than profitable fills. The isolated pure comparator fails closed on missing signal close or confirmed bid peak; it sends no broker requests.


[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]