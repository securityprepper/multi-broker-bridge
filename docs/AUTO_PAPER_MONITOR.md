# PAPER premarket timing upgrade — installed November 9, 2026

## Read-only historical executable-quote plausibility — November 9

After the initial completed-bar replay, we requested historical **Alpaca SIP best bid/ask quotes** for the candidate minute, centered on the actual one-minute MBB scheduler's `:40`-second decision time (no broker orders). All six queried names returned positive, sufficiently recent bid/ask with spread below the executor's 1% ceiling. They are observations of contemporaneous quotes, not guaranteed fills or evidence the strategy would have executed automatically.

| Stock | Historical theoretical decision (CST) | SIP ask | Spread | Historical bar confirmation |
|---|---|---:|---:|---|
| AMD | 03:18:40 | $457.95 | 0.197% | SMH/AMD/MU/SNDK 2/3-anchor uptrend |
| CAT | 06:50:40 | $569.96 | 0.521% | Semiconductor-anchored fallback breadth in research replay; CAT is outside the current MBB universe |
| CRWD | 08:46:40 | $219.94 | 0.145% | Semiconductor-anchor replay; require independent cybersecurity confirmation for actual BUY |
| PANW | 08:47:40 | $318.79 | 0.097% | Semiconductor-anchor replay; require independent cybersecurity confirmation for actual BUY |
| PWR | 08:50:40 | $570.69 | 0.175% | Research replay only, outside the current MBB universe |
| GS | 09:53:40 | $905.00 | 0.034% | Research replay only, outside the current MBB universe |

**Critical qualification:** The study code used AMD/MU/SNDK anchor confirmation for every historical candidate as an investigative comparator, regardless of the candidate's sector. It is **not** a faithful replay of the deployed MBB's per-sector gate for CAT/PWR/GS/CRWD/PANW. Only AMD is a direct semiconductor-sector example. Re-run other names with their own sector anchors and current quote/spread/risk gates before enabling purchases. The quotes cannot establish likelihood of order fill or favorable subsequent P&L, and should not be represented as guaranteed earlier order prices.

---


The owner requested earlier qualified PAPER stock purchases, fewer premature premarket sales, and **one lower-price re-entry before 10 AM Chicago** after a substantial realized profit. This change is now installed in the restricted `trading-sector-paper-executor.service` on www3; its enabled one-minute timer remains active, while the separate FDR rebound strategy's `MULTI_BROKER_REBOUND_NEW_ENTRIES=0` validation pause is unchanged. **114 automated non-pytest unit tests passed on the installed code.** No LIVE orders/API endpoints and no IBKR Gateway changes.

- Early entries: the existing Multi-Broker Bridge scans eligible BOATS overnight and SIP premarket quotes and 1-minute volume-backed bars, with at least 2/3 sector anchors confirming rising price structure and each specific stock independently qualifying. Earlier timestamps are possible; no guarantee of best price or available liquidity. The broader momentum strategy retains original up to $2,000 per-stock PAPER order cap and buy/open-order duplicate checks.
- Normal premarket exit: **at least +2.0% return from original cost to verified current BID** (not just a candle close/peak). Ordinary two-lower-bar wiggles, +1% target, standard 2% peak trailer or steady-trend 2.5% peak trailer cannot trigger a premarket sell unless that +2% executable gain exists. A separate `<= -2.5%` verified-bid **emergency risk exception** remains eligible for limit exit; it cannot guarantee fill or broker-native overnight stops. A distributed 25+-bar overnight uptrend is persisted so a routine pullback does not erase its stronger-trend classification.
- Profitable discounted re-entry: after the previous premarket SELL is independently confirmed **fully filled** by Alpaca PAPER and banked **>=2% profit** versus the matching fully filled BUY, a **single re-entry before 10:00 AM CT** is allowed if (1) a fresh 2/3 sector-anchor rising BUY_WATCH occurs with qualifying individual 1-minute bars, (2) verified executable ask is **>=0.25% lower** than the completed earlier sell price, (3) at least two minutes elapsed, (4) no current position or pending order, (5) account cash, spread, daily broker-loss/holiday safeguards allow the trade. A unique immutable `reentry` client ID prevents retries/duplicate submissions. Sunday evening through Monday morning is treated as one session when evaluating this condition.
- Today’s AMD example: MBB BUY 7:35:42 CT 4 @ $466.700, SELL 7:37:42 CT 4 @ $466.000; FDR independently BUY 7:06:13 CT 4 @ $469.000, SELL 7:30:13 CT 4 @ $464.520. Neither prior sale banked profit, so neither qualifies for the **discounted-profit re-entry** rule. A strict no-lookahead completed 1-minute historical replay gave a potential AMD sector-confirmed positive bar at **03:18 CT near $458** and early CRWD/PANW positive bars at **08:46/08:47**, but those are *bar closes*, not actual executable best asks or verified fills. The replay found no AMD candidate meeting a complete discounted profitable-sale/reconfirmed sector criterion before 10 AM. A distinct higher-price trend-continuation re-entry after a stopped-out loss is *not enabled*, pending independent multi-day testing.
- **Mandatory same-day exits unchanged:** new entries stop 13:15 CT, strategy-owned broker positions start flattening 13:40 CT regardless of source feed status, urgent if unresolved at 13:50, verify broker flat by 14:00 or mark a breach. Account outages, halts, order rejects and extended-hours market liquidity can prevent timely execution. PAPER simulation profits are not evidence of LIVE results.

**Important result-quality limitation:** The November 9 PAPER fills prove that buying earlier is possible, not that an earlier signal is always a better trade. The short prior strategy sold many trades at losses, and the new policy is not yet prospectively verified to increase profit or reduce drawdown. Existing Task - Trading Strategy Research and Task - Recommendation Audit now track the prospective bid/ask/filled price, premature-exit rate, discounted re-entries, realized P&L and 13:40 liquidations. Compare >=20 market sessions against a hold-out baseline before expanding leverage/risk.

---

## CONTROLLING LIVE CONFIGURATION — November 8, 2026

**MULTIPLE QUALIFYING STOCKS PER TRIGGERED SECTOR — PAPER EXECUTION ENABLED.** The owner's later expansion supersedes the single ETF/single-share interpretation. The five-minute observer remains read-only but triggers `trading-sector-paper-executor.service` through systemd `OnSuccess`; independently `trading-sector-paper-executor.timer` is **enabled and runs every minute at :40** with `MULTI_BROKER_ALLOW_PAPER=1` and `--execute`. It uses Alpaca's fixed PAPER endpoint, scoped systemd credentials, source-specific sector watchlists and idempotent client-order IDs. No LIVE account/order endpoint is used. **Broker PAPER account GET was verified active, with zero current positions and zero open orders on November 8; no automatic orders/fills were yet seen.** The market was closed Sunday morning, and scheduled executor runs correctly logged `PAPER_EXECUTION / SESSION_CLOSED`.

**Watchlists retained:** semiconductors 18 individual stocks; oil/energy 16; cybersecurity 12; AI infrastructure 8 (see `multi_broker_bridge/watchlists.py`). A sector qualifies when at least 2 of its 3 anchor stocks have 3 successive 1-minute higher highs and lows. The executor may independently buy *multiple individually confirmed rising constituents* in that sector, **up to $2,000 per accepted stock order** subject to broker PAPER cash, quote age/spread, position, outstanding orders and prior attempts. It does not blindly purchase all members of a sector, and does not equate a futures-only early-warning alert with a verified individual stock buy. This is *not* the single SOXX/SOXL/SOXS ETF rotation. There is currently no account-wide exposure cap beyond PAPER cash; results must disclose this simulated risk.

**2 PM Chicago exit upgraded:** `NEW_ENTRY_CUTOFF = 13:15`; independent `paper_time_exit.timed_flatten` runs **from 13:40 CT** ahead of quote and market-data fetching. It validates Alpaca's PAPER market clock and owned positions/orders, cancels MBB-tagged open orders and waits for broker readback before submitting a market close for each fully verified strategy position. It reserves deterministic `flatten` IDs before any POST; unknown broker outcomes never result in blind retries. Starting at **13:50 CT**, it reports overdue-risk for anything not confirmed flat; after **14:00 CT**, a remaining position is a breach, not a fictitious successful close. It protects unrelated/manual orders and refuses to sell quantities greater than its strategy's tracked purchases. A halt, account outage, broker lag or rejected market order can prevent closing by 2 PM; software cannot guarantee fills. No market sell is queued outside RTH.

**Regression validation:** 52/52 tests passed on the installed www3 code, including simultaneous exits for two separate owned stocks, no stale-quote dependence for liquidation, stop/cancel readbacks, manual-share protection, timeout deduplication and multiple stock entries. Both five-minute monitor and one-minute PAPER executor timers stayed enabled/active. The IBKR Gateway and all LIVE safeguards were untouched.

**Scope caveat:** This currently installed multi-stock strategy uses its **own independently confirmed 1-minute sector breadth signals**. The five-minute monitor's successful runs wake it but do not force a buy solely on each five-minute alert. Existing inverse-ETF SOXS-on-AVOID and explicit SOXX/SOXL regime rotations remain a separate uncommissioned rule set; they must not be represented as already live.

---

# Five-minute monitor PAPER execution — installed on www3

## Current implementation

The existing `trading-sector-monitor.service` remains a credential-free observer, but its systemd `OnSuccess` launches **`trading-sector-paper-executor.service`**, which is configured with `MULTI_BROKER_ALLOW_PAPER=1` and `--execute`. The separate `trading-sector-paper-executor.timer` also runs it every minute (:40) to monitor entries, existing positions and exits between five-minute scans. `securityprepper-alpaca-feed.timer` remains enabled for the original premium-data observer. The executor uses the protected Alpaca PAPER credentials with the `alpacafeed` OS account, not LIVE credentials.

No PAPER fills have yet been observed from an *automatic* entry signal. The Saturday installation checks correctly returned `PAPER_EXECUTION / SESSION_CLOSED`.

## Exactly what it does

- Reads fresh, authenticated Alpaca SIP or BOATS one-minute stock bars and bid/ask quotes for semiconductor, oil/energy, cybersecurity and AI-infrastructure watchlists. It does **not** execute from unofficial Yahoo quotes.
- Confirms a sector when **at least two of its three liquid anchor stocks** have three consecutive completed rising one-minute highs and lows. Evaluates every other watched constituent individually for the same pattern. Rejects a one-minute spike above 2.5%, crossed or stale quotes and bid/ask spreads greater than 1%.
- For a qualified long entry, checks the exact PAPER broker's positions/open orders, holiday gate, available CASH and a persistent local per-stock order record. Skips symbols already owned or ordered. Sends an eligible extended-hours DAY **LIMIT BUY** at the verified ask; one share for high-priced stocks (`ask >= $750`), otherwise the most whole shares allowed under **$2,000 per order**. There is no additional portfolio-wide cap, and the broker's available PAPER cash remains binding.
- Reserves an immutable daily stock/order ID **before** sending so a network timeout is UNKNOWN, not a reason to submit the order again. Cancels only its own unfilled BUY orders after two minutes; a cancellation request is not proof of cancellation.
- Tracks only positions from its own accepted entry references, and never uses an unidentified manual position to authorize a new short SELL. Software exit evaluations include: a 1% profit target; a 1% loss threshold; two one-minute bars with lower highs and lower lows; or a 0.5% pullback after reaching at least a 0.5% gain. The stored high-water mark only considers bars observed after the entry.
- Starts a close-by-2 PM Central process at **1:40 PM Central**: if an earlier SELL limit is pending it requests cancellation, waits for broker readback on the next tick, then may issue a regular-hours MARKET close. It never assumes an unconfirmed cancel or exit succeeded. A broker rejection, market closure, data outage or unfilled order can prevent an actual close.

## What is not implied

- The system is **not** a guaranteed stop-loss. If API access, electricity, data, or the host fails, a software stop cannot operate.
- Not a broker-native bracket or trailing stop and not LIVE trading.
- Falling sector alerts do not automatically initiate a short sale or buy a leveraged inverse ETF. A later separately specified rule can add PAPER short/inverse logic.
- SOXX is currently the unleveraged semiconductor ETF *comparison alternative*, not automatically purchased alongside all semiconductor stocks. SOXL leverage is not the default.
- The existing separate IBKR Gateway has passed PAPER identity and historical-bar checks, but the IBKR **host order-execution runner is not yet enabled**. An Alpaca PAPER order is not evidence of IBKR commissioning.

## Verification

```bash
systemctl show trading-sector-paper-executor.timer -p ActiveState -p UnitFileState -p NextElapseUSecRealtime
systemctl show trading-sector-monitor.service -p OnSuccess
journalctl -u trading-sector-paper-executor.service -n 30 --no-pager
```

The PAPER executor source and tests live in `multi_broker_bridge/auto_paper.py` and `tests/test_auto_paper.py`. Every reported order must be reconciled against the broker's PAPER dashboard; `accepted` is not `filled`.
