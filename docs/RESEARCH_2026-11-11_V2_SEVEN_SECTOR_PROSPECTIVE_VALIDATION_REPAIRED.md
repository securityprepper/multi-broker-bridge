# November 11, 2026 — Repair of seven-sector prospective forward-signal test

## What was broken

The preexisting GET-only observer recorded correctly sealed as-of market features at three slots for seven sectors, but only one narrow exploratory semiconductor weakness condition could classify a sector. **Nov 10–11: six sealed time slots, 40 of 42 sector feature observations, two missing-data abstentions, zero ex-ante UP/DOWN forecasts.** Those days are **not** valid forecast-accuracy samples. Do not backfill their labels using already-known price outcomes.

## Repaired and deployed, effective first on November 12

The root-owned *research-only* recorder at `/opt/securityprepper/v2-forward-shadow` now uses `v2_sector_forecast_policy_20261111.py`, with frozen ID `v2-7sector-forward-baselines-20261111-r1`, SHA256 `430176393f92f89faf03544df5179a7831e7209213c1518a9d0312b547ba37e0`, valid from **2026-11-12** (ET). Every eligible scheduled slot (`09:35:25`, `09:45:25`, `10:05:25` America/New_York) freezes two independent research-only arms for each of seven sectors: (1) basic ETF-from-open direction threshold of +/-0.05% for **UP/DOWN**, otherwise **ABSTAIN**; (2) ETF >=0.10% plus at least 2 own-sector peers moving >=0.05% in the same direction (or **ABSTAIN**). These are **unvalidated control hypotheses**, not previously demonstrated profitable trading strategies. Each arm issues UP, DOWN or ABSTAIN, with separate precision and coverage.

The seven sector ETFs and own peers are SOXX/AMD/MU/NVDA, GDX/NEM/AEM/KGC, XLE/XOM/CVX, XLF/JPM/BAC, XLI/CAT/GE, XLV/UNH/LLY and IGV/MSFT/CRM. Only completed five-minute Alpaca SIP trade bars and five prior completed daily histories are accepted. Incomplete/late/future bars, missing peers or prior-five histories abstain/fail closed. The forecast records actual issuance **after** all GET responses, rather than falsely treating scan-start as issuance; late scans cannot seal a stale prediction. No pre-existing snapshot is modified, and files are created once with exclusive creation. The precise actual issuance clock, source bar completion, signal mark, policy ID/hash and abstentions are recorded. A false zero order/notification authorization cannot enter the policy.

## Separate future-outcome scorer

A separate pure-research GET-only scorer `v2_forward_shadow_score_20261111.py` is installed, and a **new independent** nonroot systemd timer `securityprepper-v2-forward-score.timer` is enabled/active for weekdays **14:50:25 ET (13:50:25 Chicago during CST)**, after the previously approved **13:40 CT flat**. It does not change the existing collector timer, research task recurrence, host V1 services, or any broker monitor. Both services run as `alpacafeed` with `NoNewPrivileges`, restricted capabilities, protected filesystem, and the existing sealed data-feed credentials provided by systemd only to the service; no credentials are written into results.

The scorer rejects all dates before November 12 and all version-1/backfilled/mismatched forecast snapshots. It reads the *original* sealed forecast hashes, obtains afterward-only completed five-minute SIP marks and writes **separate one-time immutable result files** under `/var/lib/securityprepper-v2-forward-shadow/scores/YYYY-MM-DD/1340CT.json`. Outcome comparisons use the signal-time observed ETF mark as baseline, never previous-close-to-future-close. The nominal 60-minute horizon is evaluated at the **first fully completed five-minute bar no earlier than actual forecast issuance + 60 minutes**; the other endpoint is the actual 14:40 ET completed bar (13:40 CT). Flat/tiny (<0.05%) moves are not hits. The score file retains signal and end timestamps/prices, raw signed forward return, UP/DOWN correctness, misses, abstentions, missing outcomes and illustrative 30/60 basis-point friction and modeled winners. Two forecast arms are evaluated separately for each sector and slot; **up to 84 directional forecast/horizon result rows per complete market day**. It fails closed on invalid calendar status or provider data.

The active read-only holiday-gate reference is revision 2, unpaused, valid strictly before **2026-11-13 16:13 CST** absent revision/calendar edits; services use the trusted pre-existing host cache and make no market GET requests if the gate is paused or invalid.

## Verification and limitations

All **39 offline tests passed** on isolated scratch, including synthetic forward-only full-capture/outcome integration; late-issuance rejection; both arms in all seven sectors; no future bar leakage; no backfill; absent data; 60-minute actual-issuance timing; holiday fail-close; immutable source vs outcome separation; absence of broker-order/Pushover interfaces. Root-owned research deployment and the new scorer timer were smoke-checked outside market slots with **zero market-data requests, zero orders**; both collector and new scorer timers were confirmed enabled and active. The existing collector timer remained unchanged, and no V1 PAPER/LIVE systems, IBKR Gateway, brokers, stops, order routes or trade permissions were modified.

**Test validity is now prospective, NOT historical predictive reliability.** First qualifying observations can start Nov 12 subject to holiday/data; no post-signal win rate is yet verified. Real quote/offer spread, slippage, actual fills, borrow eligibility, brokerage fees and 20–30+ genuinely untouched future dates remain necessary before assessing an actual trade hypothesis. The 30/60 bp deductions are *illustrative* only; no new PAPER/LIVE trading strategy is approved, and no user-facing predictive alerts are authorized. Previous repeatedly tested price-only continuation families remain **NO GO**. The two newly frozen simple baselines are controls to measure observational predictive power, not resurrections of unprofitable trading signals.

## Files

- `research/v2_sector_forecast_policy_20261111.py`
- `research/v2_forward_only_sector_shadow_20261109.py`
- `research/v2_forward_shadow_score_20261111.py`
- `research/systemd/securityprepper-v2-forward-score.{service,timer}`
- `tests/test_v2_frozen_forecast_independent_20261111.py`
- `tests/test_v2_frozen_capture_score_integration_20261111.py`
- `tests/test_v2_seven_sector_forecast_and_score_20261111.py`
- `research/test_v2_forward_only_sector_shadow_20261109.py`

These are research-only changes on `research/rebound-v2-conditional-exits`. No automatic change to trading strategy V1 is warranted.
