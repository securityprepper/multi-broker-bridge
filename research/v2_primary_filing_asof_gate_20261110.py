"""Research-only independent official-filing time and identity gate.

Never infer historical trading-time access from a later SEC API fetch.  A filing
is actionable as an independent corroboration ONLY if issuer CIK, primary
filing acceptance time, and independently logged FIRST-SEEN timestamp precede
the candidate decision.  For historical retrospective SEC submissions fetched
today, first_seen_at is NOT publication receipt on the historical date.
"""
from datetime import datetime
ALLOWED_FORMS={"8-K","6-K","10-Q","10-K"}

def aware(t):
    if isinstance(t,datetime):
        if t.tzinfo is None or t.utcoffset() is None:raise ValueError("aware timestamp required")
        return t
    if not isinstance(t,str):raise ValueError("invalid timestamp")
    d=datetime.fromisoformat(t.replace("Z","+00:00"))
    if d.tzinfo is None or d.utcoffset() is None:raise ValueError("aware timestamp required")
    return d

def verify_official_filing_asof(candidate,filing):
    """Return reason-only decision, no orders and no issuer claims.

    Canonical CIK resolution must have been completed against an official
    issuer registry; a news symbols[] tag does not supply it.
    """
    try:
        decision=aware(candidate["decision_at"])
        seen=aware(filing["first_seen_at"])
        accepted=aware(filing["verified_primary_header_accepted_at"])
        cik=str(candidate["issuer_cik"]).lstrip("0")
        doc_cik=str(filing["issuer_cik"]).lstrip("0")
        if not cik or not doc_cik or cik!=doc_cik:
            return "CIK_NOT_CONFIRMED"
        if filing.get("form") not in ALLOWED_FORMS:return "UNSUPPORTED_FORM"
        if filing.get("primary_header_verified") is not True:return "PRIMARY_HEADER_NOT_VERIFIED"
        if accepted>decision:return "FILING_ACCEPTED_AFTER_DECISION"
        if seen>decision:return "FILING_FIRST_OBSERVED_AFTER_DECISION"
        if seen<accepted:return "INVALID_RECEIPT_CHRONOLOGY"
        if filing.get("issuer_guidance_verified") is not True:
            return "FILING_DOES_NOT_VERIFY_ISSUER_GUIDANCE"
        return "ASOF_ISSUER_GUIDANCE_CORROBORATED_RESEARCH_ONLY"
    except (KeyError,ValueError,TypeError):
        return "INSUFFICIENT_POINT_IN_TIME_EVIDENCE"
