# Broadly positive semiconductor days: rebound, continuation, fresh uptrend (8 Nov 2026)

**Historical hypothesis test only. Do not enable as PAPER or LIVE order policy without independent forward validation.**

## Historical coverage
20 sampled trading sessions, 2026-10-12 to 2026-11-06, AMD/MU/SNDK/SOXX, authenticated Alpaca SIP and BOATS one-minute bars where available. Historical after-hours gaps in the broader lookback were supplemented by unofficial Yahoo one-minute bars; November 5 after hours uses authenticated Alpaca SIP. BOATS stock/ETF bars can be sparse. SOXX 3:1 split effective 2026-11-05 was adjusted in prior-close change calculations.

## Confirmed lesson: previous 8%/5% crash threshold is too narrow

November 3 was the previous broad up day before November 6. It returned AMD +3.82%, MU +2.64%, SNDK +4.77%, SOXX +2.50% from regular close to regular close. November 2's declines were AMD −7.61%, MU −5.84%, SNDK −6.46%, SOXX −3.81%. The 8%-two-stock and 5%-SOXX loss gate would miss Nov 3.

October 19 followed October 16 declines AMD −6.00%, MU −5.66%, SNDK −6.91%, SOXX −4.19%, and similarly missed original crash gate.

October 26–28 were **three consecutive up sessions**:
- 26th AMD +2.82%, MU +3.03%, SNDK +1.46%, SOXX +2.87%.
- 27th AMD +5.45%, MU +2.82%, SNDK +3.84%, SOXX +3.84%.
- 28th AMD +3.24%, MU +5.68%, SNDK +7.69%, SOXX +2.09%.
A solely crash-qualifying rule misses the second and third days.

## Three candidate regimes (chosen after examining sample; not validated)

1. **Rebound**: previous day at least two of AMD/MU/SNDK down >=4% and SOXX down >=2.5%; current day at least 2 stocks +1% versus prior close and SOXX >=+0.5%; 2 stocks rising >=0.5% over previous 30 minutes and SOXX nonnegative over 30 minutes.
2. **Continuation**: previous day at least 2 leaders >=+0.5% and SOXX >=+0.5%; same fresh trend/confirmation requirement, re-evaluated daily.
3. **Fresh positive reversal**: prior day neither rebound nor continuation, SOXX prior day between −2.5% and +0.5%; require current two leaders +1.5%, SOXX +1.0%, 30-min momentum confirmation.

The above are *filters for candidate bullish signals*; no rule guarantees the whole day will end positive. Stop only if historical freshness, spread and broker eligibility pass. Need avoid initiating new positions close to market open unless dedicated opening-structure logic supports them.

### First qualifying examples from descriptive bar analysis (Eastern time)
- Oct 19 (Sun evening Oct 18): broad positive around 8:46 PM ET, 30-minute momentum.
- Oct 21 (Tue Oct 20): broad positive around 4:48 PM ET; unclassified/neutral prior day.
- Oct 26 (Sunday Oct 25): broad positive around 8:30 PM ET.
- Oct 27 (Monday Oct 26): broad positive around 7:53 PM ET.
- Oct 28 (Tuesday Oct 27): broad positive around 11:48 PM ET.
- Nov 3 (Monday Nov 2): stronger rebound qualification as early as 6:12 PM ET (general broad positive 4:40 PM ET).
- Nov 6 (Thursday Nov 5): stronger rebound qualification as early as 4:36 PM ET (general broad positive 4:31 PM ET).

## Diagnostic mechanical simulation — risk of false confidence

An experimental model based on next-bar OHLC limit touches, <=$2,000 order size per each of four symbols, holding overnight, with a **simulated stop-market-like 1% trailing exit at 9:30 AM ET** and afternoon continuation reentries produced these numbers. Some earlier-session 4–6:30 PM ET buys are **not included in the trading replay**, which starts at 6:30 PM ET. Pre-open entry cutoff tested at 8:30 AM ET. Signals and execution estimates use different granular checks.

- Candidate rebound, relaxed 4%/2.5% prior-drop gate: Oct 19 −$19.75, Oct 23 −$103.02, Nov 2 −$134.50 if allowing entry 8:41 AM ET; Nov 3 +$91.04; Nov 6 +$443.34. Skipping all new entries after 8:30 AM ET suppresses Nov 2's late entry but is **a hindsight-tested restriction**.
- Candidate continuation: Oct 26 +$25.87, Oct 27 −$12.35, Oct 28 −$29.69, total **−$16.17**. Thus **triggers caught multiple consecutive up days but were not reliably profitable**.
- Candidate new-uptrend neutral-prior-day: Oct 21 +$9.56.
- With 8:30 AM ET entry cutoff, all three categories together (20 sessions) generated 35 simulated exits, **+$405.00** nominal aggregate: Oct 19 −$19.75; Oct 21 +$9.56; Oct 23 −$103.02; Oct 26 +$25.87; Oct 27 −$12.35; Oct 28 −$29.69; Nov 3 +$91.04; Nov 6 +$443.34. Positive sessions 3 vs losing sessions 4 plus Oct21 positive? actually positive 4: Oct21,26,Nov3,Nov6, losing 4: Oct19,23,27,28. The total relies heavily on November 6 and thresholds were selected using it. **Not a validated edge.**
- Across prior entries, some signs were early but paper prices might never have been fillable. Regular market opening OHLC cannot prove order of high and low or actual trailing-stop fill. A stop-limit can fail to execute. All hypothetical profits exclude direct market-quality / commissions / financing evidence.

## Recommendation

Maintain independent daily **regime signals**: crash rebound, first reversal after flat/down day, and multiday continuation, each with a fresh momentum gate. This avoids arbitrarily forcing every sector rise into a crash-only strategy.

**Do not deploy** these price/risk parameters until independent forward PAPER trials with actual broker acknowledgments and executable quote checks demonstrate success across diverse sessions, including the days following an uptrend. Compare one-minute detection with broader (15/30-minute) confirmation, and assess stock-level relative strength to avoid buying all leaders indiscriminately.

Model scripts and ephemeral data remain on the authorized www3 /tmp host; this document preserves findings, not scripts or credential material.
