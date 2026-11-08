# Five completed-session semiconductor rebound: PAPER implementation and historical news review
_2026-11-08. Research results and installed host state must be distinguished from broker-confirmed fills._

## Numerical correction

- **94.4% (34/36)** was the *premarket sector up-direction* alignment among all bullish-signal days. It is NOT the proportion of profitable trades, NOT restricted to five-day downtrends, and is partly mechanically implied by the detector's already-observed premarket momentum.
- Exact historical prior-five-completed-day downtrend subgroup: **19 active session dates, 16 profitable (84.2%)**, 3 losing, using modeled nine-symbol PAPER purchases and hypothetical 8:30 AM ET extended-hours exits at 0.15% per-side execution allowance.
- Three losing modeled days: **2026-02-05 −$758.66**; **2026-03-04 −$5.57**; **2026-08-12 −$19.39**. No broker fills demonstrated.
- The 19 days used a strictly causal five-day sector category: from prior session's regular close back to the regular close six trading sessions earlier; current day excluded.
- Moving the historical exit from 8:30 ET to 8:20 ET degraded to **13/19 profitable**, underscoring timing sensitivity. The installed candidate's exit window was therefore aligned with the originally tested **8:30 ET**.

## Installed PAPER-only strategy

The authorized www3 host now has separately installed:
- `multi_broker_bridge/five_day_rebound.py`: causal pure signal decision. Requires previous five-day sector DOWN: >=2 AMD/MU/SNDK declining, SOXX declining. Then at least two stocks +1.5% above previous regular close, SOXX +0.75%, at least two leaders +0.7% over 15 minutes, SOXX nonnegative momentum, plus two leaders' completed five-minute close above the preceding bar high.
- `multi_broker_bridge/paper_rebound_runner.py`: independent PAPER-only Alpaca runner using restricted loaded broker credentials, accepted trade-date controls, day limit orders, accurate instrument tradability, restricted quotes (<=0.3% spread, <=75 sec age), $2,000/order and maximum $18,000 aggregate new purchases, broker inventory, reserved unique PAPER order IDs, previous-trade broker reconciliation, holiday gate and 8:30 AM ET premarket limit exit management. After unfilled premarket exits, broker readback/cancellation is required; an opening regular-hours market fallback is attempted only after cancellation and broker clock verification. No claim the exit WILL fill before opening.
- `trading-five-day-rebound-paper.timer`: an enabled independent systemd timer running every minute at second 12. Distinct from the existing generic PAPER sector executor (running at second 40) to preserve the unrelated uncommitted safety work.
- `Task - Five-Day Rebound Alerts`: enabled hourly ChatGPT notification watch with read-only host lookups. **Delivery is hourly (ChatGPT maximum automation frequency), not instantaneous.** Host-side `BULLISH_ALERT` events are recorded immediately in the strategy's private SQLite state; user-facing alerts are delayed until the next task check.
- Tested 8 Python unittest safety/scheduling checks on host. The unit was manually started on Sunday afternoon, returning `SESSION_CLOSED`. PAPER account readback before installation showed ACTIVE / unblocked and zero held positions or open orders. **No accepted strategy buys, live broker fills, premarket exits or next open run had yet been verified.**
- Only Alpaca PAPER connected/commissioned for this strategy; IBKR PAPER NOT enabled by this change, no LIVE orders or modifications.

## What caused the three historical misses?

- **Feb 5, 2026:** severe negative overnight continuation after prior-evening bullish alert (Feb 4 16:30 ET). AMD's just-reported earnings/near-term revenue outlook were under scrutiny, and multiple negative AMD-specific stories existed before the alert. Prior five-day AMD −20.79%, MU −12.84%, SNDK +10.79%, SOXX −8.34%, substantial stock dispersion. A hard "three leaders all declining during previous five sessions" filter would remove this loss, but also **miss three profitable signals** out of 16. A >30% previous-five-day relative dispersion veto would remove Feb5, but **also miss profitable Feb6** (dispersion 30.51%), so it does not meet the user's no-missed-winner condition.
- **Mar 4, 2026:** only −$5.57, stocks diverged; geopolitical oil-price/war uncertainty and memory-stock weakness appeared in prior-night coverage, while other semiconductor news was positive. No generic reliable exclusion is established.
- **Aug 12, 2026:** only −$19.39, scheduled 8:30 ET CPI report known well before 4:20 ET signal. This is useful as an *economic-release execution risk* tag, but not a valid claim that an early positive semiconductor signal was wrong. Had all 19 events been exited at 8:20 ET instead, win count would fall from 16 to 13. Avoid blindly changing exit timing for every day.

## Timestamped news test — 19 candidate signals

Alpaca authenticated historical news API `/v1beta1/news` was queried for the **24 hours preceding each of 19 signal timestamps**. 19/19 episodes fetched completely, storing article IDs, symbols, publisher source, headlines, created and updated timestamps in a private /tmp study file. Only articles created and last updated **by the signal time** were used; later revised headlines were not backdated. These cover Benzinga-style tagged stories and are NOT a comprehensive macro/global news archive. Each episode averaged tens of articles.

Applied basic negative-word headline heuristics to classify symbol-specific vs cross-sector news in 4, 12, 24 hour windows. This is illustrative, not a trained NLP classifier and parameters were studied after outcomes:
- **Any negative sector-tagged article in previous 12 hours** would remove **1 losing day but also 10 winning days**, damaging profitable-day recall.
- **At least three negative symbol-specific headlines in preceding 24h** would remove **1 losing day but also 3 winning days**; still two losing days remain.
- The Feb5 AMD earnings episode clearly differed from a routine no-news rally; Nov6 also had numerous negative sector headlines at its Thursday evening trigger and was a +$725.10 modeled winner, so treating negative sector sentiment as a blanket buy veto would reject the best rebound.
- The **8:30 ET CPI** on Aug12 had not yet occurred at the 4:20 ET signal. The release was a scheduled-event execution hazard rather than actual contemporaneous bad news.
- Need further *time-causal*, out-of-sample tests with economic announcements, company earnings surprise/guidance, Asia chip markets and market-wide futures; do not assert news makes trades nearly 100% profitable.

## Bearish direction clarification

- **80% (36/45)** was bearish *premarket direction already observed* among bearish signal days with complete phase data. It is NOT the number of profitable SOXS buys, nor the rate after five rising days, and is partly built into the bearish signal.
- Directly buying inverse leveraged SOXS under the prior bearish sector rule yielded **17/46 modeled winning days (37.0%)**, −$947.02 hypothetical full-year P/L, at 0.15% assumed per-side execution allowance. After prior five-day **rising** trend: 9/19 winners (47.4%); after prior five-day **falling** trend: 6/22 winners (27.3%).
- The current bearish rule is better as an AVOID LONGS / WAIT / potential reversal alert than an automatic SOXS paper strategy. Additional SOXS-specific rising-candle/breakout checks did not yield a profitable historical rule. A falling premarket often rebounded at the regular open (17/36 previously falling premarkets reversed up regular hours).

## Future measurement

1. Verify actual next PAPER session via broker order readback, limit acceptance, partial fills, end-of-session flatness; no claim of completion until broker confirms.
2. Distinguish PAPER buys and early exit fills from the model's OHLC-touch assumptions; monitor slippage, spread and missed orders.
3. Keep the negative-news and economic-calendar rules as research annotations, not automatic blocking filters without a successful out-of-sample experiment.
4. Check for simultaneous use of other PAPER strategy and broker exposure; isolated runner avoids modifying existing executor, but all Alpaca PAPER orders share the same account inventory.
