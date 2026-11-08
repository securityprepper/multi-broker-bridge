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
- Starts a close-by-2 PM Central process at **1:55 PM Central**: if an earlier SELL limit is pending it requests cancellation, waits for broker readback on the next tick, then may issue a regular-hours MARKET close. It never assumes an unconfirmed cancel or exit succeeded. A broker rejection, market closure, data outage or unfilled order can prevent an actual close.

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
