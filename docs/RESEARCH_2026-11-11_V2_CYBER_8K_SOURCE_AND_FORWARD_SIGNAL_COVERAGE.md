# November 11, 2026 — V2 official SEC material cyber-disclosure source audit and sealed forecast coverage

## Boundary and holiday

Pure **read-only research** on authorized www3. Previously validated holiday cache: revision 2, America/Chicago, unpaused, next_check_at **2026-11-13 16:13 CST**, still strictly in the future; no known invalidation in this run. Do not change task recurrence, holiday root controls, host V1, LIVE/PAPER permissions, broker orders or Gateway. These research files make **zero** Alpaca/IBKR/Robinhood broker requests, no alerts and no orders. The standalone recommendation PAPER router remains disabled; no new strategy activation is authorized.

## Distinct hypothesis: official 8-K Item 1.05 material cybersecurity disclosure

Independent negative-news idea, not a retest of previously unprofitable price-only sector continuation, opening-gap earnings, GLD lag, relative-value reversion, volume anomalies or Form 4/13D ownership candidates. The source is **SEC EDGAR Form 8-K Item 1.05**: companies report incidents they determine are material, generally within four business days of the materiality determination, not necessarily the discovery or first public report. A source filing may therefore be already known or repriced by the time a strategy sees it. Accordingly, even an authenticated disclosure is **not** automatic evidence that a new SHORT, inverse ETF purchase, protective exit or BUY veto would improve outcomes.

Official SEC guidance: https://www.sec.gov/answers/form8k.htm . Independent read-only sample used official `data.sec.gov/submissions/CIK...json` parallel arrays, NOT keyword scraping of a later-amended filing body.

Five preselected CIKs were checked with authenticated-free **GET-only** SEC submissions requests and returned HTTP 200: IRTC CIK 1388658, 8x8 CIK 1023731, AT&T CIK 732717, Stryker CIK 310764, and West Pharmaceutical CIK 105770. These are a small illustrative sample, **not a complete issuer/market universe**. Their recent submissions metadata contained **six** Item 1.05 8-K/8-K/A rows: **four original 8-K** events and **two 8-K/A amendments**. The original four have official SEC acceptance timestamps, but **zero** were accompanied by this strategy's immutable original first-observed timestamp and captured content version. The amendments are not automatically new incidents or independent first disclosures. Never equate SEC `acceptanceDateTime` with our first available trading signal or with news originally reaching the market.

Implemented new pure V2 research-only evidence gate that demands exact original 8-K rather than amended 8-K/A, exact Item 1.05 rather than incidental appearance of digits in document text, SEC accession, verified issuer CIK, timezone-aware acceptance <= verified first_seen <= decision, and SHA256 of the originally received text version. It fails closed for stale/future/missing provenance and always denies broker order/notification authorization even when all synthetic fields verify. **20 offline tests passed** (source handling and sealed forward coverage).

**Conclusion:** NO GO, source-readiness only. This sample has **zero** time-causally verified potential trades and no measured after-cost expectancy; it does **not** justify opening shorts, exiting holdings, or pushing predictive warnings. A future study needs independent first-receipt records, prior public/news veto, as-of quote/borrow eligibility, sector-matched no-news controls, real spreads/fees, and >20–30 genuinely future event dates before reconsidering. Because such incidents are uncommon and often disclosed after materiality determination, routine daily trading frequency cannot be inferred.

## Precise blocker in existing prospective seven-sector shadow evidence

Separately audited the **already sealed**, before-outcome GET-only host snapshots for Nov 10 and Nov 11, all 09:35, 09:45, 10:05 **Eastern** slots: six files, expected six, no missing slots and zero broker orders. Of the **42** seven-sector×three-slot×two-day combinations:

- **40** captured completed as-of sector features.
- **2** explicitly abstained due to missing as-of data (Nov 10 early gold miners/software).
- **ZERO** contained a non-null `shadow_classification`, thus **zero issued ex-ante UP/DOWN forecasts** on these two dates.

The installed observer currently freezes only **one exploratory bearish semiconductor condition**, while the remaining six sectors **capture features but have no issued predictive classification policy**. No qualifying semiconductor trigger fired in these two sessions. This is not a crash or loss; it is a **research validation coverage blocker**. Historical analysis must never relabel those 40 feature snapshots as 40 successful forecasts, count them in forecast-accuracy denominators, or backfill newly chosen labels after results become available. It is legitimate to preserve their raw features for future offline work, but **20–30 forecast days are not yet accumulating** across all seven sectors.

For meaningful prospective directional validation, create a separately reviewed, earlier-only frozen UP/DOWN/ABSTAIN policy for each sector; log the policy version and signal timestamp **at issuance** before future outcomes, and only then score actual post-signal movement, abstentions, execution costs and false alarms. This does not authorize connecting the research shadow to an order system or modifying its installed root timer without a separate owner approval.

## Reproducibility and constraints

Pure research files: `research/v2_material_cyber_8k_source_gate_20261111.py`, `tests/test_v2_material_cyber_8k_source_gate_20261111.py`, `research/results/v2_material_cyber_8k_sec_pilot_20261111.json` and `research/results/v2_material_cyber_8k_shadow_coverage_20261111.json`. Existing sealed host snapshots unchanged. Both historical source and prospective capture results are **metadata/data-quality audits**, not brokerage observations, realized trades, or after-fee performance. Preserve V1 and all existing PAPER/LIVE safeguards and the research holiday schedule.