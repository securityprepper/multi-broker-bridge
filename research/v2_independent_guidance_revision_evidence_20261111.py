"""V2 research-only issuer guidance + independent estimate-revision confluence.

Pure as-of evidence gate. Not an alert signal, trading permission or profitability
claim. Never infers consensus or issuer guidance from headline strings/ticker tags.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
import re

class EvidenceError(ValueError):
    pass

def utc(value):
    if not isinstance(value,str):
        raise EvidenceError("timestamp missing")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise EvidenceError("malformed timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise EvidenceError("naive timestamp")
    return dt.astimezone(timezone.utc)

def amount(value):
    if isinstance(value,(bool,float)):
        raise EvidenceError("exact decimal required")
    try:
        d=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError) as exc:
        raise EvidenceError("invalid decimal") from exc
    if not d.is_finite() or d <= 0:
        raise EvidenceError("nonpositive or nonfinite decimal")
    return d

def original_sha256(value):
    """Only a capture-computed SHA256 digest of the *original* received text."""
    return isinstance(value,str) and bool(re.fullmatch(r"[a-f0-9]{64}",value))

def sec_archive_url(value,cik):
    if not isinstance(value,str):return False
    p=urlparse(value)
    return (p.scheme=="https" and p.netloc=="www.sec.gov"
            and bool(re.fullmatch(
                rf"/Archives/edgar/data/{int(cik)}/\d{{18}}/[A-Za-z0-9_.%-]+",
                p.path)) and not p.query and not p.fragment)

def readiness(issuer,revision,asof,negative_events=()):
    """Check positive issuer guidance and independently sourced numeric revisions.

    Returns an evidence readiness state, not an entry recommendation.
    All times are point-in-time and independent issuance/first observation.
    """
    now=utc(asof)
    def out(status):
        return {"status":status,"order_authorized":False,
                "signal_authorized":False,"research_only":True}
    if not issuer or not isinstance(issuer,dict):
        return out("NO_OFFICIAL_ISSUER_EVIDENCE")
    try:
        cik=int(issuer["cik"])
        if cik<=0 or not sec_archive_url(issuer.get("sec_exhibit_url"),cik):
            return out("INVALID_OFFICIAL_SOURCE")
        if issuer.get("official_event_type") not in ("RAISED_EPS_GUIDANCE","RAISED_REVENUE_GUIDANCE"):
            return out("NOT_RAISED_GUIDANCE")
        event_publish=utc(issuer["release_published_at"])
        sec_accepted=utc(issuer["sec_accepted_at"])
        event_seen=utc(issuer["first_observed_at"]) # first receipt of *issuer release*
        if any(t>now for t in (event_publish,sec_accepted,event_seen)):
            return out("OFFICIAL_EVENT_NOT_YET_OBSERVED")
        if event_seen < event_publish:
            return out("INCONSISTENT_RELEASE_PROVENANCE")
        # An issuer release can legitimately be published/observed BEFORE
        # the related Form 8-K is SEC-accepted. This is not an invalid event.
        # However the independent SEC exhibit must itself have been received
        # and immutable BEFORE the current research decision.
        if not (issuer.get("sec_exhibit_first_observed_at") and
                original_sha256(issuer.get("sec_exhibit_sha256"))):
            return out("MISSING_SEC_FIRST_SEEN_OR_ORIGINAL_HASH")
        if not original_sha256(issuer.get("release_original_sha256")):
            return out("MISSING_RELEASE_ORIGINAL_HASH")
        sec_seen=utc(issuer["sec_exhibit_first_observed_at"])
        if sec_seen > now:
            return out("SEC_EXHIBIT_NOT_YET_OBSERVED")
        if sec_seen < sec_accepted:
            return out("INCONSISTENT_SEC_PROVENANCE")
        if amount(issuer["new_guidance"])<=amount(issuer["prior_guidance"]):
            return out("NOT_RAISED_GUIDANCE")
        period=issuer.get("fiscal_period")
        units=issuer.get("units")
        share_basis=issuer.get("share_basis")
        if not period or units not in ("USD_PER_DILUTED_SHARE","USD_MILLIONS"):
            return out("UNVERIFIED_FISCAL_UNITS")
        if share_basis not in ("AS_REPORTED_UNADJUSTED","SPLIT_ADJUSTED_VERIFIED"):
            return out("UNVERIFIED_SHARE_BASIS")
    except (KeyError,TypeError,ValueError,EvidenceError):
        return out("INVALID_OFFICIAL_SOURCE")
    if not revision or not isinstance(revision,dict):
        return out("NO_INDEPENDENT_ANALYST_REVISION")
    try:
        if int(revision["issuer_cik"])!=cik:
            return out("REVISION_WRONG_ISSUER")
        if revision.get("origin_type")!="INDEPENDENT_ANALYST_ESTIMATE":
            return out("REVISION_NOT_INDEPENDENT")
        if (not revision.get("analyst_firm_id") or
            not revision.get("source_document_id") or
            not original_sha256(revision.get("revision_original_sha256"))):
            return out("UNVERIFIED_REVISION_ORIGIN")
        if (revision.get("fiscal_period")!=period or revision.get("units")!=units or
            revision.get("share_basis")!=share_basis):
            return out("INCOMPARABLE_REVISION_BASIS")
        revision_publish=utc(revision["published_at"])
        revision_seen=utc(revision["first_observed_at"])
        if revision_publish>now or revision_seen>now:
            return out("REVISION_NOT_YET_OBSERVED")
        if revision_publish < event_publish or revision_seen < revision_publish:
            return out("REVISION_NOT_CAUSAL_OR_UNVERIFIED")
        if amount(revision["new_estimate"])<=amount(revision["old_estimate"]):
            return out("REVISION_NOT_POSITIVE")
    except (KeyError,TypeError,ValueError,EvidenceError):
        return out("REVISION_DATA_INVALID")
    try:
        for negative in negative_events:
            if int(negative.get("issuer_cik",-1))!=cik:
                continue
            seen=utc(negative["first_observed_at"])
            if seen<=now and (negative.get("official_negative") is True or
                              negative.get("verified_analyst_downgrade") is True):
                return out("VERIFIED_NEGATIVE_NEWS_VETO")
    except (TypeError,KeyError,ValueError,EvidenceError):
        return out("NEGATIVE_NEWS_EVIDENCE_INVALID")
    return out("INDEPENDENT_CONFLUENCE_EVIDENCE_READY_SHADOW_ONLY")

def inventory_articles(articles):
    """Coverage audit of licensed article metadata without disclosing content."""
    if not isinstance(articles,list):raise EvidenceError("article list required")
    required={"news_id","created_at","updated_at","headline","source","symbols"}
    needed={"issuer_cik","official_guidance_value","prior_guidance_value",
            "fiscal_period","share_basis","independent_analyst_old_estimate",
            "independent_analyst_new_estimate","independent_revision_published_at",
            "first_observed_at","sec_exhibit_url"}
    summary={"articles":0,"base_fields_present":0,"numeric_issuer_and_revision_ready":0,
             "missing_independent_revision":0,"missing_official_guidance":0}
    for a in articles:
        if not isinstance(a,dict):continue
        summary["articles"]+=1
        if required<=set(a):summary["base_fields_present"]+=1
        if needed<=set(a):
            summary["numeric_issuer_and_revision_ready"]+=1
        else:
            if not {"independent_analyst_old_estimate","independent_analyst_new_estimate",
                    "independent_revision_published_at"}<=set(a):
                summary["missing_independent_revision"]+=1
            if not {"issuer_cik","official_guidance_value","prior_guidance_value",
                    "sec_exhibit_url"}<=set(a):
                summary["missing_official_guidance"]+=1
    return summary
