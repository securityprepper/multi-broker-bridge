# November 10, 2026 — PAPER recommendation bridge reconciliation commissioning blockers

**Research-only code and isolated synthetic tests. No new PAPER/LIVE broker orders, enabled timers, active V1 changes, production Percona writes or commissioned service changes.** The installed recommendation bridge on www3 remains disabled, inactive and missing its commissioning file; this source-only patch is not an installation.

## Independently reproduced correctness failure

The separate, off-by-default recommendation_paper_bridge.reconcile.check_parent compares str(broker_parent.limit_price) to str(MySQL_intent.limit_price). Its Percona column is DECIMAL(18,6); a stored 100.10 is returned as 100.100000, whereas a valid Alpaca broker response can encode the **same numeric price** as "100.1" or "100.10". The original code falsely raises Unsafe("PAPER parent identity or bracket parameters mismatch") on such formatting differences. exit_guard.receipt() calls this same check, so this formatting failure can block both FILL reconciliation and the required 13:40 Chicago forced-flat planning **if future PAPER trading were commissioned**. This is a demonstrated **pre-release implementation defect**, NOT evidence of an active V1 position or missed real close.

Research-branch fix: compare exact finite Decimal values using the existing nonnegative qty() validator, preserving strict rejection of real limit discrepancies and malformed/nonfinite prices. No floats or rounding tolerances were added. Synthetic tests cover 100.100000 vs 100.1/100.10/100.100000 and reject 100.100001/100.11/NaN/infinity/empty/null.

## Independently observed bounded-queue coverage problem

The original read-only reconciler query included indefinitely retained CLOSED_NEEDS_FEE_RECON records among the **oldest 50** rows. Once 50 historical closed records accumulate, they could occupy the entire scheduled scan and prevent any newly filled position from being reconciled. The original query also excluded UNFILLED nonterminal parents, so a later fill could remain unobserved by this reconciler. Separately, the exit guard silently selected only the oldest 75 eligible rows; at 76 eligible rows, a later current position might never be processed. No production backlog exists yet (zero bridge intents), so these are **synthetic stress failures / prospective safety risks**, not observed live open positions.

Research-branch mitigation: exclude already closed fee-pending rows from the active fill scanner; include nonterminal UNFILLED parents for broker recheck; prioritize partial/unprotected and open positions; request **one extra** record (51/76) and **fail loudly** rather than silently report partial scan coverage if the finite capacity is exceeded. This is NOT a complete pagination/owner notification solution. A commissioned watchdog must monitor such failures, and adequate multi-session capacity, forced exits and independent broker position readback must still be proven before GO.

## Reproduction and limitations

- Isolated checkout /tmp/v2-run19-paperguard-research based on canonical V2 branch research/rebound-v2-conditional-exits head ec09f5b before this change.
- New synthetic unit suite: tests/test_recommendation_paper_queue_and_decimal_regression.py; edits to **research branch only** recommendation_paper_bridge/reconcile.py and recommendation_paper_bridge/exit_guard.py.
- All recommendation-paper tests: **53 passed** (including five new safety tests). No broker network requests or real DB writes; test-only fake DB and allowlisted fake account.
- Read-only www3 Percona inspection on Nov 10 ~17:33 Chicago: sp_live_recommendation_ledger has **96 historical records**, latest Nov 6; new sp_paper_rec_intents, sp_paper_rec_events, and closed audit watermarks are empty. The four Trading Opportunities tasks have no new canonical recommendation rows today; therefore no claim of broker-linked recent closed recommendations, and the hourly Recommendation Audit remains the only notifier when real closed records exist.
- Existing bridge's router/reconcile/exit timers were all **disabled/inactive** and /etc/securityprepper/recommendation-paper-bridge/COMMISSIONED absent. No new broker-trade permission follows from this patch.
- Research trusted holiday cache: paused=false, revision 2, America/Chicago, next boundary 2026-11-13 16:13 CST (strictly before boundary, if no calendar edit). All original 13:15 entry stop, 13:40 flat, 14:00 verification and V1/LIVE barriers preserved.

**Remaining blockers** beyond these source fixes: independently provisioned restricted SQL accounts; shared broker-account/symbol lock with active MBB/FDR or isolated PAPER account; true Alpaca PAPER parent/child/partial-fill/late-stop/exclusive-lot and after-14:00 flat rehearsals; bracket-native stop gap/slippage uncertainty; broker UUID and commission readback; independent release and owner GO. Research does not enable or install anything.
