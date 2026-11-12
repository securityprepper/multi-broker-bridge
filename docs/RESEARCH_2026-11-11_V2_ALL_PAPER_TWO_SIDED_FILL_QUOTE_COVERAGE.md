# November 11, 2026 — Alpaca PAPER completed-round-trip quote coverage, independent research

**Research-only.** Source data are previously authorized broker-verified filled-order pairs and separate SIP NBBO GET-only observations ending strictly at each actual final-fill timestamp. No broker POST, account change, V1/LIVE/PAPER strategy edit, schedule change, or stop modification.

## Newly measured, bounded cohort

- One authenticated Alpaca PAPER account, whose account ID is **not exposed in the sanitized cache**; no claim about other accounts. **60 actual completed long round trips across three trading days**: Nov 9 **40**, Nov 10 **13**, Nov 11 **7** (America/Chicago). **MBB 51**, **FDR 9**; no duplicate same-day source/symbol pair in this bounded input. These are broker-filled orders, not raw activity-event counts or accepted orders.
- MBB realized simulated gross before fees: **-$161.12**, with 14 winning, 36 losing and one break-even completed round trips. FDR: **-$118.22**, all 9 losses. Combined **-$279.34 gross**. Do not interpret this as a commission-verified net result, a conclusion about a source's future profitability, or an all-account census.
- Holding duration: <=2m **4**; >2-5m **9**; >5-10m **9**; >10-30m **25**; >30m **13**. Thus **22/60** filled exits occurred within ten minutes. Exit *reasons* remain UNKNOWN without order UUID joined to the contemporaneous decision-reason journal. The compatible two-falling-bars study is not a proven causal attribution.

## Strict as-of broker-fill NBBO evidence

The independent quote retrieval inspected a five-second interval prior to each of 120 entry/exit final fills. A **FRESH_ASOF_QUOTE** requires uncrossed SIP bid/ask, <=1% quoted spread, <=1.5 seconds age at the fill, and best-side displayed size covering the filled lot. (This is a *research measurement gate*, not a recommendation that the active V1 quote gate be tightened.)

| Quote-leg outcome | Filled legs |
|---|---:|
| Fresh and qualifying | **62/120** |
| Earlier quote present but older than 1.5s | **33/120** |
| Historical quote retrieval unavailable/error | **25/120** |

Only **13/60 round trips** have a qualifying prior quote on **both** actual filled entry and exit. This means **47/60 lack a two-sided time-matched NBBO comparison under this strict gate**. The stale/error category does not prove the market lacked liquidity, and the quote alone does not certify a hypothetical alternative order could fill. All 13 qualifying pairs had best-side displayed size at least the actual filled quantity, but queue priority, quote movement, hidden liquidity and order type still matter.

On these 13 paired cases, actual broker-filled gross was **-$14.22** (6 winners, 6 losers, one flat). Descriptive actual-fill versus prior quote midpoint implementation cost was **$30.10 combined**, equivalent to **12.08 basis points of the entry notional** and median **4.63 bp per pair**. Do not subtract this again from realized gross: the execution prices already incorporate market execution. It is neither a broker commission nor a guaranteed future slippage estimate. Two entries filled above the *previous* observed ask, zero exits below the *previous* observed bid; intra-second quote movement is unresolved, so these are not proven execution faults.

## Decision

**NO GO** for selecting new bracket target/stop or minimum-hold parameters. Existing 100-scenario 1m-mark grid is sensitivity analysis on three days, not an executable/fee-verified, 20+ independent-day forward result. Historical news status is NEWS_UNKNOWN; retain outcome-only controls rather than calling historical buys eligible. Full 20+ untouched days, actual commission/fees, complete account identity, more matched usable SIP/BOATS quote paths, and contemporaneous decision-reason-to-filled-order UUID joins remain missing.

Future work: archive the receiving broker's authenticated account-scoped fill order IDs and quote/decision receipts without credentials or private identifiers in publications, collect 20+ genuinely forward sessions, mark missing quotes/exits UNKNOWN, and use only then an as-of, stop-first, latency+fee-aware heldout comparison. No changes to V1 or broker positions/orders/timers.
