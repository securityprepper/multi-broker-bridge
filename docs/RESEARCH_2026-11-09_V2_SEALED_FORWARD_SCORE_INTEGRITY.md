# Nov 9 2026 — sealed forward-shadow scoring integrity (research only)

**No V1 PAPER/LIVE changes. No orders, Pushover, risk-gate changes, or changes to the already-installed read-only forward recorder.** The independent host snapshot service remains enabled and has not yet generated any new market-day observation. Holiday revision 2 was previously validated unpaused strictly before Nov 13 2026 16:13 America/Chicago unless invalidated.

## Issue found before first prospective market-day score

The installed GET-only recorder saves an observed input at **09:35:25 ET**, and its JSON field earliest_later_entry_at_ET is **09:40:25 ET**, not 09:40:00. Earlier historical 52-week simulations treated the **09:40 five-minute bar OPEN** as the +5-minute delayed entry. That trade mark actually precedes the recorder's asserted earliest entry time by **25 seconds**. This is a timestamp/execution-proxy mismatch, not a broker execution problem. A five-minute series cannot tell us the price at 09:40:25; genuine SIP/BOATS NBBO, order eligibility, quotes, latency, and real commissions are still missing.

For forward-only reporting, either use the first *independently observed executable quote at/after 09:40:25* (preferred), or, when restricted to 5-minute OHLC, use the **09:45 five-minute bar OPEN as a deliberately delayed trade-price proxy**. That proxy is not a fill and likely changes return distributions relative to earlier research. Avoid mixing old and new modeled returns as if entry timestamps matched.

A second data-integrity trap: the recorder writes its JSON with sort_keys=True, so the first features key in the semiconductor sector can be **AMD, not SOXX**. Scorers must map **sector name -> explicit sector ETF** rather than assume the first key is the sector mark. The new scorer uses this mapping, including GDX, XLE, XLF, XLI, XLV, and IGV.

The recorder currently labels time_of_observation_utc at service startup before two GET requests finish. Before calling an observation genuinely prospective, check that its sealed file creation and service journal attest to completion **before the first outcome target**; the file's self-declared timestamp alone does not authenticate that. Capture precise fetch completion/record creation timestamps in a separately reviewed recorder improvement. Do not rewrite existing sealed snapshots. A completed 5m trade bar still cannot certify bid/ask execution or short availability.

## New purely offline scoring code

- research/v2_score_sealed_sector_shadow_20261109.py — accepts pre-outcome snapshot dictionary and independently supplied post-signal five-minute bars; **does not connect to Alpaca or a broker**. Performs explicit sector ETF mapping, completion delay and exact-horizon checks, missing-data abstains, impossible OHLC/nonfinite/duplicate rejection, and separates signal-time direction (from observed price) from delayed-entry hypothetical 15/60-minute and 13:40 CT return. Assumed 30bp round-trip cost is labeled hypothetical. Also returns best/worst intratrade trade-bar excursions as **outcomes only**.
- research/test_v2_score_sealed_sector_shadow_20261109.py — ten offline tests for never-before-observation scoring, incomplete horizons, explicit SOXX-vs-AMD identity, 09:40:25 entry delay, missing bars, stale signal bars, duplicated/nonfinite/invalid data, abstention and no-order flags. **Ten tests passed locally**, November 9 2026; no actual future data exists yet.

The currently sealed research candidate remains only an exploratory **DOWN SOXX WATCH** (SOXX −0.75% to −1.5% from RTH open, AMD/MU/NVDA each at least −0.2%, recent completed five-minute SOXX <=−0.1%). Every other sector's recorded features are **descriptive**, not automatically scored as a predictive UP/DOWN forecast. Never turn a descriptive move into a retroactively invented prediction. The historical 6/9 later semiconductor shadow outcomes and 52-week grid are **not** untouched validation and justify no notifications or orders.

## Forward validation gate

First independently verify a SEALED snapshot is on disk and that the trusted holiday/session gate was satisfied at collection; count coverage and abstentions across all seven sectors. Obtain post-signal quotes afterward, without rewriting the sealed record. Score 15m/60m/13:40 CT outcomes, with data freshness, direction, tiny moves, loss tails, same-day upside and downside misses, MAE/MFE, after-cost hypothetical expectancy, and separately real executable spread/fill evidence. Accumulate >=30 unseen independent days per sector/side before any policy promotion. Require actual quote/borrow/commission evidence before any PAPER-only approval; no LIVE actions. Preserve the existing 13:15 CT latest-entry, 13:40 flat and 14:00 verification gates.
