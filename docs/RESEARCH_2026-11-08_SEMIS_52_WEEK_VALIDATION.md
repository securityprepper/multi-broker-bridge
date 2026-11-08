# 52-week semiconductor entry/exit tests — November 8, 2026

**Research only. Not broker-confirmed P/L. No trading logic, scheduled tasks, PAPER accounts or LIVE accounts were changed.**

## Data and scope

Authenticated Alpaca SIP split-adjusted historical daily and five-minute bars for AMD, MU, SNDK and SOXX. Window: Nov 7, 2025–Nov 6, 2026 (251 daily trading sessions). Five-minute query used Alpaca historical pagination in 13 calendar-month requests; ~189k OHLC bars across four symbols. SIP covers after-hours/premarket/RTH, but is **not** the BOATS overnight venue. A separate 20-session BOATS+SIP analysis had earlier been completed. The full-year results **do not simulate 8 PM–4 AM ET fills**.

SOXX underwent a 3-for-1 split Nov 5, 2026, so this report uses Alpaca `adjustment=split` in **both** daily and five-minute source requests. Dataset file and working scripts are on authorized www3 /tmp and are ephemeral:
- `/tmp/semis_52weeks_alpaca_daily.json`
- `/tmp/semis_52wk_5min_sip_adjusted.json`
- `/tmp/semis_52wk_daily_eval.py`
- `/tmp/semis_year_intraday_strategy.py`
- `/tmp/semis_52w_train_validate.py`
- `/tmp/semis_52wk_candidate_detail.py`
- `/tmp/semis_52w_intraday_reentry.py`

All scripts are historical/non-trading. No actual broker orders or bid/ask timestamps were used, and hypothetical limits were assumed filled when next-bar OHLC touched prices. This can materially overstate actual fills. A trailing stop only triggers during normal hours and can fill worse than stop price; stop-limits can remain unfilled. Position sizing: whole shares and <=$2,000 per independent stock/ETF order, no account-wide strategy ceiling. P/L before commissions, taxes, financing.

## 52-week split-adjusted daily bar extremes

| Symbol | Year low (date) | Year high (date) |
|---|---|---|
| AMD | $188.22 (Mar 3, 2026) | $658.52 (Oct 6, 2026) |
| MU | $192.59 (Nov 21, 2025) | $1,255.00 (Jun 25, 2026) |
| SNDK | $183.00 (Nov 21, 2025) | $2,354.39 (Jun 22, 2026) |
| SOXX | $86.81 (Nov 21, 2025) | $218.65 (Jun 22, 2026) |

250 daily changes available. Defined a broad positive sector day as at least 2 of 3 leaders (AMD, MU, SNDK) up close-to-close and SOXX up: 118 such days. Positive runs: 30 one-day, 13 two-day, 15 three-day, 3 four-day, 1 five-day; 32 multi-day runs.

## Prior-day signals are not sufficient

Daily bar signal at prior close and next-day close direction:
- Prior moderate decline (2-of-3 down >=2%, SOXX down >=1.3%) flagged 55 next days, only 29 up days (52.7%).
- Prior larger decline (2-of-3 down >=4%, SOXX down >=2.6%) flagged 35, only 19 up days (54.3%).
- Prior continuation (2-of-3 >=+0.5%, SOXX >=+0.5%) flagged 96, only 45 up days (46.9%).

Daily open-to-close hypothetical fills were mostly losing or highly order-of-high-low sensitive; no prior-day-only rule established predictive advantage.

## Five-minute strategies — test protocol

576 combinations tested across 52 weeks:
- Sector breadth: broad (2 of 3 leaders), strict (3 leaders) or momentum only.
- Prior-day filter: none / rebound / continuation / either.
- 15- or 30-minute momentum; threshold 0.3% or 0.7%; gains above previous close 0.5% or 1.5%.
- Exit: premarket limit near 9:20 AM ET; simulated 1%/2% opening trailing stop; or profit limit/stop.
- Same fixed limit order slippage buffer 0.15% per side.
- Selection/training dated through **Aug 31, 2026**, later check Sept 1–Nov 6, 2026. While later prices were withheld from the *ranking*, these patterns were conceived after inspecting November 6 in earlier research; later period is **not pristine validation**.
- The backtest is per opportunity/session; no claim of real order acceptance, overnight stock eligibility, fill priority, partial fills, or order persistence.

**Training-selected candidate:** strict 3-of-3 leadership; all leaders above +0.5% from prior close, SOXX above +0.25%; 15-minute momentum +0.3% in all three leaders and positive SOXX momentum; signal from completed five-minute bars; buy whole shares at a hypothetical previous-bar limit +0.15% next bar; submit a 9:20 AM ET premarket sell limit based on 9:15 close with 0.15% markdown; if unfilled, model has RTH trailing fallback. This deliberately favors very short premarket exits instead of full-day holds.

- All 52 weeks: **69 signal sessions**, 262 completed modeled trades, 9 modeled missed buys, **+$1,971.73 total**.
- Through Aug 31: 215 modeled trades over 56 active days, **+$1,777.13**; 35 winning days and 21 losing; biggest day loss **−$302.30**; positive monthly results inconsistent (Feb −$442.55).
- Sept–Nov 6: 47 modeled trades over 12 active days, **+$194.60**, with **5 profitable and 7 losing days**; worst day Nov 4 **−$246.93**.
- **Nov 6 alone +$400.88**; validation excluding Nov 6 **−$206.28**.
- Model predicted a positive day on 45 of its 69 signal sessions (precision 65.2%) but caught only 45 of the 118 broad-positive days (**38.1% recall**). It failed to identify Oct 28's third positive day.
- It earned modeled +$23.28 on 52-week low Nov 21; signaled neither AMD's low on Mar 3 nor high on Oct 6. At MU/SNDK June high dates June 22 +$22.38 and June 25 +$162.39.
- Previously cited days: Oct 19 +$27.16, Oct 21 +$119.95, **Oct 26 −$29.45**, **Oct 27 −$17.74**, **Oct 28 no entry**, Nov 3 +$178.00, Nov 6 +$400.88. Thus **did not work on each target day**.

### Execution sensitivity

With the SAME candidate selection and intervals:
- 0.05% execution allowance: training +$2,037.76; validation +$281.87.
- **0.15%**: +$1,777.13; validation **+$194.60**.
- **0.30%**: +$655.28; validation **−$78.32**.
- **0.50%**: training **−$866.28**; validation **−$393.74**.

**Critical:** Every one of the 262 modeled completed exits in the winning configuration was assumed filled via the 9:20 AM premarket limit. That entirely depends on tradable quotes, latency and queues absent from the OHLC data. Without verified fills the dollar figures are exploratory only.

### Identical entry, alternative exits

Strict 15-minute signal, same 0.15% execution allowance:
- Premarket limit at ~9:20 AM ET: train +$1,777.13, later +$194.60.
- Simulated 1% RTH opening trailing exit: train +$858.08, later **−$259.33**.
- Fixed profit-taking with downside stop, with **conservative stop-first convention if target and stop are both inside one 5-minute bar**: train +$2.76, later **−$231.56**.

### Additional regular-hours intraday entry tests

Three-five-minute higher-high/lower-low, pullback then recovering, recent-high breakout. Sector positive 15-minute breadth and SOXX, entry after 10 AM ET, maximum once per ticker per session; compare fixed profit versus 1%/2% trailing and stop-watch. 12 combinations in year-long tests. **All combinations lost money in both training and later checking** under this simulator. Example least negative *pullback* fixed-profit variant: training **−$411.21**, validation **−$289.13** on 351 modeled round trips. These are intentionally simple rules and do not exhaust all possible quantitative strategies.

### Breadth versus coverage tradeoff

- Strict (+0.3% 15min) signaled **69** days / **45** of 118 broadly positive days (65.2% precision; 38.1% recall). Validation is fragile but model P/L highest in training.
- Broad 2-of-3 (+0.3%) signaled **134**, caught **81** of 118 positive days (60.4% precision, 68.6% recall) but **validation −$438.04**.
- Momentum-only (+0.3%) signaled **136**, caught **79** up days (58.1% precision) and validation **−$297.44**.

A rule that flags nearly every up day also flags many false positives. It cannot know at 4–8 PM ET which future regular session will finish bullish.

## Conclusion

**No strategy tested meets the user's goal of profitable trades on every positive semiconductor day, including multiple consecutive up days and dates near annual extremes.** The strongest backtest is driven by premarket fill assumptions, fails on Oct 26/27, misses Oct 28, and is negative in the later interval when November 6 is removed. Overfitting parameters to rescue each historical miss would not establish a repeatable edge.

Suggested next controlled *PAPER* measurement (not installed here):
- Distinguish alert/watch (broad sensitivity) from order eligibility (strict).
- Preserve signal time and executable market quote / broker order readback; calculate actual versus theoretical price execution and queue misses.
- Different premarket vs regular-hours exits; do not assume a 1% trailing stop operates outside RTH.
- Expand evidence to other semiconductor peers and more future days without retuning.
- Monitor trades/position reconciliation and mandatory exit separately from signal scoring.

## Official source reference

Alpaca Historical Stock Bars API: https://docs.alpaca.markets/us/reference/stockbars ; its 5-minute interval, SIP/BOATS feed selection, split adjustment and pagination. Order types / RTH trailing restrictions: https://docs.alpaca.markets/us/docs/orders-at-alpaca .
