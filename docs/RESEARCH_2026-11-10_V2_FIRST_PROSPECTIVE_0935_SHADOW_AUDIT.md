# November 10, 2026 — First untouched 09:35 ET forward-sector shadow: read-only provenance review

**Research only, as of 08:35:47 CST / 09:35:47 ET.** No broker order, active monitor/timer change, production DB change, notification, V1 PAPER/LIVE change or new trading permission.

## First genuinely prospective observation

Independent read-only inspection on authorized www3 confirms `securityprepper-v2-forward-shadow.service` finished successfully (`ExecMainStatus=0`) and journaled `RESEARCH_SHADOW_SEALED` for the 09:35 ET slot on 2026-11-10. It reported two Alpaca DATA-only market requests, **zero broker orders**, seven configured sectors and **five sectors with complete as-of features**.

A separate read of the sealed `/var/lib/securityprepper-v2-forward-shadow/2026-11-10/0935.json` found:

- Source observation: **2026-11-10T09:35:25.240489-05:00**; 09:35 ET slot; original file 3,984 bytes. The research-only, PAPER-disabled and LIVE-disabled flags are present.
- **ASOF_FEATURES**: semiconductors (SOXX, AMD, MU, NVDA), energy (XLE, XOM, CVX), financials (XLF, JPM, BAC), industrials (XLI, CAT, GE), healthcare (XLV, UNH, LLY).
- **ABSTAIN_MISSING_ASOF_DATA**: gold miners (GDX, NEM, AEM, KGC) and software (IGV, MSFT, CRM). All-or-nothing sector outputs do **not** identify which individual required symbol/bar caused an abstention. Do not guess or backfill.
- No provisional bearish-semiconductor shadow classification was generated; no new predictive trading signal was issued. All recorded constituent bar-end timestamps were independently tested <= source observation time (**CAUSAL_SEAL_CHECK_PASS**).
- The service's timer remained active, with subsequent slots configured for 09:45 and 10:05 ET. No 15-minute, 60-minute or 13:40 CT outcome existed when the 09:35 snapshot was sealed. No outcome or P&L is scored here.

Filesystem creation/mtime and logs are corroborating provenance, **not cryptographic immutability, executable quote proof or broker-order attestations**. The first snapshot is **one independent calendar session**, not five independent sector days or seven correct directional predictions. Five sectors merely have as-of inputs; the other two correctly abstained. A later completed outcome may be evaluated in a separate object only after its horizon and without modifying the original.

## Operational entry review through 08:30 CT (bounded journal)

Independently parsed `trading-sector-paper-executor.service` JSON scans 07:30–08:30 CST: **72 completed scans**, 28 repeated BUY_WATCH symbol appearances (ALAB 1, AMD 4, ASML 5, AVGO 4, INTC 2, MU 6, SNDK 3, TSM 2, WDC 1), with **14** `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY` and **14** `NO_FRESH_BID_ASK` skips. These are appearances, not distinct valid executable entries. The cross-session tracked-entry defect is already known and still operationally unresolved. This bounded log census cannot establish complete actual broker activity or missed profit.

## Causal November 9 AMD timing reminder

An isolated offline 1-minute timing check at **2026-11-09 03:18:40 CST** with illustrative 15-second publication allowance shows a trade bar **starting 03:17** was complete/eligible, whereas a bar **starting 03:18** would not finish until 03:19 and was **ineligible at 03:18:40**. Therefore the reported historical 03:18 AMD/MU/SNDK breadth requires its original per-symbol bar **start versus completion** timestamps before treating it as an as-of qualified trade at the 03:18:40 historical ask. This does **not** disprove a signal based on 03:17-start/03:18-end bars. Original MBB `buy_watch_symbols`/`skipped_buy_reasons` are absent at that historic scan; the **exact AMD omission cause remains unknown**.

## Next and safety

After the 09:45 and 10:05 ET slots, independently audit new sealed records without modifying existing snapshots. At a later genuinely completed 15m/60m/13:40 CT outcome, score only post-signal movement, including abstentions, tiny moves and after-*actual*-spread execution uncertainty, never prior-close-to-close sign. Retrieve source-level per-symbol missing data for future diagnostics in a separate research path; do not invent missing symbols for today's frozen observation.

Existing V1 PAPER/LIVE and order/exit safeguards, 13:15 CT entry cutoff, 13:40 flat/14:00 readback, holiday revision-2 cache (valid strictly before Nov 13 16:13 CST absent calendar edit), all active timers and IBKR Gateway remain unchanged. No new PAPER strategy GO.
