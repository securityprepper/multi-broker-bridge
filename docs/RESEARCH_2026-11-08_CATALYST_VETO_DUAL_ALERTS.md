# PAPER five-day rebound: company-catalyst veto and dual-alert installation
_Date: November 8, 2026. Experimental PAPER-only system; no LIVE orders._

## Correct measurement

- **94.4% (34/36)** described bullish **premarket market-direction alignment**, not P/L and not just the five-day-downtrend subset.
- Strictly causal five-completed-trading-session downtrend + sector breakout generated 19 hypothetical active dates in the sampled 52-week study. **16/19 (84.2%) modeled day portfolios profitable** at 0.15% each-side OHLC execution allowance with a modeled 8:30 AM Eastern premarket limit exit.
- Losing dates: February 5 **−$758.66**, March 4 **−$5.57**, August 12 **−$19.39**. Real broker fills, spreads and extended-hours queue behavior not verified.

## February 5 was not just an AMD loss

All **nine modeled constituents** lost on February 5: AMD −$52.74, MU −$114.00, SNDK −$123.39, SOXX −$53.21, NVDA −$44.44, AVGO −$83.94, WDC −$142.24, TSM −$68.70, INTC −$76.00. **Nine of nine tested positions**, not a claim that literally every semiconductor security in the market fell. Total −$758.66.

Avoiding AMD only would reduce the simulated loss to −$705.92. A sector-wide veto on a major adverse company-specific earnings/guidance catalyst in an **anchor** semiconductor stock would instead have avoided that entire portfolio loss in this historical episode. That is why the narrow risk overlay invalidates the **basket**, while it identifies the affected anchor in the alert.

## Event-time-valid historical news study

The authenticated Alpaca /v1beta1/news archive was queried for **each of the 19 trade signals**, returning complete pages of timestamped headlines for the preceding 24 hours. Only headlines both published and last updated **at or before** the completed trade signal time were considered. Headline heuristic:
- Name AMD / Micron / Sandisk explicitly IN the headline, not merely in a broad symbol tag;
- Contain a material fundamentals context (earnings, revenue, guidance, quarter, forecast, outlook, China AI licensing or sales);
- Contain adverse context (earnings disappointment, cut, lower, weak, selloff, concern, doubt, slipping, etc.);
- At least **two DISTINCT headlines** about the same anchor within the 24 hours preceding signal.

This **narrow rule flagged February 5 only**: four independent AMD adverse-company-fundamentals headlines were available before the previous-evening signal. It flagged **none of the other 18 dates**, including none of the **16 modeled profitable dates**. Historical modeled hit rate *after suppressing Feb 5* becomes **16/18 (88.9%)**, with two remaining small losing dates. This is explicitly **in-sample filter development**; cannot claim it will generalize or reach 100% forward. A broader generic-negative-sector-headline veto would have suppressed multiple profitable rebounds, including November 6.

## Activated PAPER-only setup

The following installations on authorized www3.securityprepper.com were verified active on November 8:

1. `trading-five-day-rebound-paper.timer`: one-minute timer, second 12, invokes restricted `paper_rebound_runner.py` as `alpacafeed`, Alpaca PAPER-only, each candidate <=$2,000 per order, total <=$18,000, session and holiday gate, fresh quotes, broker open-orders/positions, unique attempt IDs, previous-position reconciliation, and synthetic 8:30 AM ET premarket exit attempts. Unfilled exits require authoritative broker cancel/order readback before retry; RTH market emergency fallback continues through 3:50 PM ET when broker market is open.
2. `trading-sector-monitor.timer`: existing five-minute read-only sector monitor, **augmented** with `ExecStartPost=-/usr/bin/python3 -B /opt/securityprepper/sector-monitor/rebound_alert_watch.py`. It accesses a nonsecret group-readable, atomic rebound notice under `/var/lib/sector-rebound-handoff/current.json`, records deduplication in its existing SQLite store, and uses its existing Pushover credentials. Sends a **normal priority phone alert** for `BULLISH_SIGNAL` or `CATALYST_VETO` if fresh, correctly formed and holiday allowed. It **never submits orders**. A notification describes order status as NOT FILLED / not confirmed. Provider delivery still needs real qualifying event to verify.
3. `Task - Five-Day Rebound Alerts`, automation ID `Automation_9cfe3672ec3481919f0e0eb15db6713a`, enabled hourly via ChatGPT Automations. Prompt updated to inspect fresh `BULLISH_ALERT`, `CATALYST_VETO`, PAPER accepted orders, broker fills, premarket sell status, duplicate conflicts and exceptions. **READ-ONLY**; cannot place, retry, cancel or duplicate broker orders. Delivery and real end-to-end confirmation need actual future event.
4. The existing `trading-sector-paper-executor.timer` remains enabled. Its separate broker inventory check skips symbols with existing positions/open orders. Rebound runner also checks all broker open orders and positions. Running at :12 and :40 seconds staggers checks; this is a mitigation, **not mathematical proof against eventual-consistency/race hazards**.
5. Safety tests on host passed: 10 runner unittest tests, 7 adverse-news heuristic unittest tests; isolated five-minute monitor dry runs parsed bullish and veto alert types but did not send a real Pushover signal. A Sunday run returned `SESSION_CLOSED`. Latest read of Alpaca PAPER account before installation: active, trading unblocked, no held positions and no open orders. **No buy/sell fills or alert-provider receipts confirmed yet**. The existing unrelated local edits to the original paper-executor source were preserved.

Relevant source files in `securityprepper/multi-broker-bridge`:
- `multi_broker_bridge/five_day_rebound.py`
- `multi_broker_bridge/rebound_catalysts.py`
- `multi_broker_bridge/paper_rebound_runner.py`
- `ops/rebound_alert_watch.py`
- `tests/test_paper_rebound_runner.py`
- `tests/test_rebound_catalysts.py`

## Open cautions

- The learned two-distinct-headline rule uses a limited historical news provider and lexical matching. It may mistake sentiment for causal information or fail on untagged/novel catalysts. **No universally profitable filter established.**
- May block profitable future days if genuinely negative anchor earnings news is followed by a sharp rebound.
- Historical fills were modeled from candle OHLC; valid quote, limit fill queue, gap and cancellation cannot be proven until the PAPER broker readback is logged. The 8:30 AM planned exit may fail; emergency RTH fallback is separately protected but contradicts a guaranteed 'sell before open' outcome.
- ChatGPT hourly alert task cannot deliver sub-hour confirmations; the host five-minute Pushover mechanism serves as fast nonbroker alert.
- No IBKR PAPER order authorization or LIVE account change occurred in this setup.
