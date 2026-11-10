"""Offline-only reservation/race safety tests: synthetic evidence and no brokers."""
from dataclasses import replace
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v2_mbb_intent_reservation_research import (
    OfflineIntentRegistry, Readback
)

CHI = ZoneInfo("America/Chicago")
NOW = datetime(2026, 11, 10, 6, 20, tzinfo=CHI)


def snap(now=NOW, **updates):
    base = Readback(
        asof=now - timedelta(seconds=2),
        account_scope="PAPER_SCOPE_A",
        session_key="2026-11-10",
        symbol="AMD",
        calendar_authorized_session_key="2026-11-10",
        calendar_revision_valid=True,
        session_eligible=True,
        broker_history_complete=True,
        fill_uuid_chain_reconciled=True,
        writer_registry_attested=True,
        positions_complete=True,
        open_orders_complete=True,
        broker_flat=True,
        no_open_orders=True,
        no_unknown_submissions=True,
    )
    return replace(base, **updates)


def reserve(registry, r=None, now=NOW, writer="MBB", client_id="MBB-attempt-1",
            slot=0, **kw):
    return registry.reserve(r or snap(now), now=now, writer=writer,
                            client_order_id=client_id, slot=slot, **kw).status


def test_first_entry_allowed_even_with_prior_session_history():
    reg = OfflineIntentRegistry()
    before = NOW - timedelta(days=1)
    old = snap(before, session_key="2026-11-09",
               calendar_authorized_session_key="2026-11-09")
    assert reserve(reg, old, now=before, client_id="MBB-old") == "RESEARCH_RESERVATION_ONLY"
    assert reserve(reg, snap(), client_id="MBB-new") == "RESEARCH_RESERVATION_ONLY"
    assert len(reg.snapshot()) == 2


def test_same_session_across_writers_blocked():
    reg = OfflineIntentRegistry()
    assert reserve(reg) == "RESEARCH_RESERVATION_ONLY"
    assert reserve(reg, writer="NEWS", client_id="NEWS-next") == "BLOCK_SAME_SLOT_ALREADY_RESERVED"


def test_duplicate_client_order_id_rejected_across_symbols_and_accounts():
    reg = OfflineIntentRegistry()
    assert reserve(reg) == "RESEARCH_RESERVATION_ONLY"
    assert reserve(reg, snap(symbol="MU", account_scope="PAPER_SCOPE_B")) == "BLOCK_DUPLICATE_CLIENT_ID"


def test_unknown_submission_never_auto_expires_or_rearms():
    reg = OfflineIntentRegistry()
    reserve(reg)
    assert reg.transition(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
                          symbol="AMD",slot=0,writer="MBB",new_state="SUBMISSION_UNKNOWN").status == "RESEARCH_TRANSITION_ONLY"
    assert reserve(reg, client_id="MBB-retry") == "BLOCK_SAME_SLOT_ALREADY_RESERVED"
    assert reg.transition(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
                          symbol="AMD",slot=0,writer="MBB",new_state="CANCELED_EMPTY",
                          complete_broker_readback=False,verified_flat=True).status == "BLOCK_NEEDS_BROKER_FLAT_PROOF"
    assert reserve(reg, client_id="MBB-late-retry", now=NOW+timedelta(hours=1),
                   r=snap(NOW+timedelta(hours=1))) == "BLOCK_SAME_SLOT_ALREADY_RESERVED"


def test_incomplete_or_stale_proof_rejected():
    for bad in (
        {"broker_history_complete":False},
        {"fill_uuid_chain_reconciled":False},
        {"writer_registry_attested":False},
        {"positions_complete":False},
        {"open_orders_complete":False},
        {"broker_flat":False},
        {"no_open_orders":False},
        {"no_unknown_submissions":False},
        {"calendar_revision_valid":False},
        {"calendar_authorized_session_key":"2026-11-09"},
        {"asof":NOW-timedelta(seconds=61)},
        {"asof":NOW+timedelta(seconds=1)},
    ):
        assert reserve(OfflineIntentRegistry(), snap(**bad)) == "BLOCK_BROKER_OR_SESSION_PROOF"


def test_wrong_session_returning_during_evening_requires_independent_calendar():
    night = datetime(2026,11,9,20,30,tzinfo=CHI)
    row = snap(night,session_key="2026-11-10",
               calendar_authorized_session_key="2026-11-10")
    assert reserve(OfflineIntentRegistry(),row,now=night) == "RESEARCH_RESERVATION_ONLY"
    assert reserve(OfflineIntentRegistry(),replace(row,calendar_authorized_session_key="2026-11-09"),
                   now=night) == "BLOCK_BROKER_OR_SESSION_PROOF"


def test_weekend_calendar_must_attest_not_infer_saturday():
    sunday = datetime(2026,11,15,20,30,tzinfo=CHI)
    row = snap(sunday,session_key="2026-11-16",calendar_authorized_session_key="2026-11-16")
    assert reserve(OfflineIntentRegistry(),row,now=sunday) == "RESEARCH_RESERVATION_ONLY"
    assert reserve(OfflineIntentRegistry(),replace(row,calendar_revision_valid=False),
                   now=sunday) == "BLOCK_BROKER_OR_SESSION_PROOF"
    friday = datetime(2026,11,13,20,30,tzinfo=CHI)
    assert reserve(OfflineIntentRegistry(),snap(friday,session_key="2026-11-16",calendar_authorized_session_key="2026-11-16",session_eligible=False), now=friday) == "BLOCK_BROKER_OR_SESSION_PROOF"


def test_no_auto_reentry_after_loss_or_without_discount():
    reg = OfflineIntentRegistry()
    reserve(reg)
    args = {"now":NOW,"writer":"MBB","client_id":"MBB-reentry",
            "slot":1,"prior_profit_sale_verified":True,
            "discounted_fresh_ask_verified":True}
    assert reserve(reg,**args) == "BLOCK_PREDECESSOR_NOT_CLOSED"
    assert reg.transition(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
                          symbol="AMD",slot=0,writer="MBB",new_state="ACKNOWLEDGED",
                          broker_order_id="broker-A").status == "RESEARCH_TRANSITION_ONLY"
    assert reg.transition(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
                          symbol="AMD",slot=0,writer="MBB",new_state="FILLED",
                          broker_order_id="broker-A").status == "RESEARCH_TRANSITION_ONLY"
    assert reg.transition(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
                          symbol="AMD",slot=0,writer="MBB",new_state="CLOSED_VERIFIED",
                          complete_broker_readback=True,verified_flat=True).status == "RESEARCH_TRANSITION_ONLY"
    assert reserve(reg,slot=1,client_id="X-2",prior_profit_sale_verified=False,
                   discounted_fresh_ask_verified=True) == "BLOCK_REENTRY_PROOF"
    assert reserve(reg,slot=1,client_id="X-2",prior_profit_sale_verified=True,
                   discounted_fresh_ask_verified=False) == "BLOCK_REENTRY_PROOF"
    assert reserve(reg,**args) == "RESEARCH_RESERVATION_ONLY"
    assert reserve(reg,**{**args,"client_id":"MBB-third"}) == "BLOCK_SAME_SLOT_ALREADY_RESERVED"


def test_reentry_after_ten_ct_rejected():
    reg = OfflineIntentRegistry()
    later = NOW.replace(hour=10, minute=1)
    assert reserve(reg,snap(later),now=later,slot=1,client_id="MBB-r",
                   prior_profit_sale_verified=True,
                   discounted_fresh_ask_verified=True) == "BLOCK_REENTRY_PROOF"


def test_1315_cutoff_rejects_even_first():
    later = NOW.replace(hour=13,minute=15)
    assert reserve(OfflineIntentRegistry(),snap(later),now=later) == "BLOCK_ENTRY_CUTOFF"


def test_holiday_pause_always_blocks():
    assert reserve(OfflineIntentRegistry(),holiday_unpaused=False) == "BLOCK_HOLIDAY"


def test_partial_does_not_rearm_without_broker_proof():
    reg=OfflineIntentRegistry()
    reserve(reg)
    keys=dict(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
              symbol="AMD",slot=0,writer="MBB")
    assert reg.transition(**keys,new_state="ACKNOWLEDGED",broker_order_id="broker-A").status == "RESEARCH_TRANSITION_ONLY"
    assert reg.transition(**keys,new_state="PARTIAL",broker_order_id="broker-A").status == "RESEARCH_TRANSITION_ONLY"
    assert reg.transition(**keys,new_state="CLOSED_VERIFIED",complete_broker_readback=True,
                          verified_flat=False).status == "BLOCK_NEEDS_BROKER_FLAT_PROOF"
    assert reg.transition(**keys,new_state="CLOSED_VERIFIED",complete_broker_readback=False,
                          verified_flat=True).status == "BLOCK_NEEDS_BROKER_FLAT_PROOF"
    assert reg.transition(**keys,new_state="FILLED",complete_broker_readback=False).status == "BLOCK_UNKNOWN_OR_FILLED_NOT_RECONCILED"


def test_replayed_transition_idempotent():
    reg=OfflineIntentRegistry();reserve(reg)
    keys=dict(account_scope="PAPER_SCOPE_A",session_key="2026-11-10",
              symbol="AMD",slot=0,writer="MBB")
    assert reg.transition(**keys,new_state="ACKNOWLEDGED",broker_order_id="broker-A").status == "RESEARCH_TRANSITION_ONLY"
    assert reg.transition(**keys,new_state="ACKNOWLEDGED",broker_order_id="broker-A").status == "IDEMPOTENT_NOOP"
    assert reg.transition(**keys,new_state="FILLED",broker_order_id="broker-B").status == "BLOCK_ORDER_UUID_CONFLICT"


def test_concurrent_first_purchase_only_one_reservation():
    reg=OfflineIntentRegistry()
    def attempt(i):
        return reserve(reg,writer="MBB" if i%2 else "NEWS",client_id=f"candidate-{i}")
    with ThreadPoolExecutor(max_workers=16) as pool:
        results=list(pool.map(attempt,range(100)))
    assert results.count("RESEARCH_RESERVATION_ONLY")==1
    assert results.count("BLOCK_SAME_SLOT_ALREADY_RESERVED")==99
    assert len(reg.snapshot())==1


def test_different_accounts_can_reserve_independent_orders():
    reg=OfflineIntentRegistry()
    assert reserve(reg)=="RESEARCH_RESERVATION_ONLY"
    assert reserve(reg,snap(account_scope="PAPER_SCOPE_B"),
                   client_id="MBB-different-account")=="RESEARCH_RESERVATION_ONLY"


def test_invalid_writer_and_slot_are_rejected():
    assert reserve(OfflineIntentRegistry(),writer="LIVE")=="BLOCK_INVALID_WRITER_OR_ID"
    assert reserve(OfflineIntentRegistry(),slot=2)=="BLOCK_INVALID_SLOT"
