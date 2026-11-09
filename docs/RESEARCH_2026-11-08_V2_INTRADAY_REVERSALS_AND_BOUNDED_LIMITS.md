# V2 two-sided intraday reversals and bounded-limit order stress — November 8, 2026

**Research only; no broker orders, configuration changes, or V1 modifications.**

This is a follow-up to `RESEARCH_2026-11-08_V2_TWO_SIDED_DAILY_OUTCOMES.md`.
The sample is the same **2,244 stock-days** across nine semiconductor names
(AMD, AVGO, INTC, MU, NVDA, SNDK, SOXX, TSM, WDC), November 10, 2025 through
November 6, 2026. There were **254 >=+5%** and **209 <=-5%** previous-regular-close
to regular-close stock-days. Sector totals are unchanged from prior daily
audit (**118 positive, 83 negative, 49 mixed** across 250 sessions).

The prior daily review covered preceding evening, premarket and the first
regular hour. This new experiment **only evaluates 09:45–13:00 ET**
regular-session decision times, and separately 13:00–15:50 ET warnings.
Do not compare its counts directly with the previous combined premarket/first-hour
counts as though the evaluation windows were identical.

## Why test intraday high/low reversals?

The fixed, original rule measures a **2.5% decline from previous regular close,
INCLUDING at least a 1% decline during the latest 15 completed minutes**. It
can miss an abrupt reversal of a stock that opened substantially higher.

The additional **intraday peak drawdown** candidate requires a fall >=2.5%
from the maximum high observed so far *in completed regular-session bars*,
including >=1% in the last 15 completed minutes. It does **not** require
the stock to be negative from the previous close. Its upside mirror requires
a rise >=2.5% from the lowest completed-bar low so far, including >=1% in
15 completed minutes. Both conditions are overlapping, not additive.

All decisions use timestamps no earlier than the end of a five-minute bar;
the next bar is *outcome only*, never an input. No sector close label is used
for a decision. Daily +5%/-5% labels are retrospective evaluation only.
This is not a one-minute or real-time streaming reconstruction.

## Full 09:45–13:00 ET signal coverage

| Causal decision family | Signals | Major day hits | Major missed | Signals on other days | Modeled mean advantage through 14:00 with 30-bp bounded limit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original down from previous close | 531 | 187/209 | 22 | 344 | **-0.058 pp** |
| Down from intraday high | 862 | 176/209 | 33 | 686 | **-0.050 pp** |
| Original up from previous close | 514 | 225/254 | 29 | 289 | **+0.017 pp** |
| Up from intraday low | 895 | 212/254 | 42 | 683 | **-0.158 pp** |

Among the **22** >=5% down closes with no original RTH rule warning
before 13:00, the intraday-high rule caught **four** and created
**414 additional warnings on non-5%-down days**.
For upside it added **three** of **29** missed major gainers while
creating **456** extra alerts on non-5%-up days.

**Interpretation:** Such a signal is valuable as a research feature or
additional *context*, but these false-alarm counts are too high for an
unconditional PAPER automatic exit or entry.

## Detecting the turn earlier

When both rules eventually triggered, the intraday reversal occurred first:

- **Downside:** 144 paired stock-days, including 20 eventual >=5% down
  days and 124 others; among the 20 severe declines, reversal timing
  preceded the original warning by 36.25 minutes on average. Earlier
  next-five-minute-open prices were **2.454 percentage points higher**
  on average relative to prior close than later original-trigger prices.
  This is a *hindsight-selected* subset, not an expected tradable return.
- **Upside:** 76 paired stock-days, including 18 eventual >=5% gainers
  and 58 others; the earlier proxy entry was **1.408 percentage points
  lower** on average in the 18 major gainers. This ignores any missed
  price moves or losses on the other alerts.

**Concrete example, WDC November 20, 2025:** The stock closed -8.912%
from previous close. A completed five-minute-bar peak reversal warning
appeared **09:50 ET** when WDC was still **+1.494% from prior close**
but **-4.598% off its observed intraday peak**, with **-2.438%**
in its last 15 minutes. The original total-decline rule fired **11:35 ET**
at -3.647%, 105 minutes later. Next-bar-open proxies differed by
**5.242 percentage points of prior-close value**. This is an illustrative
past event, not predictive evidence or an executable fill.

**Upside example, SNDK August 3, 2026:** Earlier intraday-trough warning
09:50 ET versus original previous-close warning 10:30 ET; modeled next
open was 4.407 percentage points better (prior-close units) on that
one eventual +6.178% close day.

## Distinct afternoon risk / opportunity review

Continuing the *same fixed signals* until the completed 15:45 bar
(actionable as early as 15:50) found:

- **Four** additional major decliners among **18** still missed by both
  families at 13:00, alongside **46** additional warnings on nonmajor days.
- **One** additional major gainer among **26** still missed at 13:00,
  alongside **67** additional warnings on nonmajor days.

The late alerts frequently arrive **after much of the move**, and cannot
be used to claim a 14:00 exit. Some may matter for overnight risk, but that
requires following-day actual outcomes and an appropriate late-session order
execution model; neither is quantified by this afternoon count.

## Streaming synthetic stop with bounded sell limit: what 5-minute bars permit

We compared a single next-bar-open **price-only eligibility** scenario:
- Signal at the completed five-minute close.
- Software would submit a sell limit priced at the signal close minus
  a fixed 15/30/50/100 bps bound. For buys, ceiling is signal close plus
  the same bound.
- An assumed **15-bps adverse next-open execution adjustment** and
  **15-bps sell exit adjustment** is applied; a modeled limit is considered
  *price eligible* only when the adjusted next-open price is inside the
  limit. If not, model a **nonfill** and continued hold (for sell) or no
  entry (for buy). Do **not** use future intrabar highs to assert a fill.
- Even when the bar-open price is eligible, **actual fill probability
  remains UNKNOWN**: OHLC is not contemporaneous bid/ask, market depth,
  order placement latency or a broker execution receipt.

For the intraday reversal signals, next-bar price-eligibility rates:

| Maximum bound | Downside exit (861 evaluable) | Upside entry (894 evaluable) |
| --- | ---: | ---: |
| 15 bps | 55.5% | 56.2% |
| 30 bps | 98.6% | 99.4% |
| 50 bps | 99.9% | 100.0% |
| 100 bps | 100.0% | 100.0% |

The >=98% *price-eligibility* under a wide limit is emphatically **not a
>=98% order fill rate**. The true execution probability could be much lower,
especially in extended hours or a sharp price collapse.

Across all reversal signals, the modeled 30-bps-bounded **sell-before-14:00
advantage** was **-0.050 pp** on average. On buy signals, hypothetical
buy-to-14:00 average return was **-0.158%**. Earlier period results were
-0.100 pp (exit) and -0.113% (entry); September–November holdout was
+0.281 pp (exit) and -0.473% (entry). The upside degradation persisted in
the later period. No profitable general-purpose trading policy is established.

### Practical limitations and next test

1. **Stop-limit cannot guarantee exit.** If quotes move below the sell
   limit, the order can remain open as losses deepen. A software-managed
   stop adds disconnected feed, rejected order, partial fill, duplicate order
   and stale quote risks. Never replace a protective broker stop in LIVE
   based on this bar-replay study.
2. Need matched **timestamped NBBO bid/ask and sizes**, tick/trade streaming
   and **real PAPER order status/ack/fill latency** for Alpaca and other
   brokers. BOATS (20:00–04:00 ET) samples, news/futures with publication
   times, and actual V1 fills were **not available** in this study.
3. Future V2 PAPER sandbox should run shadow stop decisions with hard
   notional/position safeguards, after reconciliation, without touching V1
   or sending an order until separately approved. Evaluate order eligibility,
   time-to-fill, missed exits, repricing caps and broker-native stop baselines.
4. Expand beyond semiconductor names only after obtaining the corresponding
   full-year timestamped data. Do not transfer this sector's results to all
   other rising sectors or claim a full SIP/BOATS 52-week fill test.

**Disposition: remain research-only.** No V1 live/PAPER monitor, order,
timer or broker configuration changed.

### Reproduce

```sh
cd /tmp/v2-trading-strategy-research
PYTHONPATH=. python3 -m research.v2_reversal_and_limit_stress \
  --output /tmp/v2_reversal_limit_stress_20261108.json
PYTHONPATH=. python3 -m unittest discover -s research -p 'test_*.py'
```

Inputs: `/tmp/semis_52wk_5min_sip_adjusted.json`,
`/tmp/semis_peers_52wk_5min_adjusted.json`,
`/tmp/semis_52weeks_alpaca_daily.json` (all local, not committed).
