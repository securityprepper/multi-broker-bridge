# V2 shock threshold: strict post-signal continuation replay, November 9 2026

**No V2 broker release, no LIVE/PAPER order placement, and no V1 monitor/exit modifications.** This is a read-only retrospective study designed to repair the important distinction between an OBSERVED sector shock and an ACTIONABLE prediction of additional movement.

## Date coverage and exact signal timing

Read-only Alpaca SIP split-adjusted 5-minute trade bars from **November 3, 2025 through November 6, 2026**, ~253 complete regular sessions (255 for GDX), using independent seven sector ETFs **SOXX, GDX, XLE, XLF, XLI, XLV and IGV** and anchored related sector stocks. No November 9 result is counted in this historical replay. Chronological earlier 70% / later 30% divides the data at July 22–23, 2026; the later ~76–77 days are already repeatedly exposed to prior research and MUST NOT be represented as a fresh untouched sample.

**RTH shock**: initial reference is that sector ETF's 09:30 ET RTH OPEN; a signal is available only at the close of a **completed** five-minute bar starting 09:30 ET, earliest 09:35 ET. A single first crossing and two-bar confirmation are distinct. **Night shock**: initial reference is the preceding completed 16:00 ET RTH CLOSE; check preceding SIP afterhours 16:00–20:00 and following premarket SIP 04:00–09:30. Unobserved BOATS 20:00–04:00 ET means nighttime events are undercounted. A closing trade can be a thin extended-hours print; no quote is guaranteed executable.

Thresholds **SOXX 2% day/3% night; GDX 2% both; remaining five sector ETFs 3% both**, symmetric UP/DOWN. First crossing only per sector/session/mode. Distinguish:

* **1-close**: first eligible five-minute completed sector ETF close beyond owner threshold.
* **2-close**: two adjacent completed ETF bar closes beyond same directional threshold (no missing intervening bars).
* **2-close+peers**: additionally at least two contemporaneous peer bar closes confirm the same direction, >=0.25% from peer's day OPEN (or preceding CLOSE for nights), timestamp lag <=10 minutes. For sectors with only two peer ETFs/stocks, both are required. A later peer close can never validate an earlier signal.

All directional scoring uses **the signal-time completed close as the baseline**, not yesterday's close, today's open, or an intrabar high. Count actual later signed price movement >=+0.05% as directionally correct; <=-0.05% as wrong; changes within +/-0.05% are separately tiny/flat and NOT credited. For BUY/SHORT models a signed gain **greater than illustrative 0.30% round-trip friction** counts as potentially profitable; short borrowing, inverse ETF tracking, spread at time and real brokerage commissions are NOT known. The row's simulated trading exit is **14:40 ET / 13:40 Chicago**, restricted to signals received no later than **14:15 ET / 13:15 Chicago**. This respects the user's entry and flat time restrictions but remains price-mark research, not actual executable orders.

## Chronological later-sample directional/post-cost replay

| Sector (ETF) | Completed-close daytime shocks / full history | Holdout cutoff-eligible breadth signals | Post-signal correct by 13:40 CT (≥0.05%) | >0.30% forward gain | Mean after 0.30% friction | Night signal correct to next RTH open |
| --- | --- | --- | --- | --- | --- | --- |
| semiconductors (SOXX) | 130/253 | 30/76 | 12/30 | 9/30 | -0.1681% | 13/19 (after30bp 13/19) |
| gold_miners (GDX) | 135/255 | 26/77 | 9/26 | 9/26 | -0.7706% | 23/40 (after30bp 21/40) |
| energy (XLE) | 8/253 | 3/76 | 1/3 | 1/3 | -0.4855% | 0/0 (after30bp 0/0) |
| financials (XLF) | 3/253 | 1/76 | 1/1 | 1/1 | 0.5261% | 0/0 (after30bp 0/0) |
| industrials (XLI) | 2/253 | 1/76 | 0/1 | 0/1 | -0.478% | 0/0 (after30bp 0/0) |
| healthcare (XLV) | 1/253 | 0/76 | 0/0 | 0/0 | n/a% | 0/0 (after30bp 0/0) |
| software (IGV) | 39/253 | 7/76 | 3/7 | 3/7 | 0.0615% | 2/4 (after30bp 1/4) |

Numerators above refer to **signals that were emitted causally**, not total winning days. Each later sample contains 76–77 covered dates. The daytime post-signal score is based on the first qualifying **two-close + breadth** event, with the owner-required 13:15 CT entry cutoff; night score uses first completed sector close at threshold and the next regular OPEN (which is only a descriptive outcome, not permission to hold a position overnight). All full day/session audits, including missing future price outcomes, bullish/bearish counts, first signal timestamp in America/Chicago, 15/60min continuations, next open, 13:30 ET, 13:40 CT and official RTH close, are in the machine-readable results.

### Material findings

- **No sector has established >=80% forward post-signal direction at useful volume**. Confirmed RTH SOXX breadth trade-window signals were directionally correct only **12/30** by the 13:40 CT flatten, and only **9/30** advanced enough to cover hypothetical 30bp friction (mean **-0.1681%**). GDX scored **9/26** at >=0.05% in the same direction and **9/26** exceeding 30bp, mean **-0.7706%**. These disconfirm using mere shock detection as an automatic sector BUY or SHORT.
- The broader first-completed-close shock mode detects **130/253 SOXX** and **135/255 GDX** RTH dates, less than previous high/low-touch counts (145 and 149). **Reversal and thin-price touches must not be called confirmed sector shock alerts.** Two bar confirmation reduces these respectively to 118 and 126 full-year dates; breadth confirmation to 114 and 126. Night earliest-completed-close counts are 55 SOXX and 126 GDX, vs prior high/low-night-touch reports 66 and 134.
- Semiconductors have a potentially interesting, BUT *small and incomplete*, night pattern: later 3% SOXX first-close signals moved in the same direction to the next open **13/19** times, and **13/18** for two-close/peer confirmation; both below 80%. Overnight model mark-to-open is NOT a qualified overnight executable trade, particularly with missing 20:00–04:00 BOATS prices and NBBO bid/ask.
- The other 3% sector thresholds are **extremely rare** in the most recent 76 regular sessions: day+peer trade-window opportunities energy 3, financials 1, industrials 1, healthcare 0, software 7. Even 1/1 directionally correct is not a validated 100% forecast. Owner levels are appropriate as factual unusual-move **WATCH** thresholds but should not be advertised as high-confidence advance predictions.
- 15m and 60m next-horizon metrics are separately saved, because the strong prior-close-to-close direction label says nothing about near-term continuation. A +/-0.05% flat/tiny tail is separately measured and excluded from direction successes.

### Outstanding AMD 03:18 CT missed early buy origin

Authorized **read-only** Nov 9 03:18 CT journal shows `trading-sector-paper-executor.service` started 03:18:40 CT, finished 03:18:41 CT with **7 sector BUY/EXIT candidates**, **gate_allows_new_entries=true**, and just two submitted PAPER buy attempts: **AVGO 6 shares** and **INTC 35 shares**. The old Nov 9 03:18 log JSON **does not include** `buy_watch_symbols` or `skipped_buy_reasons`. Thus **AMD omission cannot be reliably attributed** to cash, prior order, quote/staleness, exposure/sector lock, or filter from that historical journal. Do not guess or re-run dated market decisions with new state. Examine those diagnostic fields on the next eligible completed scan and join as-of quote freshness + account position/order + sector eligibility without exposing cash/credentials. Actual AMD paper MBB later bought four at $466.70 at 07:35 CT and sold $466.00 about two minutes later; retrospective earlier ask $457.95 at 03:18:40 does not prove an executable earlier fill.

### Deployment and risk verdict

All results are **research only** with the owner's holiday schedule/gates unchanged; host `/tmp` scratch only. The historical full-sample events have already influenced other research, so the chronological later slice must be confirmed in fresh prospective shadow data. Before any new PAPER emergency/noise alert or order strategy: fresh SIP/BOATS bid/ask at timestamp, no lookahead, out-of-sample >=20 eligible days per sector, false alert rates, actual post-signal afterfee returns, explicit short/inverse availability, position and working-order dedup, sector-wide caps, broker readbacks, separate PAPER-only approval, and unmodified LIVE barrier. Do not disable factual urgent existing-position risk protections. Never equate a single crossed price threshold with a profitable continuation or permission to trade.

## Research artifacts

- `research/v2_20261109_sector_shock_asof_future.py` causal seven-sector runner.
- `research/test_v2_20261109_sector_shock_asof_future.py` 11 passing as-of/forward/no-leak regression tests.
- `research/results/v2_20261109_sector_shock_asof_future_summary.json` complete full/earlier/later statistics for each sector, sign, horizon and mode.
- `research/results/v2_20261109_sector_shock_asof_future_events.csv` 1,475 dated signal events (plus header), as-of CT timestamp, signal-price reference, direction, 15/60-minute and fixed future horizons, cutoff eligibility.
