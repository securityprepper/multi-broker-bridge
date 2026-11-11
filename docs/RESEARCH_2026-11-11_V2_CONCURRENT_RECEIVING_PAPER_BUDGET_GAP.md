# November 11 2026 04:30 CST — receiving-Alpaca PAPER cross-strategy concurrent exposure admission defect

## Confirmed host source evidence (read-only)
The **separate, currently disabled** `securityprepper-recommendation-paper-router.service` has
`ExecStart=/usr/bin/python3 -B -m recommendation_paper_bridge.bridge run-once`, WITHOUT a shared
`/var/lib/multi-broker-paper/broker-execution.lock` flock wrapper. The existing enabled MBB
`trading-sector-paper-executor.service` and FDR `trading-five-day-rebound-paper.service`
BOTH use this same execution flock. No router order or timer activation was performed.

The disabled router source `/opt/securityprepper/recommendation-paper-bridge/recommendation_paper_bridge/bridge.py`:
- Takes receiving-PAPER account, position and open-order GET snapshots in `preflight()`;
- Runs daily-loss/exposure checks **only when** `row["source_task"]==EARN_TASK` (previously identified blocker);
- Reserves only through `sp_paper_rec_symbol_claims` with primary key `(session_date,paper_account_fingerprint,symbol)`. This blocks duplicate orders **for the same symbol**, NOT simultaneous distinct symbols exceeding the account-wide cap;
- Ends the initial selection transaction before preflight; then makes its reservation in an independent per-row transaction. There is no account-scoped transaction lock spanning budget check through all-source reservation.
- Uses the same starting `now` for the quote-age and cutoff tests rather than a receipt-time/final pre-POST clock (previously identified blockers).

Thus, **if this currently-disabled router were enabled without review**, it would not participate
in the MBB/FDR host execution serialization and its independent recommendations could consume
unaccounted concurrent buying power/exposure across different symbols. This is a **release defect**,
not evidence of actual overlapping orders or losses.

## Concrete two-symbol synthetic counterexample
Suppose independently verified own-Alpaca holdings are $10,000 and there are no open broker orders.
Two different-source recommendations for **different** stocks each propose a $1,500 order. If both
run against the same pre-reservation broker snapshot, each sees $11,500 projected exposure (under
the $11,800 ceiling) and independently passes. Together, their potential commitment becomes
**$13,000**, exceeding the ceiling by **$1,200**. A per-symbol unique key does not prevent this.

## Research-only implementation
Added `research/v2_paper_account_reservation_budget_20261111.py` and
`tests/test_v2_paper_account_reservation_budget_20261111.py` ONLY to canonical isolated V2
`research/rebound-v2-conditional-exits`. The model requires:
1. Exact receiving-Alpaca PAPER account identity, monitor fingerprint and verified complete
   receiving-broker positions/open orders as-of the decision (20-second freshness bound in research);
   no Robinhood/IBKR prerequisites.
2. A durable **per-PAPER-account + trading-session** exclusive admission lock asserted by the
   caller; a mere in-memory or per-symbol reservation cannot certify this.
3. Outstanding commitments from ALL recommendation sources, plus MBB/FDR open orders/positions,
   with partial-filled remaining quantity notional accounted. Unknown POSTs consume full reserved
   risk until receiving-broker reconciliation; no time-based automatic release.
4. Verified no-POST or broker-terminal+inventory-reconciled release only, fail-closed unknown
   states, same-intent deduplication and no double-counting an exact already-reflected broker order.
5. Exact daily loss **at or below -$400** rejects admission even if an untrusted lockout flag
   incorrectly says false. This is a conservative boundary change in research, NOT an active
   loss control change.
6. Every decision returns `order_authorized=False` and invokes ZERO broker operations.

**Verification:** 21 new admission tests + 12 prior all-source loss/exposure tests + 5 news
first-seen tests = **38 offline tests PASS** on isolated www3 canonical V2 checkout,
GitHub SHA `f6bd43cac994dd59fce5b949182d231f9cdc6345`.
The tests demonstrate the two-distinct-symbol over-cap admission when a reservation is omitted
and rejection when the preceding commitment is included. These are fake inputs, NOT replayed orders.

## Required release design, NOT installed
- Make the separate router share MBB/FDR receiving-account execution serialization from
  acquisition through fresh account/readback, all-source daily-loss/exposure and final cutoff
  check, reservation, broker POST and authoritative broker readback. Systemd wrapper and
  file permissions require independent deployment/security review.
- Add account/session-scoped Percona transactional budget row (or equivalent durable lock)
  with total outstanding shadow reservations, plus open broker exposure and uncertainty handling.
  **All writers** for that receiving Alpaca PAPER account must honor coordinated gate; adding an
  account lock to only this router does not serialize independent MBB/FDR brokers or other writers.
- Refetch/validate own-broker positions and all open orders, exact account, freshness, cash,
  protected bracket, holiday and 13:15 CT cutoff **immediately before broker POST**, no
  time-of-check/time-of-use replay. Enforce daily-loss/combined exposure for all sources.
- Respect 13:40 CT flatten and 14:00 final verification, bounded retry/readback, broker idempotency,
  and no ever-automatic unknown-state POST retry.
- At commissioning, require staged PAPER-only independent security review, broker readback and
  integration tests including two concurrent distinct-source symbols, partial fills, unknown POST,
  terminal release, loss-limit boundary and unrelated broker outage.
- No authorization of new PAPER strategies, no LIVE authority and no broker order requests.

The existing V1 PAPER/LIVE services, broker orders, systemd timers, host source files,
trusted rev2 holiday cache (unpaused through strictly before 2026-11-13 16:13 CST absent
calendar invalidation), and owner's cutoff/flat safeguards were **not changed**.
No verified profitable after-cost V2 strategy emerged. Existing historical gap/price-chase
research stays retired.
