# Seven-sector forward shadow — valid prospective forecast/score capture commissioned (November 11, 2026)

## Issue and correction

The original GET-only observer sealed market features for seven sectors at 09:35, 09:45 and 10:05 America/New_York but only a rare exploratory semiconductor bearish condition could populate `shadow_classification`. On Nov 10–11, six sealed observations contained 40 complete sector features, two missing-as-of abstentions, and **zero issued UP/DOWN predictions**. The older snapshots have **not** been retroactively classified; no historical predictions are invented.

A frozen versioned **research-only** policy now issues, separately for each of the seven sector ETFs and each slot:

- A low-threshold ETF direction *benchmark* (UP / DOWN / ABSTAIN, fixed ±0.05% observed ETF movement from that day's RTH open).
- An independent **ETF-and-peer confirmed** arm (ETF magnitude at least 0.10%, and at least two preselected own-sector peers each moving at least 0.05% in the same direction, otherwise ABSTAIN).
- Explicit fail-closed abstentions for missing, malformed, future/incomplete bars, or absent preceding five complete RTH sessions.
- A unique immutable policy ID and SHA256, source-bar-completion timestamp, **actual decision issuance timestamp sampled after GET completes** (no stale scan-start backdating), observed ETF price, side, reason and account-independent research permissions. The older semiconductor watch is preserved separately, not misrepresented as an independently verified BUY/SHORT.

Policy `v2-7sector-forward-baselines-20261111-r1` becomes effective **Nov 12 2026** and is frozen for prospective evaluation; the threshold choices are fixed research benchmarks, **not established profitable trading rules**. It never authorizes notifications or broker orders. The collector retains exclusive write-once `YYYY-MM-DD/{0935,0945,1005}.json` seals; prior Nov 10–11 schema-v1 files are unchanged.

## Independent after-outcome scorer

A separate root-installed **read-only** `securityprepper-v2-forward-score.service` and enabled timer, running **14:50:25 ET (13:50:25 Chicago)** on weekdays, scores only already-issued schema-v2 forecasts from that day. This new timer did **not** change the existing GET-only capture timer or any V1 timers. It requires the trusted fail-closed holiday gate and current frozen policy hash; the Nov 11 pre-effective-date run skips without accessing a market feed.

The scorer GETs Alpaca SIP **completed 5-minute trade bars only** after the owner 13:40 CT model exit. Signal marks are the ETF price as of the completed bar at the original decision, not previous RTH close. Outcomes are fixed **60 minutes after the decision** and **14:40 ET = 13:40 Chicago**, both strictly future to the real issuance timestamp. It writes a separate exclusive immutable `scores/YYYY-MM-DD/1340CT.json` document with original seal SHA256 hashes, daily per-sector/slot/arm UP, DOWN or ABSTAIN, signed post-signal returns, direction HIT/MISS, missing and tiny movement categories (tiny <0.05% is not a hit), and illustrative 30/60bp cost-adjusted mark results. It cannot edit forecast seals. Costs are illustrative; quote-level executable NBBO/actual fills/commissions are **not** certified by this forecast research.

**Never count three same-date slots as three independent prospective trading days.** Aggregate chronologically by distinct trading date and evaluate at least 20–30 untouched days before deciding predictive validity; do not optimize the frozen policy mid-study or count forecasts that were never issued. Forward direction accuracy is distinct from after-spread/after-fee trade profitability. This change commissions **research observation only**, not a new PAPER/LIVE strategy.

## Verification and scope

- Confirmed on authorized `www3.securityprepper.com` that both `securityprepper-v2-forward-shadow.timer` and `securityprepper-v2-forward-score.timer` are **enabled and active**; existing capture times remain unchanged.
- Tested the **installed** source paths with 39 deterministic offline unit/integration tests, including issuance after GET, all seven sectors, paired forecasts, as-of exclusions, invalid/unfinished bars, five prior sessions, holiday fail-closed, late issuance, original-file write-once, no score before future availability, matched fixed future marks, costs, score dedup, and rejection of schema-v1 seals.
- Manual `systemctl start securityprepper-v2-forward-score.service` smoke at 10:xx CT Nov 11 exited successfully with `NOT_SCORE_TIME`, **0 data requests and 0 orders**; no outcomes were written prematurely.
- Existing validated holiday cache was unpaused revision 2 with `next_check_at=2026-11-13T16:13:00-06:00` when inspected, strictly in the future. No calendar edit or invalidation was observed.
- No IBKR Gateway, Alpaca PAPER/LIVE or Robinhood broker positions/orders, V1 execution, protective controls, 13:15 entry cutoff, 13:40 flat, 14:00 verification, or existing scheduled tasks were changed. No Pushover alert or automatic trade was emitted. The separate recommendation-PAPER router remains disabled.

**Readiness:** The instrumentation is installed and validated against synthetic scenarios, but **no** 20–30-day fresh forward sample or profitable trade precision has been established yet. First qualifying live research-only forecast is expected in the first eligible Nov 12 slot if fresh market data and holiday gates permit; the first eligible after-outcome score is expected at 13:50 Chicago that day. Actual capture and scoring must be verified from the resulting immutable files, rather than assumed from timer state.

Sources: `research/v2_forward_only_sector_shadow_20261109.py`, `research/v2_sector_forecast_policy_20261111.py`, `research/v2_forward_shadow_score_20261111.py`, and tests in `research/test_v2_forward_only_sector_shadow_20261109.py` / `tests/test_v2_*20261111.py`. Host-only systemd units `securityprepper-v2-forward-score.{service,timer}` contain no broker order interface.
