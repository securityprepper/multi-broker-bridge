# Thursday-evening semiconductor reversal research — November 8, 2026

**RESEARCH ONLY — NOT A COMMISSIONED OR PROVEN TRADING STRATEGY. No deployed PAPER behavior or schedules were changed by these tests.**

## What was tested

- Sessions ending October 12–November 6, 2026: **20 weekday trading sessions**.
- Historical Alpaca one-minute SIP (after hours, premarket and regular) and BOATS (overnight) data for AMD, MU, SNDK and SOXX. Most 4–8 PM ET historical after-hours bars in this lookback were filled with **Yahoo one-minute data where the cached Alpaca response did not include them**; **November 5 4–8 PM ET was overwritten with authenticated Alpaca SIP bars**. Marked as mixed-source data. OHLC bars do not prove executable quotes or fills. SOXX had sparse BOATS bars on many nights.
- **SOXX 3:1 split, effective November 5, 2026**: previous-session comparisons that straddle the split were adjusted by dividing the November 4 SOXX close by 3. Source: SEC prospectus supplement, https://www.sec.gov/Archives/edgar/data/1100663/000119312526430480/d156277d497.htm
- Initial historical source files / scripts are on authorized www3 in /tmp, including `sector_complete_20session_alpaca_mixed.json`, `amd_crash_rebound_20session.py`, `amd_crash_rebound_preopen_20session.py`. Paths are ephemeral scratch, not deployed production code.
- All times in this report are **US Eastern Time**, not Chicago. 7:24 PM ET Thursday = 6:24 PM CT.

## First observable signal Thursday, November 5

The rule identified a possible buy **7:24 PM ET Thursday** after a severe prior-session sector decline, based on:
1. AMD, MU, SNDK all >=3% above the prior 3:59 PM ET regular-session closes.
2. SOXX >=2% above its own regular-session close.
3. At least two leaders up >=0.5% over the previous 30 minutes, with SOXX positive over the same interval.
4. Buy at a *simulated* marketable limit: previous completed minute close ×1.0015, whole shares with independent <=$2,000 notional.

Friday's resulting modeled entries:
- 4 AMD at **$415.56**;
- 2 MU at **$682.12**;
- 2 SNDK at **$840.08**;
- 14 SOXX at **$133.77**.

These are **backtest-selected, hypothetical fills**, not actual Alpaca order fills.

## Two exit approaches, same Thursday evening entry

**A. React to short-term weakness**: an individual decline from recorded peak, confirmed by a negative 15-minute SOXX move; use a next-minute synthetic limit. An exit at 1.25% pullback gave **−$24.42 on the Friday session** after multiple trades/reentries, as the rule repeatedly lost the larger bullish leg. Even a 1.5% or 2% pullback produced unstable outcomes.

**B. Hold overnight until regular-hours broker-managed trailing exit**: no software trend exits before the open; simulate a **1.0% trailing stop-market starting 9:30 AM ET**. Friday modeled **+$313.52** total with 7 round trips including the afternoon reentries: AMD +$119.64; MU +$37.80; SNDK +$93.50; SOXX +$62.58. The four Thursday entries exited in the opening minute at estimated prices: AMD $439.33 (+$95.08), MU $701.14 (+$38.04), SNDK $886.83 (+$93.50), SOXX $137.95 (+$58.52). Later Friday reentries: AMD 4 shares $438.69 at 1:09 PM ET -> $444.83 at 2:55 PM ET (+$24.56); MU 2 at $689.02 1:33 PM -> $688.90 (+/−$0.24); SOXX 14 at $135.70 1:32 PM -> $135.99 (+$4.06). No SNDK afternoon buy triggered. Forced exits at 2:55 PM ET reflect the owner's 2 PM Central maximum.

**C. Sell before market opens**: submit *simulated* eligible extended-hours sell limits based on the 9:24 AM ET close, with a 0.15% execution allowance and require next bar to touch the limit. Friday modeled **+$374.06** including the same afternoon reentries. Four estimated 9:25 AM ET exit prices: AMD $441.07, MU $707.15, SNDK $895.78, SOXX $139.64. With a 0.30% allowance, this fell to **+$338.66**. The pre-open exit has additional fill risk because a minute OHLC high crossing the limit does not prove bid/ask, queue priority, fill size or auction availability.

**Stress:** 1% opening trailing stop with 0.15% assumed execution allowance = +$313.52 Friday. At 0.30%, +$278.18; at 0.50%, +$231.20. A 1.5% trailing stop with 0.15% allowance = +$284.26. These are not broker-verified fills. A trailing **stop-limit** may fail to fill when price gaps down; these simulations instead model a **stop-market-like** exit. Same-bar high/low ordering is unknown.

## Results on earlier sessions (avoid cherry-picking)

For a **broad** 3%-leaders/2%-SOXX/0.5%-momentum evening entry rule, allowing later premarket and afternoon entries, and simply holding until 1% trailing at open:

- 20-session sample: 31 completed modeled round trips; **+$93.75 cumulative**.
- Almost all positive P/L came from Friday November 6 **+$313.52**; earlier sessions collectively **−$219.77**.
- Friday was inspected before these thresholds were selected. This is not independent out-of-sample validation.

A more stringent **crash-then-rebound** qualifier, selected *after looking at Friday*: previous session at least two of AMD/MU/SNDK down **8% or more**, with SOXX down **5% or more** (split-adjusted); also require the subsequent evening regime from above; afternoon reentry only for a symbol with an earlier session entry. Within the 20-session lookback:

- Prior-session crash filter held on October 23, November 2, and November 6.
- Only **November 6** satisfied the full subsequent rebound and produced modeled entries; all other 19 sessions produced *no trades*. Reported **+$313.52 total**, but the rule has only **one positive qualifying day**—**not a demonstrated edge**.
- One simulated 2% software weakness exit variant produced +$147.96 on Nov 6; same model with no overnight software weakness exit produced +$313.52. This suggests a narrow overnight stop may be counterproductive for this *particular* rally; it does not establish overnight exits are universally bad.

## Critical caveats and next decision

1. Parameters were selected and revised with knowledge of November 6; strong hindsight/selection bias. One qualifying historical event cannot validate the strategy.
2. Quotes are not trades, and OHLC can fill a hypothetical limit even when no executable bid/ask or queue priority was available. No commissions, provider microstructure or outages included.
3. Software exits overnight are not guaranteed; 1% trailing stop/stop-limit assumed at opening can gap or fail, and a protective order requires a verified accepted order tied to actually held quantity.
4. A large prior-day crash followed by a coordinated rebound is a plausible **separate strategy candidate**, not a replacement for generic rising-sector scanning. Do not confuse a no-trade rule's zero P/L with proof of profitability.
5. Do not enable this candidate across all stocks, let alone LIVE accounts. Maintain independent PAPER observation and execute only after checking extended-hours eligibility, broker account orders, fills, valid stop orders, position reconciliation, and timely daily close.

**Recommendation:** Freeze these parameters and collect independent future crash/rebound signals with real bid/ask and PAPER fills, recording expected-versus-actual entries/exits. Compare holding to the open against verified premarket exit limits. Review after multiple independent eligible sessions rather than inventing further Friday-specific filters.
