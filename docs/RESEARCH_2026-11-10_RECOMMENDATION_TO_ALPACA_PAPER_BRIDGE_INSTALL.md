# Recommendation-to-Alpaca PAPER bridge — implementation and commissioning handoff (2026-11-10 CT)

## Verified implementation
- Canonical research-only branch: `securityprepper/multi-broker-bridge` / `research/rebound-v2-conditional-exits`.
- New isolated root-owned host install: `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/`. Production V1 `/opt/securityprepper/multi-broker-bridge` remains untouched/dirty for independent agents.
- Percona `securityprepper_trading` new tables installed: `sp_paper_rec_intents`, `sp_paper_rec_events`, `sp_paper_rec_symbol_claims`, `sp_paper_rec_flatten_intents`, `sp_paper_rec_audit_watermarks`. No historical recommendation migrated to broker orders. **Zero new bridge intent rows as of commissioning rehearsal.**
- Six new systemd service/timer units installed for isolated router (:50), read-only broker FILL reconciliation (:52), and independently owned exit guard (:54); all **DISABLED/INACTIVE**. The service has `ConditionPathExists=/etc/securityprepper/recommendation-paper-bridge/COMMISSIONED` and `PAPER_BRIDGE_COMMISSIONED=0` plus two independent zero-valued safety attestations. The GO file DOES NOT EXIST.
- **46 offline tests passed** on www3: 15 validation, 13 order/fill attribution, 13 exit and 5 MySQL/broker mocked integration tests. All tests are synthetic; no Alpaca PAPER POST or actual order occurred from this bridge.
- Alpaca supported RTH DAY limit bracket encodes exact owner-recommended parent limit, `take_profit.limit_price`, and `stop_loss.stop_price`. Extended-hours bracket trading is forbidden. Bracket children do not activate until parent fills in full; therefore a separate active partial-fill watchdog is required before commissioning. A bracket stop can gap/slip beyond its trigger.
- Intake inserts a typed immutable recommendation AND historical canonical ledger/notes rows together in one Percona transaction. Unique ID and deterministic client order ID prevent automatic duplicate retry. Broker transport uncertainty remains reserved/unknown, not retransmitted. If entry is stale/after 13:15 Chicago, record NO ORDER and expire.
- Reconciler reads bracket parent/child broker order UUIDs and exact order-specific FILL activities; refuses duplicate/foreign UUIDs, flags partial-unprotected cases, and reports CLOSED_NEEDS_FEE_RECON rather than falsely claiming after-fee net P&L without verified charges.
- Exit guard recognizes the 13:15 Chicago cancellation, 13:40 forced flat and 14:00 verification objective, refuses to SELL another strategy's account shares, and requires an exclusive broker-derived lot. A deterministic exit reservation prevents a second attempt on transport uncertainty. No guard has yet been commissioned or broker-tested end to end.
- Recommendation Audit exporter `python3 -m recommendation_paper_bridge.audit pending` surfaces only not-yet-reported broker-confirmed CLOSED recommendations. After an audit is actually delivered, `python3 -m recommendation_paper_bridge.audit mark-reported --recommendation-id ...` commits an exact durable watermark.

## Exact recommendation ingestion interface (after restricted identities are provisioned)
An eligible Trading Opportunities task, **only after its market/news qualification**, sends one JSON object via STDIN to:
```bash
PAPER_BRIDGE_INTAKE_CNF=/etc/securityprepper/recommendation-paper-bridge/intake.cnf \
PYTHONPATH=/opt/securityprepper/recommendation-paper-bridge \
python3 -B -m recommendation_paper_bridge.bridge intake
```
Fields: `recommendation_id` matching `TO-YYYYMMDD-SYMBOL-T[1-4]-RUNID`, `issued_at_utc`, `quote_at_utc`, `symbol`, `action` = `BUY NOW` or `BUY AT PULLBACK`, `quote_last`, `quote_bid`, `quote_ask`, `limit`, `profit_target`, `stop_loss`, `rationale`, `source_task`, `source_run_id`. **All monetary values must be decimal strings; never float.** Whole-share quantity is bounded by floor($2000/limit), buying power, issuer/account restrictions and broker readback; zero means no order. Historical entries must never be replayed as fresh order intents.

The router is NOT synchronous with ChatGPT. An accepted queue event is NOT a broker order; only a matching Alpaca PAPER order UUID and verified native-bracket readback establish submission.

## BLOCKERS — NOT COMMISSIONED
1. **Restricted SQL identity provisioning was blocked by an authorization/safety check.** The existing `sp_trading_opportunities_writer` has no INSERT on the new queue; a live nonmutating/rollback rehearsal failed with MySQL 1142 before any synthetic record was committed. Never use the root/admin identity for an enabled service, leak the password or broaden old V1 credentials. An authorized host database administrator must create:
   - `sp_paper_rec_intake@localhost`: INSERT/SELECT on typed intents and events and canonical `sp_live_recommendation_ledger`/`sp_notes_recommendations` only.
   - `sp_paper_rec_router@localhost`: SELECT/UPDATE on intents; INSERT/SELECT on events, symbol claims, flatten intents.
   - `sp_paper_rec_audit@localhost`: SELECT on typed intents/events, INSERT/SELECT on audit watermarks.
   Generate independent strong passwords on host, store in `/etc/securityprepper/recommendation-paper-bridge/{intake,router,audit}.cnf` in appropriately restricted modes; NEVER display secrets in logs or chat.
2. **Atomic cross-strategy dedup NOT ATTESTED.** Active MBB PAPER and other potential writers do not read the bridge's new `sp_paper_rec_symbol_claims`. An isolated claim only prevents duplicate bridge recommendations, not a concurrent MBB purchase of the same stock. Either integrate shared lock into *all* PAPER writers under a reviewed change or commission a separately isolated PAPER account; do not modify active V1 behind its owner.
3. **Partial-fill/exit guard has not received an independent PAPER release rehearsal.** Test a whole-fill bracket, a partial-fill unprotected emergency, simultaneous stop/target race, 13:15 cancel, 13:40 forced flat, zero positions/open orders by 14:00, and no inadvertent liquidation of another strategy's shares. Verify owner-approved 2pm latest flat and all holiday/session handling.
4. Pin and verify expected Alpaca PAPER account ID without printing it, provide systemd-only credentials through `LoadCredential`, validate the independent trusted holiday cache, test current SIP NBBO/quote freshness, quote/position/order readback and daily exposure caps; obtain explicit final security review.
5. The existing four task prompt updates demand recommendation records but still require the *actual intake CLI call* on each newly qualified opportunity; a user-visible BUY message by itself does not create a DB record. Audit task must use the new table and durable watermark, and report only new closed reconciled positions.

## Release sequence — requires the missing checks, not automatic
Provision restricted accounts; test `intake --test-rollback` and verify all three ledger row counts remain zero for the synthetic ID; test true duplicate intake collision and a permitted genuine owner-selected PAPER limit on an independent nonproduction session with verified stop/target children, broker UUID/activity readback, partial fill case, and full 13:40 flat; independently review collision/ownership protections. Only after every gate is GO, create the protected commissioning file, supply account allowlist, set all three explicit gates to 1 using reviewed service drop-ins, and enable the three new timers. No LIVE URL or credential ever used.

If any requirement fails, leave all bridge timers disabled and report the precise blocker. Existing V1 PAPER/LIVE services and orders continue unchanged.
