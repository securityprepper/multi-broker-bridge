"""Separate research-only activist Schedule 13D source/provenance gate.

The issuer submissions list is NOT a complete target-company filing index. The
only acceptable trigger is an independently target-matched ORIGINAL Schedule
13D, with content version and first observation proven as of decision.
No execution, no trading signal, no network or broker access in this module.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

ACC = re.compile(r"^\d{10}-\d{2}-\d{6}$")
CIK = re.compile(r"^\d{1,10}$")

@dataclass(frozen=True)
class ResearchResult:
    decision: str
    reasons: tuple[str, ...]
    allowed_to_trade: bool = False
    validated_prediction: bool = False

def utc(value):
    if not isinstance(value,str): return None
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None

def cik(value):
    return str(int(value)) if isinstance(value,str) and CIK.fullmatch(value) else None

def finite_percent(value):
    try:
        x=Decimal(str(value))
        return x if x.is_finite() and Decimal("5")<x<=Decimal("100") else None
    except (TypeError,ValueError,InvalidOperation): return None

def evaluate(*, form, accession, target_cik, expected_target_cik, accepted_at,
             first_observed_at, decision_at, event_document_sha256,
             source_covers_target, item4_independently_attested,
             active_intent_attested, ownership_pct, negative_news_veto_clear):
    errors=[]
    if form != "SC 13D": errors.append("NOT_ORIGINAL_SC_13D")
    if not isinstance(accession,str) or not ACC.fullmatch(accession):
        errors.append("INVALID_ACCESSION")
    if cik(target_cik) is None or cik(target_cik)!=cik(expected_target_cik):
        errors.append("TARGET_CIK_UNVERIFIED")
    if not source_covers_target:
        errors.append("TARGET_COVERAGE_NOT_CERTIFIED")
    accepted, first, decided = utc(accepted_at), utc(first_observed_at), utc(decision_at)
    if accepted is None: errors.append("SEC_ACCEPTANCE_UNVERIFIED")
    if first is None: errors.append("ORIGINAL_FIRST_OBSERVED_MISSING")
    if decided is None or (accepted is not None and accepted>decided):
        errors.append("DECISION_BEFORE_ACCEPTANCE")
    if (first is not None and (accepted is None or first<accepted or decided is None or first>decided)):
        errors.append("FIRST_OBSERVED_OUTSIDE_DECISION")
    if not isinstance(event_document_sha256,str) or not re.fullmatch(r"[0-9a-f]{64}",event_document_sha256):
        errors.append("DOCUMENT_VERSION_UNVERIFIED")
    if not item4_independently_attested: errors.append("ITEM4_PURPOSE_NOT_ATTESTED")
    if not active_intent_attested: errors.append("CONTROL_INTENT_NOT_ATTESTED")
    if finite_percent(ownership_pct) is None:errors.append("OWNERSHIP_GT5_NOT_VERIFIED")
    if not negative_news_veto_clear: errors.append("NEGATIVE_NEWS_VETO_UNVERIFIED")
    return ResearchResult("SOURCE_VERIFIED_REPLAY_ONLY" if not errors else "NO_GO_SOURCE_INCOMPLETE",
                          tuple(errors),False,False)