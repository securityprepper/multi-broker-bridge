# November 11, 2026, 14:30 CST V2 research: issuer/SEC first-seen chronology correction and evidence-source feasibility

## Material source-provenance defect discovered and fixed (research-only)

The isolated V2 `research/v2_independent_guidance_revision_evidence_20261111.py` previously conflated the **issuer press-release first-observed timestamp** (`first_observed_at`) with **SEC exhibit availability**, rejecting an issuer release seen before the SEC accepted its accompanying Form 8-K. That sequence can be entirely legitimate: SEC Form 8-K Item 2.02 requires an issuer making a public release to disclose its release date and include the text as an exhibit. See the official [SEC Form 8-K, Item 2.02](https://www.sec.gov/forms/form8-k.pdf). A release may precede the SEC filing/acceptance. The old rule `event_seen < sec_accepted => INCONSISTENT_SEC_PROVENANCE` misclassified this valid sequence.

More importantly, the gate verified only that a linked SEC URL's acceptance time was no later than the research decision. It did **not** require a record of when **this research system first received the original SEC exhibit**, or immutable original-content hashes. Publisher acceptance time is not proof of the strategy's information availability, and mere presence of a URL cannot prove the earlier original text version. This matters critically to causally valid research, although this gate has **never authorized an alert or order**.

The revised pure research gate now separately requires:

- Issuer release publication `release_published_at` <= issuer `first_observed_at` <= decision, plus `release_original_sha256`.
- Authenticated SEC exhibit URL/CIK, `sec_accepted_at` <= **independent** `sec_exhibit_first_observed_at` <= decision, plus `sec_exhibit_sha256` for the originally received exhibit. An issuer release may be observed **before** SEC acceptance; both must be verified by decision time to reach the final research-only evidence state.
- Independently attributed numeric analyst revision for the identical issuer/fiscal-period/units/share basis, `published_at` <= `first_observed_at` <= decision, plus `revision_original_sha256` for its first-seen document.
- Source-ready **SHADOW ONLY** remains `signal_authorized=false` and `order_authorized=false`. Missing, invalid, future, inconsistent or unverifiable provenance fails closed. SHA256-format validation is only a provenance contract; actual capture-time hashing, signed receipts and source authentication **remain to be implemented/verified** before using real events.

Updated the V2 module and expanded the original test suite to **28 passing offline tests**, including release-before-SEC acceptance, SEC first-seen earlier than acceptance, SEC evidence not seen until after decision, missing original hashes for all three documents, wrong CIK, mismatched units/share bases, independently published revision ordering and negative-news veto. No V1, broker services, live/PAPER orders, current research schedules or active host units changed.

## Provider qualification without assuming access

- [FactSet Estimates Point-in-Time](https://www.factset.com/marketplace/catalog/product/factset-estimates-pointintime) explicitly preserves historical daily **local-midnight** consensus snapshots. This is appropriate for a **next-day** consensus-as-of benchmark if separately licensed; it **cannot establish a minute-level first-seen analyst revision after an earnings release on the same day**.
- [Intrinio EPS Estimates](https://intrinio.com/products/eps-estimates) documents enterprise-only access and extra payment for historical data. Historical availability is not the same as verifiable original receipt timestamps; we do not claim entitlement, version history or intraday as-of access.
- [OHLC Analyst Estimates](https://ohlc.io/docs/analyst-estimates) documents `as_of` / `observed_on` behavior but says its own frozen observation history starts September 23, 2026. This could supply more recent daily as-of snapshots if licensed, **not** a three-year archive of original intraday first-seen revisions. Its observation date must not be promoted to a minute-level receipt.
- No connected/host-licensed provider was authenticated as delivering immutable first-seen **numeric analyst old/new revisions with fiscal and share basis**. The existing 3,141 headline-only historical articles are still unusable for this independently sourced confluence. No after-cost predictive edge is established, and no new PAPER execution GO is authorized.

## Independent read-only MBB journal check (bounded November 11)

Parsed `trading-sector-paper-executor.service` JSON records between 00:00 and approximately 14:32 America/Chicago, with **no account credentials/cash/buying-power disclosure**. Observed **959** scans containing `buy_watch_symbols` / `skipped_buy_reasons`; **590** BUY_WATCH symbol appearances, including AMD on **40** scans; **574** skip-reason appearances were `PRIOR_ENTRY_NOT_ELIGIBLE_FOR_DISCOUNTED_REENTRY`, and **zero** were `NO_FRESH_BID_ASK` in this bounded parsed cohort. This is consistent with the current quote-receipt clock correction and restrictive reentry policy, **not** proof of additional successful broker fills or of the exact original November 9 03:18 AMD skip. Repeated symbol appearances are not distinct trades. Active PAPER V1 code already contains `quote_received_at`; **this run did not modify it**.

## Holiday and execution boundaries

The authorized host cache was checked on November 11 at approximately 14:32 CST: calendar revision 2, `paused=false`, verified future `next_check_at=2026-11-13T16:13:00-06:00`, no known calendar edit. The canonical [holiday pause rule](https://github.com/securityprepper/trading-opportunities/blob/main/HOLIDAY-PAUSE-RESCHEDULE.md) explicitly preserves the hourly recurrence while **unpaused**; no DTSTART change is indicated. The V2 forward shadow/score timers remained enabled, but this policy takes effect first on November 12, so no new future-session validated outcome exists. No broker read/write, recommendation order-router commissioning, IBKR Gateway intervention or LIVE authority. The research-only confluence candidate remains **NO GO** pending genuine original source snapshots, independent analyst revisions, matched sector controls, 20–30 untouched days and executable NBBO/fee evidence.

GitHub source/tests: `research/v2_independent_guidance_revision_evidence_20261111.py` and `tests/test_v2_independent_guidance_revision_evidence_20261111.py`, canonical branch `research/rebound-v2-conditional-exits`.
