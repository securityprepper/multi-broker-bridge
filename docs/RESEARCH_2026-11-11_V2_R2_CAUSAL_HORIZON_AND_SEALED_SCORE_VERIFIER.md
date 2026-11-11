# November 11, 2026, 15:4x America/Chicago — prospective V2 horizon semantics correction and independent immutable-score verification

## Why this is a required pre-forward test correction

An independent comparison of **the installed** `/opt/securityprepper/v2-forward-shadow/research/v2_sector_forecast_policy_20261111.py` and `v2_forward_shadow_score_20261111.py` found an inconsistency before the first effective forecast day. The **r1 policy metadata** described the 60-minute outcome as "fixed 60 minutes after scheduled slot", but the **installed scorer code** actually implements the **first completed five-minute bar ending no earlier than the actual timestamp of forecast issuance plus 60 minutes**. This is a more causally sound post-signal horizon, but it is not the same clock time. For example, a 09:35:32 Eastern issuance must be measured no earlier than the completed 10:40 Eastern bar; calling a 10:35 bar "60m after issuance" would credit an outcome before the specified future interval completed.

This distinction is **not** evidence of a trading profit or loss, and no November 10–11 market snapshots were rewritten. However, silently mixing slot-based and actual-issuance-based horizons would make forecast-validation denominators and benchmark comparisons unreliable.

**Research-only correction made before the first prospective day (November 12):** freeze the identical seven-sector UP/DOWN/ABSTAIN decision logic as `v2-7sector-forward-baselines-20261111-r2`, with outcome description `first completed SIP 5-minute bar ending no earlier than actual forecast issuance plus 60 minutes`; SHA256 of the complete canonical policy JSON is `629a5f7dab20d8ba4d5ed1e51b3947f658d4bb4971ffdf5e95ece2078fdf3ff3`. The score implementation already computes this issuance-based future horizon, so no code path in the active scorer or capture service needed an execution change. The r2 policy file was atomically installed on the **read-only V2 research host** using a lock, an expected-old-file SHA guard, and a no-previous-November-12-forecast check; the original r1 file was backed up. No V1 PAPER/LIVE execution sources, orders, trading services, schedules, flat/cutoff gates or IBKR sessions were changed.

The existing policy's threshold values, seven sectors, three early-regular-session observation slots, research-only permissions, source 5-minute bar rules, and actual earliest-signal timestamp rules are unchanged. The r2 policy is effective for the first eligible November 12 session only; no old feature-only November 10–11 files may be relabeled. At the host check both `securityprepper-v2-forward-shadow.timer` and `securityprepper-v2-forward-score.timer` remained **active**. Holiday cache: revision 2, unpaused, next check 2026-11-13 16:13 CST, valid strictly before boundary absent a calendar edit.

## Independent verifier added (does not alter the installed timers)

New standalone `research/v2_forward_shadow_integrity_verify_20261111.py` independently checks all three original sealed forecast files from the same prospective date against the **issuance-time** `RESEARCH_SHADOW_SEALED` service journal, the precise digest in that journal, and the separate **post-outcome** score file. It pins the r2 policy hash rather than trusting any internally consistent replacement hash. It fails closed on missing, duplicate, late, after-horizon or altered journal seal records; altered source-file bytes; invalid/absent all-seven-sector decisions; unauthorized orders/alerts; or missing/stale outcome documents.

For every forecast arm, sector, slot and horizon, it verifies the post-outcome score still references exactly the original sealed SHA256, original direction, issued-as-of price and actual issuance timestamp. It independently recalculates the signed **post-signal-only** return, direction HIT/MISS/TINY/ABSTAIN, illustrative 30/60bp subtractions, and target time (issuance+60m rounded **up** to the next completed five-minute bar, or 14:40 Eastern/13:40 Chicago flat). It rejects duplicate or missing rows; there are **84 expected outcome rows per complete session**: 3 slots × 7 sectors × 2 forecast arms × 2 outcome horizons. The verifier never fetches market prices or news, has no broker API interface, does not change source/outcome files, cannot create orders, and does not send alerts. It reports aggregate counts only; no account, cash, personal data, credentials or raw quotes.

Validation on www3:
- **39** existing capture/scorer offline tests passed with the **new installed r2 policy**.
- **20** independent verifier offline tests passed, including tampered forecasts, forged/missing/late issuance receipts, pre-signal/tiny returns, score time inconsistency, old schema, duplicate rows and order-permission fail-closed.
- An additional cross-module **synthetic end-to-end integration** created three source files with the installed collector and a separate 84-row score with the installed scorer, then independently verified the journal-to-forecast-to-outcome chain: `PASS_SOURCE_AND_SCORE_AGREE`, 3 slots, 7 sectors, 84 rows, 0 broker orders. **Synthetic**, not real market performance.
- The read-only score timer's actual November 11 13:50 Chicago result was `POLICY_NOT_YET_EFFECTIVE_NO_SCORE`, with **0** market requests and orders. No November 12 outcomes exist as of this report.

## Evaluation contract and limitations

The first real eligible journal SHA and forecast must be written **before** tomorrow's future outcomes; the independent verifier should be run with the trusted local journal export **after** the separately sealed 13:50 Chicago score. On a holiday pause, missing market data, missing score, or incomplete sector coverage, the verifier must report **UNVERIFIED**, never success. Count at least 20–30 **distinct** newly prospective completed market days; multiple slots on one date are correlated and not independent days. Direction accuracy from a post-signal mark is not after-fee trading profitability, and 30/60bp deductions from SIP trade marks are only hypothetical, not executable bid/ask/fill evidence.

Source/tests are committed on the isolated `research/rebound-v2-conditional-exits` branch:
- `research/v2_sector_forecast_policy_20261111.py` (r2 metadata correction)
- `research/v2_forward_shadow_integrity_verify_20261111.py` (new independent audit)
- `tests/test_v2_forward_shadow_integrity_verify_20261111.py` (20 focused offline tests)

**NO new trading strategy GO:** no live after-cost forward profit evidence; all active V1 PAPER/LIVE protections and brokers remain unchanged. Unrelated repeated historical price-chase and reentry candidate families remain retired. The research recommendation-PAPER router timer remains disabled; this verifier does not attempt to commission it.
