# Sector-trend research — November 8, 2026

**Status: research only; no profitable multi-stock rule has passed independent validation. Do not enable or amend live/PAPER execution based on this report.**

## Scope and evidence

- Historical one-minute OHLC data from Yahoo chart (unofficial and potentially missing overnight minutes), retrieved November 8, 2026; **not bid/ask quotes, not actual limit-order fills**. Dates: October 29, October 30, November 2–6, 2026.
- Symbols: semiconductor leaders AMD, MU, SNDK; independent semiconductor checks NVDA, WDC, AVGO, TSM, INTC; energy XOM, CVX, OXY, EOG; cybersecurity CRWD, PANW, ZS, FTNT.
- Selection days: Oct 29–Nov 4, 2026 (five stock sessions). Later check: Nov 5–6 (two sessions). This is **not a truly untouched holdout**, since November 6 was discussed before the walk-forward design and the sample is small.
- Long-only, at most $2,000 notional per independent order, next-minute limit-filling approximation; price buffer approximately 0.15% each side, simulated broker status (never actual).
- Original strategies studied: three consecutive one-minute higher highs/lows; three five-minute higher highs/lows; breakout; pullback/recovery; 15/30/60-minute sector confirmations; prior-close sector strength; one or two entries per day; profit limits 1%–5%, trailing exits, wider stop watches and re-entry cooldown.
- Meaningful caveats: cannot determine bid/ask availability or order of trades within an OHLC bar; limit orders may never fill; software exits can fail or slip; no tax/commission modeling. Some tests had only one fill per symbol.

## Walk-forward findings

The first restrictive 48-config set that required at least four earlier AMD/MU/SNDK trades had **no profitable candidate on the selection dates**. The least-negative configuration lost $34.62 across four earlier trades, then made +$5.20 across three later trades for the original three—but lost $49.93 on other semiconductor names in the later sample, $120.76 in energy, and $108.40 in cybersecurity.

A further 72-selective-config set allowed holding longer and included fixed profit limits. Its highest earlier return among the three original names was **+$73.31 on only three completed trades**, with parameters:
- 5-minute breakout; 60-minute leader-sector confirmation; 2 of 3 semiconductor leaders at least +2% above prior regular close; no more than one buy per symbol per session.
- Buy before 11 AM ET; ignore first hour of regular trading; one-share/wholed-share sizing up to $2,000 each.
- Take profit around +1.5%; software loss watch at −2%; mark/cancel/flatten by the session's scheduled exit. The loss watch was not a guaranteed broker stop.
- Later Nov 5–6: **AMD +$23.68; MU −$32.62; SNDK +$24.64; total +$15.70 on three trades.**
- Independent later semiconductor names: **NVDA +$25.90; WDC $0; AVGO −$41.58; TSM −$45.80; INTC +$27.00; total −$34.48**.
- The same parameter set generated **zero energy and zero cybersecurity entries** over the evaluated training/later periods; that is non-execution, not demonstrated transfer profitability.
- With the same parameters but a three-1-minute pattern: earlier original three +$72.44 on three trades; later +$7.28 on three trades; five independent semiconductors −$68.60. Five-minute higher highs/lows: earlier +$70.12; later +$17.08; independent semiconductor names −$87.85.

Illustrative three-original-name fixed-parameter modeled entries/exits:
- Nov 3 SNDK: 1 share, $1,114.50 entry 7:20 ET; profit exit $1,132.29 at 7:53 ET; +$17.79.
- Nov 3 MU: 2 shares, $859.45 at 5:02 ET; profit exit $871.37 at 8:31 ET; +$23.84.
- Nov 3 AMD: 4 shares, $482.03 at 7:40 ET; profit exit $489.95 at 9:41 ET; +$31.68.
- Nov 6 SNDK: 2 shares, $887.33 at 6:24 ET; profit exit $899.65 at 6:42 ET; +$24.64.
- Nov 6 MU: 2 shares, $716.30 at 6:37 ET; loss-watch exit $699.99 at 8:08 ET; −$32.62.
- Nov 6 AMD: 4 shares, $435.54 at 6:30 ET; profit exit $441.46 at 9:21 ET; +$23.68.

The profits on November 3 and 6 are not enough evidence to claim that a strategy works: the training winner contains only three completed trades, later MU loses, and new semiconductor symbols lose.

## Execution assumptions and unresolved problems

- Limit fills were approximated with next-bar OHLC; no actual fill, broker acceptance, borrow availability or executable extended-hours quote was tested.
- A simulated 2% downside threshold is **not** a maximum 2% realized loss; the gap between signal and fill can be larger.
- A one-minute alert can be useful for monitoring, while 5/15/30/60-minute context reduces false entries; there is no demonstrated universal superiority of either three 1-minute or three 5-minute patterns.
- Do not automatically buy every constituent or buy both leveraged sector ETFs and sector constituents. No model above proved reliable on sectors beyond semiconductors.

## Recommended next test, not an implemented strategy change

Maintain shadow/paper **measurement** of sector breadth, longer-term regime, relative strength, and actual broker bid/ask/fills. Require evidence from multiple future sessions and unaffected symbols before modifying the automated executor. A no-trade outcome when the edge is unverified is preferable to forcing entries. Do not increase complexity or LIVE access without a separate owner decision.
