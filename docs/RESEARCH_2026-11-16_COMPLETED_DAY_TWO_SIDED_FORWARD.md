# November 16, 2026 — completed-day two-sided research (not an execution signal)

**Status: research-only, no qualifying after-fee edge, no V1/PAPER release.** This is a new completed-session observation, not a repeat of the historical November 9–13 work. Market-data and sector research used only authenticated, read-only Alpaca SIP completed five-minute bars; the www3 root holiday gate was freshly verified unpaused before data retrieval. No broker POST or alerts.

## Coverage and market observations

- Scanned 217 quality/sector symbols; **215** had complete regular-session five-minute bars on **both November 13 and November 16** (09:30–16:00 ET). CYBR and EA lacked a complete matched pair, so coverage is **UNKNOWN**, not flat.
- Seven tracked sector ETFs, **Nov 16 RTH opening price → final completed 5m close**: SOXX −1.307%, GDX −1.791%, XLE −1.255%, XLF −1.021%, XLI −1.204%, XLV −1.463%, IGV −1.452%. **None** met the owner's high-specificity shock threshold on two consecutive completed ETF five-minute closes (SOXX/GDX 5%; XLE/XLF/XLI/XLV 3%; IGV 4%). Price-only alerts stayed research-only.
- One constituent rose ≥3% from its RTH open: **CLS +3.976%**. Twelve constituents fell ≤−3%: **DDOG −5.224%, ROST −3.942%, DVN −3.761%, CARR −3.716%, NFLX −3.557%, GOOGL −3.431%, PLTR −3.258%, FCX −3.140%, CDNS −3.133%, TJX −3.091%, BMY −3.072%, ORCL −3.038%**. These are *descriptive open-to-close changes*, not forward prediction statistics, quotes or short instructions.

## Causal as-of weakness screen — earliest warning per symbol

An internal screen required, **at the same completed five-minute availability timestamp**:

1. Latest completed 5m close at least 2.5% below the actual November 13 *regular-session final* close.
2. The price loss over the **most recent three completed five-minute intervals** at least 1.0 percentage point of that same prior-close baseline. The 15-minute leg is **part of** the total loss and is never added to it.
3. A bar starting at *t* becomes observable no earlier than *t + 5 min*. There was no use of future 5m highs/lows to qualify a signal.

Across 215 matched stocks, **44 distinct symbols** met the screen at least once on November 16. Count each symbol's **first** independently available trigger once; later repeated 5m hits were not additional predictions. Directional returns are measured **AFTER** the earliest signal-time completed close.

| Forward horizon | Lower price (bear direction correct) | Higher price (incorrect) | Mean forward close-to-close price change |
|---|---:|---:|---:|
| Next 15 min | 35/44 (79.5%; simple 95% Wilson 65.5–88.8%) | 9/44 | −0.488% |
| Next 60 min | 14/43 (32.6%; 20.5–47.5%) | 29/43 | **+0.239%** |
| 13:40 CT risk-flat mark | 31/43 (72.1%; 57.3–83.3%) | 12/43 | −0.559% |
| RTH close | 33/44 (75.0%; 60.6–85.4%) | 11/44 | −0.761% |

**Limits:** These Wilson intervals assume independent Bernoulli outcomes, but all signals come from **one correlated broad down day**, so they substantially overstate effective certainty. No untouched 20–30-session forward validation exists. These are close-only price *direction* labels; there are no matched executable bid/ask orders, fees, short borrow or permitted actual positions, and no independently cleared news. Thus **no demonstrated positive after-fee short or BUY edge**; the 60-minute result is particularly cautionary. Do not relax thresholds, auto-short, release V2, notify, or change V1 stops.

Among the twelve ≥3% down-at-close symbols, six met the strict completed-bar weakness trigger (**CDNS, DDOG, FCX, ORCL, PLTR, ROST**) and six did **not** (**BMY, CARR, DVN, GOOGL, NFLX, TJX**). Nontriggers must remain explicit misses/abstentions, not silently counted as correct predictions. For example, DDOG's first qualifying screen became available at **10:00 ET** (09:00 CT), after which the observed RTH close was 2.630% lower than its signal bar close; this is retrospective, **not** a broker-fill claim. The next-open result for Nov 17 is not yet observed and must remain UNKNOWN.

## Provenance and unchanged broker coverage

A bounded **GET-only** Alpaca PAPER inspection of *one identified account* from Nov 16 00:00Z returned **zero distinct Nov 16 FILL activities and zero orders**, with activity pagination complete for that queried account. The result is **not** proof of zero fills at any other Alpaca account and is **not** an all-broker reconciliation. R1M's dedicated Percona signal ledger and service continued running; no confirmed R1M PAPER fills were observed in that service's ledger. An absent recommendation-router event or older Robinhood snapshots were not treated as proof of no trades or current broker authorization. Recommendation Audit, not this research, remains the new-closed-trade notifier.

**Next eligible work:** keep independently timestamped first-seen news, prior five complete sessions, receiving-broker bid/ask and actual fill provenance distinct from retrospective bar labels; withhold parameter changes pending genuinely untouched forward sessions and after-fee executable validation. Continue seeking **different causal mechanisms** rather than reviving repeatedly unprofitable one-minute chase/stop-reentry families.

*Audit mode:* Broker/data GET only, no execution or systemd changes in this research. Experimental data snapshot held separately on www3 at `/tmp/trading-research-20261116-two-sided.json` (temporary root-local copy), not a live strategy input.
