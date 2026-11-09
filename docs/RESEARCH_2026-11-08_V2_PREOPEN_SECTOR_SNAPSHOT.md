# V2 two-sided preopen SOXX and peer breadth snapshots — November 8, 2026

**Research only.** No broker connection, PAPER/LIVE orders, V1 monitor modifications, or runtime deployment. This experiment is an *additional candidate signal*, not a redefinition or replacement of the owner's 2.5% previous-close decline **including** 1 percentage point in 15 minutes rule.

## Objective and causal protocol

Can synchronized semiconductor breadth at **08:30 ET** or **09:15 ET** warn of large moves even when the individual stock has not met the original fifteen-minute momentum conjunction? Test both upside entries and downside exits symmetrically over the same completed 52-week sample.

Use only split-adjusted Alpaca SIP **completed five-minute bars** at 08:25 or 09:10, respectively, and the preceding **completed** regular-session close at 15:55 ET. At each fixed checkpoint, require all nine symbols to have bars and prior closes (otherwise fail closed). A signal needs:
* SOXX moved at least **0.5%** from prior close in the direction of the candidate;
* at least half of the eight semiconductor peers (excluding the target stock, so seven other peers for a constituent) also moved at least **0.5%** in that direction;
* the target stock itself moved at least **1%** in the same direction.

These were prespecified exploratory thresholds; no outcome labels, later bars, or future regular close enter any signal. Each stock-day receives at most one candidate per direction, taking its first qualifying checkpoint. The original **down** comparison uses the prior-close 2.5%-total/1%-in-15-minute premarket-or-eligible-evening alert; the comparison **up** baseline mirrors this condition with the sign reversed. Friday evening is *not* treated as Monday's immediately preceding evening. When both rules fire, the union counts the stock-day once.

A qualifying preopen signal is scored against the actual **same-day regular 15:55 five-minute close** and against 09:30 open, using a hypothetical following five-minute opening print, 30bp limit envelope and 15bp adverse price markdown per side. If that next-bar opening print is beyond the limit, the modeled candidate remains **unfilled** (zero incremental gain/loss); missing prices are unscored. This is a price-mark scenario, **not an NBBO or broker-fill backtest**. The benefit at the close compares an immediate preopen sale with a hypothetical sale at that day's close (down), or preopen buy with sale at close (up). It does not establish appropriateness for existing positions or a completed strategy return.

## Full 52-week review: 2,244 stock-days, 2025-11-10–2026-11-06

| Family | Original preopen: major / nonmajor warnings | New breadth: major / nonmajor warnings | Union major hits / total major | Extra major hits from breadth | Extra nonmajor warnings |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Upside** | 88 / 165 | **193 / 598** | **204 / 254** | **116** | **476** |
| **Downside** | 81 / 127 | **143 / 474** | **155 / 209** | **74** | **392** |

"Major" means a **+5% or -5% close-to-close** outcome in the relevant direction. A nonmajor warning means no 5% closing move; some could still yield an executable trade gain, so nonmajor is **not interchangeable** with losing trade.

The full union would have detected **155/209 (74.2%)** severe downside stock-days rather than 81/209 (38.8%) for the strict preopen rule, but produced **519 nonmajor downside warnings** rather than 127. For upside the union detected **204/254 (80.3%)** major up stock-days rather than 88/254 (34.6%), with **641 nonmajor upside warnings** rather than 165.

Breadth alone captured only **103** of the 209 severe down stock-days *before the stock was already down 5%*, and **147** of the 254 severe up days *before the stock was already up 5%*. Timely protection and profitable entries are therefore materially less common than simple end-of-day hit counts imply.

### Modeled bounded price advantage against same-day 15:55 close

These averages include zero effect when the next-bar 30bp envelope is not eligible; they **do not** establish fills. Positive for a downside alert means earlier exit saved value versus remaining long to close; positive for upside means a preopen entry would have gained versus same-day exit.

| Period | Up signal, mean pp | Down signal, mean pp |
| --- | ---: | ---: |
| Earlier through Aug 31, 2026 | **-0.2087** | **-0.3372** |
| Later Sep 1–Nov 6, 2026 | **-0.6056** | **+0.5736** |
| All | **-0.2840** | **-0.0903** |

Among future-price-scorable warnings, only **753/786 upside** and **577/616 downside** next-bar marks met the modeled bounded-limit price envelope, even before depth, latency, quote and session eligibility considerations. When restricted to those price-eligible marks, the hypothetical mean benefit to 09:30 is **+0.0506pp upside** and **+0.1176pp downside**, which is far too little on its own to justify an execution engine.

**Interpretation:** Broader preopen breadth increases detection sensitivity but incurs substantial false alarms and negative full-sample modeled same-day results. Performance differs sharply across the earlier/later split. It does **not** support automatically buying rising sectors or liquidating positions on every sector snapshot.

## Critical missed crash: Monday November 2, 2026

At **08:30 ET**, SOXX's completed 08:25 bar was **+0.92%** versus Oct 30 regular close; at **09:15 ET** its completed 09:10 bar was **+1.41%**. Most other semiconductor peers were also **up**. Nevertheless, SOXX ended **-3.80%** and large individual declines occurred:

| Stock | 08:25 ET | 09:10 ET | Regular close |
| --- | ---: | ---: | ---: |
| AMD | +1.00% | +1.65% | **-7.61%** |
| MU | +1.12% | +1.16% | **-5.84%** |
| SNDK | +0.59% | +1.03% | **-6.46%** |
| WDC | +1.13% | +1.54% | **-7.47%** |
| INTC | -1.35% | -0.12% | **-8.95%** |

At those fixed preopen checkpoints, a price-only sector **downside** signal was absent; an **upside** signal would have been misleading on several stocks. This exposes a specific blind spot: reversal after premarket strength, not merely failure to choose the right decline threshold. Existing completed-bar intraday reversal studies generated first downside alerts later: WDC **09:50**, INTC **10:45**, AMD **10:50**, SNDK **10:55** ET; MU had no 09:45–13:00 qualifying downside candidate. These are post-open warnings and should **never be represented as preopen detection**.

Before-open protection on such days will require truly earlier, timestamped non-price evidence (news, events, futures/cross-market positioning) or an explicitly accepted inability to warn. Do not claim hindsight observations as an earlier live signal.

## Validation, boundaries, and next research

* All **84 research unittest cases passed**, including **11 new** tests for side symmetry, missing peer data, fixed as-of timestamp, future price exclusion, sector confirmation, weekend boundaries, and modeled limit eligibility.
* Canonical V2 branch: `research/rebound-v2-conditional-exits`; code: `research/v2_premarket_sector_snapshot.py`; tests: `research/test_v2_premarket_sector_snapshot.py`; structured output: `docs/RESEARCH_2026-11-08_V2_PREOPEN_SECTOR_SNAPSHOT_RESULTS.json`.
* Reproduce with `python3 -m research.v2_premarket_sector_snapshot --output /tmp/v2_preopen_sector_snapshot_results.json` using the three read-only existing historical input files under `/tmp/semis_*adjusted.json` and `/tmp/semis_52weeks_alpaca_daily.json`.
* Prior two-sided sector-day classification remains **118 positive, 83 negative, 49 mixed**, but this experiment is scored on 9-symbol stock-days rather than reclassifying sector days.
* No full-year synchronized NBBO/BOATS overnight quotes, broker fills, live order queue depth, verified latency, futures, or timestamped earnings/news were available. The data are semiconductor-only and thresholds are observational, not independently validated across sectors. A hypothetical five-minute opening price is **not a guaranteed fill**.
* Next research: test separate post-open reversal/overnight gap detection and cross-sector confirmation without hindsight; record all missed up/down days and actual next regular open; validate against contemporaneous NBBO quotes and held-share PAPER shadow execution before considering order placement.

**V1 PAPER/LIVE monitors, production checkout, broker positions and orders remained untouched.** The research host used a separate clean temporary clone rather than resetting or overwriting the divergent local V2 checkout.
