# V2 Research — AMD 21-session breadth and anti-churn replay, November 9, 2026

**RESEARCH ONLY — no V1 PAPER/LIVE monitor changes, broker orders, timer changes, or strategy activation.** The validated holiday revision-2 cache remains unpaused strictly before November 13, 2026, 16:13 America/Chicago, absent explicit invalidation.

## Priority: actual movement AFTER a signal, not prior-close-to-close labels

The earlier 88–95% sector-direction scores cannot be represented as future-movement prediction accuracy. This new AMD-specific experiment uses 21 completed market dates (October 12–November 9, 2026), including the actual November 9 completed session, but **November 9 was already known when constructing these policies** and is not a fresh untouched forward holdout. The 20 preceding days are SIP one-minute historical trade bars; November 9 was fetched read-only as one-minute Alpaca SIP trades. Do not publish the source paid bar payload. A vendor raw-versus-split daily comparison shows a 3:1 SOXX historical adjustment, handled as normalization, not an outcome classifier.

As-of **08:35 ET / 07:35 Chicago**, use only complete 08:34 one-minute trades and previous completed-session close: require SOXX same-direction >=0.2%, AMD same-direction >=0.2%, and 2 of AMD/MU/SNDK same-direction >=0.2%. A selective gate also requires positive 5-minute momentum for AMD and SOXX and at least 2 of the three peer stocks, using complete 08:29 vs 08:34 observations. The model enters AMD at the 08:35 ET OPEN proxy if that bar exists, not at a retrospective low. All exit rules inspect only completed one-minute bars, fill at the NEXT one-minute OPEN if present, and enforce final exit at **14:40 ET = 13:40 Chicago**, 20 minutes ahead of the 2 p.m. owner ceiling. DOWN entries are theoretical shorts and have **no verified short eligibility or borrow costs**.

Stop policies:
* Tight 1-minute stock and sector pullback: AMD <=-0.10% and SOXX <=-0.05% in trade direction, completed last minute.
* 1% target / stop from entry price.
* Hard entry-adverse -2.5%, with separate stock adverse >=2.5% from previous close **including** >=1.0% last15m (never additive).
* Trend-aware stop: hard/overlap emergency first; otherwise AMD 5m adverse >=0.25%, SOXX 5m >=0.15%, and >=2/3 peers each >=0.10% adverse in completed 5m.
* Same trend rule with one cool-down >=15m and fresh 2/3+5m positive confirmation reentry by 13:00 CT, then full 13:40 CT liquidation.
* Unprotected hold only as an **unsafe reference**, never a proposed V1 policy.

## Measured later movement

21 historical dates audited: 9 bullish forecasts, 9 bearish, 3 abstentions. One missing exact 08:35 fill among the 18 forecast dates yields **17 eligible modeled positions**: 9 long and 8 hypothetical short. The following figures are **per-original-day AMD direction-signed post-signal returns**, after **illustrative** 0.30 percentage points round-trip friction, not observed executable bid/ask or PAPER fills.

| Policy | After-30bp winning days | Mean net per entered day | Worst day net | Fixed-notional sequential drawdown (percentage points) |
|---|---:|---:|---:|---:|
| Tight 1m reversal | 2/17 | **−0.3391%** | −0.7093% | −5.765 |
| +/-1% target/stop | 11/17 | +0.0377% | −1.5215% | −6.749 |
| Completed 5m sector-breadth weakness + hard protection | 5/17 | +0.0520% | −0.8619% | −4.714 |
| Above with one fresh-confirmation reentry | 4/17 | +0.1926% | −1.6758% | −7.796 (34 tickets vs 17) |
| Hard -2.5% emergency/entry protection | **12/17** | **+1.5079%** | **−3.0123%** | **−5.848** |
| Unprotected hold to 13:40 CT | 12/17 | +1.3816% | **−7.6561%** | **−8.051** |

The single largest observed intratrade adverse move in the unprotected group was approximately -7.44%; even protective models have gap/slippage uncertainty. At 0.60 percentage points friction, the one-reentry average changes to **−0.4074%** per original day, showing high sensitivity to extra executions. These are one AMD stock, selected using known historical data, with the DOWN side hypothetical. There is **no 80% after-cost profitable hit-rate or release GO**.

Adding the strict improving-5m entry qualification reduced entry opportunities from 17 to **4**. Just **3/4** were net-positive under hold, including November 9; 9 profitable breadth-only held days were rejected. This is far too small to promote as a precision improvement.

Importantly, the 248-day cross-sector five-minute studies already found trailing-stop and reentry variants less stable, with worse net outcomes and significant tail drawdowns. Do not generalize the favorable 21-day AMD hold subset to all semiconductor/sector stocks or to a verified overnight/PAPER strategy.

## November 9 retrospective — no fill replay as a live order

A completed 08:34 ET SIP bar showed SOXX +1.28% from previous close, AMD +3.93%, MU +0.94%, SNDK -0.40%; therefore **2/3 stock breadth** qualified even while SNDK was weak. Complete preceding-five-minute change: SOXX +0.28%, AMD +0.47%, MU +0.24% (also qualifies selective gate). AMD's later 09:39 ET bar was already +5.88% from the previous regular close, but **the unobserved remaining 09:40–14:40 ET market-price change was another +7.39%**, using the 09:40 and 14:40 minute OPEN trade marks. That gain is meaningful future movement after the later observation, not the already-realized move.

The real matched PAPER AMD entries/exits and dollars are held privately in the authorized broker task audit, not duplicated into this public repo. A separate read-only broker FILL-audit service journal confirms the previously unexplained FILL activities were all associated with the independent FDR order family, not an unidentified third family in the audited set. The timing of any still-working orders and cross-strategy idempotency remains separately reviewable. No order was placed or modified by this research.

For the modelled November 9 AMD 08:35 OPEN proxy: tight one-minute exit at 08:37 ET was negative after 30bp, five-minute trend-aware exit was at 10:03 ET with gross +4.29%, and a protected 2.5% stop did not trigger before the final 14:40 ET open. A second 10:28 ET reentry following trend-aware exit lost money after its own round-trip friction; it was not a clear improvement. A no-stop hold from model entry was +9.35% gross, but this is hindsight and not an automatic order or verified quote.

## Independent event timing / screening
The official RB Global November 9 earnings were scheduled before the market opened, with the 08:30 ET earnings call, so any same-day RBA signal must account for the timestamp of the released information and its subsequent price changes, not treat end-of-day results as premarket forecasts. Prioritized standalone PWR, GS, CAT and RBA screening is **not yet independently validated by this AMD-only experiment**. News and market-event timestamps are not included as signal inputs here.

## Controls and remaining limitations
* 9 new offline unit tests passed, including same-day future-bar perturbation, 2.5%-including-1%-in-15m semantics, next-minute exit time, cool-down, and hard 13:40 CT flat. Full 21-day decision audit and aggregate event outcomes stored in the branch under `research/results/v2_amd_21session_breadth_antichurn_2026-11-09.json`.
* The research scans historical prices after the chosen as-of time only for **outcomes**; no future prices used as signal inputs. Historical inputs have gaps. Missing marks abort entry or suppress stop checks; results may have survivorship/data-gap bias.
* SIP/BOATS trade bars are not executable NBBO. Spread, fees, market/limit execution probability, order latency, gaps and available borrow for shorts remain uncertain.
* The real MBB AMD morning PAPER trade was premarket. A true strategy must preserve session eligibility, verified exposure/working-order reconciliation, protective exit effectiveness and 2pm Chicago final-flat watchdog, and never inherit overnight exposure.
* **GO/NO-GO: NO-GO.** Candidate work is on separate V2 research branch only. Next evaluate fully independent chronological forward days, broader semiconductor constituents and other rising sectors, and quote-based execution. Preserve the existing V1 PAPER/LIVE and all orders.

## Research files
* `research/v2_amd_breadth_antichurn_21session.py`
* `research/test_v2_amd_breadth_antichurn_21session.py`
* `research/results/v2_amd_21session_breadth_antichurn_2026-11-09.json`
