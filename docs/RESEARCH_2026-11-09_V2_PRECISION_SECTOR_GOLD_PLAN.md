# V2 reliability-first sector research gate — 2026-11-09

RESEARCH ONLY. Do not import into V1 or production order engines. No broker order placement or cancellation.

## Why the rule is changing
The current 52-week semiconductor research has 2,244 stock-days, 254 >=5% gainers and 209 >=5% decliners. Recent studies detected almost every severe decline only after increasing warnings on nonsevere days to >1,000. Detection recall is NOT profitable-trade precision, and >=80% detection must not be misrepresented as 80% trades making money.

On Nov 9 at approximately 07:16 America/Chicago, read-only host checks found Alpaca PAPER entry execution still enabled through `trading-sector-paper-executor.timer` (minute cadence) and `trading-five-day-rebound-paper.timer` (minute cadence). Logs reported paper submitted buy orders for LRCX/ALAB in the sector strategy and AMD/MU/SNDK/NVDA/TSM/INTC/SOXX/AVGO/WDC in rebound scan, statuses accepted or pending new, NOT necessarily filled. The IBKR connected trade feed separately showed BUY fills in WDC, NVDA, ALAB, VRT, AVGO, QQQ and MU. Do not assume these came from V2 research. Reconcile by broker account, execution id and client order id. Preserve existing exit and protection services.

## Confidence target
Independently test each strategy and each sector. Primary metric: **completed PAPER entry profitable after commissions, bid/ask spread, slippage and exit costs**, counted with independent trading-day confidence intervals and portfolio-level drawdown. Aim for >=80% profitable-trade hit rate as a research target, not a currently achieved or promised rate; include Wilson 95% lower bound, minimum number of independent days, and return distribution. Secondary: percentage of serious ups/downs detected early enough to trade, traded days, average after-cost return, tail loss and inventory hours. Evaluate all negative/positive sessions and *no-signal* days. Fix candidate selection in training history, then test later holdout and walk-forward data; preserve prior five COMPLETED sessions and no future bar/news use.

## Emergency sell threshold matrix
Compare prior-close drawdown thresholds **2.0%, 2.5%, 3.0%**, each with 0.5%, 1.0%, 1.5% recent 15-minute losses, and alternative intraday-high or prior-open references. Specifically the existing 2.5% TOTAL includes the 1% over 15 minutes. Separately evaluate ATR-scaled, historical volatility percentile and liquidity-adjusted thresholds by sector. Measure false urgent alerts and profits surrendered by selling before recovery, and severe losses where gap occurred before any signal. Keep WATCH distinct from executable SELL. Failure to get realistic quotes and broker-confirmed fills blocks automatic-exit validation.

## Gold and miners protocol
Test independent timestamped **gold spot / CME futures / GLD / IAU** signals against **GDX, GDXJ** and liquid individual gold producers (e.g. NEM, GOLD/Barrick as correctly as-of ticker mapping, AEM, KGC), separately from silver and gold explorers. Gold's percentage volatility is not equal to gold-miner volatility; obtain independent 1-minute/5-minute SIP and overnight BOATS quotes across >=52 weeks. Use market-session aligned as-of observations (do not treat spot gold weekend advances as executable miner prices). Test leads of 5, 15, 30, 60 minutes and overnight, plus DXY, yields, equity-risk and company earnings. Require miner ETF AND breadth/relative strength confirmation, stale-quote rejection and no pre-existing conflicting risk position. Compare gold alone, miners alone and gold+miner confirmation. Preserve dates when gold rose but miners later fell. Evaluate gap-up chase failure, after-fee profit and loss at 30min, 2pm, close, next opening, and bounded-limit fill uncertainty.

## Sector expansion
Run identical frozen protocol independently for semiconductors, cybersecurity/software, industrials, financials, healthcare, oil/energy, gold miners and broad indices, with sector-specific ATR, breadth, liquidity and catalyst features. Report each sector's out-of-sample confusion matrix (true and false buy/sell, missed up/down days), actual count of entry days, and failure cases. Do not transfer semiconductor threshold to miners by assumption.

## Deployment and communications
All four Trading Opportunities reports: show ONLY near-actionable sector changes and executable high-confidence BUY/AVOID/SHORT/EXIT scenarios, grounded by independently verified as-of evidence, otherwise one line 'No sufficiently reliable actionable setup'. Never force an immediate BUY or GOOD label to satisfy legacy minimums. Sector cards include 3 peers only when the entire sector is near actionable, avoiding noise. Maintain hard safety and emergency exception warnings.

Existing V1 PAPER/LIVE and IBKR order and safeguard systems must remain unchanged by the V2 research task. A future PAPER-only sector strategy can be enabled only after independent backtesting, feed and market-session eligibility, broker readback, partial-fill reconciliation, exposure limits and release review. This document does not authorize new orders.

## Code
`research/v2_precision_gate.py` and `research/test_v2_precision_gate.py`. Run `python -m unittest research.test_v2_precision_gate -v`. The tests are synthetic scenarios, not measured gold/semiconductor outcome statistics.
