# Five-day rebound PAPER: company catalyst test and dual-monitor coordination (November 8, 2026)

## Company-specific catalyst test (19 historical sessions)

Using the *installed* `multi_broker_bridge.rebound_catalysts.screen` code on complete timestamped Alpaca historical news metadata for the 24 hours BEFORE each of 19 completed trading-date sector rebound signals, with article revisions timestamped after the signal excluded:

- 19 modeled bullish sessions after a strictly prior-five-completed-trading-day downtrend.
- Baseline: 16 modeled winning and 3 losing session baskets at 0.15% per-side execution allowance, NOT broker confirmed fills.
- Exactly **one** session matched >=2 distinct negative company fundamentals headlines explicitly naming AMD/MU/SNDK: **February 5, 2026**, affecting **AMD**, with 4 matched AMD adverse headlines.
- Other 18 historical signals (including **all 16 winners**) were NOT vetoed by this narrow headline test.
- Removing Feb 5 would yield **16/18 modeled winning sessions = 88.9%**. Hindsight-developed threshold and tiny sample: *not* proven or 100%.
- February 5 was a sector-wide simulated trade loss: AMD −$52.74, MU −$114.00, SNDK −$123.39, SOXX −$53.21, NVDA −$44.44, AVGO −$83.94, WDC −$142.24, TSM −$68.70, INTC −$76.00; total **−$758.66**.
- Omitting AMD **alone** would have left **−$705.92**, still a large loss. Thus the test's blanket basket veto avoided a common rebound failure on this one session, even though the causal news was AMD-specific.
- IMPORTANT DISTINCTION: not all nine stocks closed lower on February 5. Using split-adjusted Alpaca regular prices (Feb 4 15:55 ET vs Feb 5 15:55 ET): AMD −3.84%, MU **+0.90%**, SNDK −1.42%, SOXX **+0.12%**, NVDA −1.33%, AVGO **+0.83%**, WDC −3.38%, TSM **+1.49%**, INTC −0.64%. The simulated adverse outcome was specifically **buying after an evening rebound signal and selling before market open**, not necessarily end-of-day declines.
- AMD adverse matched first-publication UTC headlines: Feb 3 22:49 (China AI chip outlook), Feb 4 14:11 (earnings beat and selloff), Feb 4 14:35 (Q4 earnings and price slip), Feb 4 19:47 (China AI sales and doubts); historical bull signal cutoff Feb 4 **21:30 UTC**. Exact datetime-based creation/last-update cutoff was enforced. Stock-specific news of other companies is not an anchor veto.

**Guard design:** For this PAPER candidate only, >=2 distinct independently timestamped adverse company earnings/guidance/fundamental headlines naming an *anchor* (AMD/MU/SNDK), with material terms and negative context, block the entire 9-symbol rebound basket; generic sector selloff articles do not block. This is a cautious rule and requires future reevaluation. A missing news API response fails new buys closed, not existing position exit management.

## Both monitoring mechanisms, only one rebound order execution owner

Verified on www3 host:
- `trading-five-day-rebound-paper.timer`: enabled + active, every minute at second 12; `trading-five-day-rebound-paper.service` executes `multi_broker_bridge.paper_rebound_runner --once --execute`, User `alpacafeed`, PAPER credentials only, separate SQLite ledger and FDR client order IDs. This runner **alone** owns rebound signal PAPER orders and mandatory premarket exits. It reads current broker positions/orders, avoids symbol conflicts, and persists order attempts BEFORE sending. Order accepted is NOT order filled.
- `trading-sector-monitor.timer`: enabled + active, five-minute observer; its appended `rebound_alert_watch.py` consumes a nonsecret, atomic handoff file at `/var/lib/sector-rebound-handoff/current.json`, sends deduplicated Pushover signal/veto message and **has no broker order access**. Its broader `OnSuccess` separately launches the *preexisting* generic sector PAPER executor; that existing executor reads broker positions and open orders before placing its own strategy orders. This does not give the five-minute rebound notifier purchasing power. Generic PAPER executor is separate and can recommend independent purchases; cross-strategy safe reconciliation should continue to be audited.
- `Task - Five-Day Rebound Alerts`: enabled hourly, **read-only**; it inspects the strategy SQLite events and broker READ-ONLY orders/positions to confirm whether an earlier host buy/sell was accepted, partially filled or fully filled, and avoids repeated events. It **must never** place, re-place, cancel or modify orders. It is secondary confirmation, not a second order submitter.
- Test verification: host `unittest` 10 rebound PAPER runner tests and 7 catalyst tests passed; local five-minute rebound Pushover observer with synthetic nonsecret signal and `send=False` returned `WOULD_NOTIFY` (no user message sent). Both timers active. Last historical/current Sunday runner returned `SESSION_CLOSED`; no strategy database events or actual rebound fills existed yet. Hourly task last completed run reported broker zero positions and open orders and zero notification delivery rows; live end-to-end has not been demonstrated yet.
- *No claims* of actual successful push delivery, broker buy, sell, or exit until a qualifying signal and verified broker readback occur. Explicit PAPER only, not IBKR or LIVE.

Historical strategy research source repo: `securityprepper/multi-broker-bridge`; prior installed code and main branch implementation documented separately.
