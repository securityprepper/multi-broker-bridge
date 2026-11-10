"""V2 research-only point-in-time catalyst/issuer safety gate.

Pure functions. Never contacts a broker, creates orders, or modifies a live task.
Never use an article's suggested symbol as independent issuer verification.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")
ENTRY_CUTOFF = time(13, 15)
VALID_EVENT_TYPES = frozenset({"RAISED_REVENUE_GUIDANCE", "RAISED_EPS_GUIDANCE", "FDA_APPROVAL"})
ALLOWED_SOURCE = frozenset({"COMPANY_IR_RELEASE", "SEC_8K", "FDA_OFFICIAL"})

class InvalidEvent(ValueError):
    pass

def stamp(x):
    if not isinstance(x, str):
        raise InvalidEvent("timestamp missing")
    try:
        t = datetime.fromisoformat(x.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidEvent("malformed timestamp") from exc
    if t.tzinfo is None:
        raise InvalidEvent("timestamp must carry timezone")
    return t.astimezone(timezone.utc)

def positive_decimal(value):
    if isinstance(value, (float, bool)):
        raise InvalidEvent("decimal string required, no float")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise InvalidEvent("invalid numeric guidance")
    if not d.is_finite() or d <= 0:
        raise InvalidEvent("guidance must be positive")
    return d

def result(status, *, reason):
    return {"status": status, "reason": reason, "order_authorized": False,
            "source": "V2_RESEARCH_ONLY"}

def evaluate(article, issuer_evidence, instrument, as_of_utc, *, quote=None):
    """Fail closed; validated evidence must have been available BEFORE as_of."""
    asof = stamp(as_of_utc)
    observed = stamp(article["observed_at_utc"])
    published = stamp(article["published_at_utc"])
    if observed > asof or published > asof:
        return result("NOT_YET_OBSERVED", reason="future article or publication")
    if not isinstance(article.get("symbols"), list) or instrument.get("symbol") not in article["symbols"]:
        return result("SYMBOL_NOT_TAGGED", reason="not a candidate for this instrument")
    if not issuer_evidence:
        return result("UNVERIFIED_ISSUER", reason="article tag and company name are insufficient")
    verified_at = stamp(issuer_evidence["verified_at_utc"])
    if verified_at > asof:
        return result("UNVERIFIED_ISSUER", reason="official issuer evidence not yet observed")
    if issuer_evidence.get("source_type") not in ALLOWED_SOURCE:
        return result("UNVERIFIED_PRIMARY_SOURCE", reason="primary filing/release/FDA source required")
    if issuer_evidence.get("official_event_type") not in VALID_EVENT_TYPES:
        return result("UNVERIFIED_CATALYST", reason="material event type not independently established")
    # Research keys are illustrative; a real order router must use audited SEC CIK/LEI
    # mappings, instrument listing identity, and separately commissioned broker gates.
    official_issuer = issuer_evidence.get("canonical_issuer_key")
    listed_issuer = instrument.get("canonical_issuer_key")
    if not official_issuer or not listed_issuer:
        return result("UNVERIFIED_ISSUER", reason="authenticated issuer keys missing")
    if official_issuer != listed_issuer:
        return result("WRONG_LISTED_ISSUER", reason="official catalyst belongs to a different company")
    chicago = asof.astimezone(CHICAGO)
    if chicago.time() > ENTRY_CUTOFF:
        return result("AFTER_ENTRY_CUTOFF", reason="past 13:15 Chicago for new entry")
    kind = issuer_evidence["official_event_type"]
    if kind.startswith("RAISED_"):
        old = positive_decimal(issuer_evidence.get("previous_guidance"))
        new = positive_decimal(issuer_evidence.get("new_guidance"))
        if new <= old:
            return result("NOT_AN_UPGRADE", reason="new guidance is not higher")
        prior_consensus = issuer_evidence.get("consensus_frozen_at_utc")
        if not prior_consensus or stamp(prior_consensus) >= published:
            return result("UNVERIFIED_PRIOR_CONSENSUS", reason="consensus not frozen before event")
    if quote is None:
        return result("NO_EXECUTABLE_QUOTE", reason="fresh bid/ask and supported session absent")
    quote_at = stamp(quote["observed_at_utc"])
    if quote_at > asof or (asof-quote_at)>timedelta(seconds=60):
        return result("STALE_OR_FUTURE_QUOTE", reason="no as-of executable market-data evidence")
    bid=positive_decimal(quote["bid"]);ask=positive_decimal(quote["ask"])
    if ask < bid or (ask-bid)/ask > Decimal("0.01"):
        return result("UNSAFE_SPREAD", reason="crossed/too-wide bid ask")
    if not quote.get("session_supported") or not quote.get("protective_exit_supported"):
        return result("NO_VERIFIED_PROTECTION", reason="session protection not guaranteed")
    return result("RESEARCH_SHADOW_ELIGIBLE_ONLY",
                  reason="issuer/catalyst/quote gates pass; separate PAPER authorization still required")

def audit_recent(feed, at_utc):
    """Read-only cohort of news candidates; never infer a profitable trade."""
    now = stamp(at_utc)
    records = feed.get("recent", [])
    if not isinstance(records, list):
        raise InvalidEvent("recent news must be a list")
    count=0; after_cutoff=0; pending=0
    for e in records:
        if e.get("category") not in ("EARNINGS_RELEASE_CANDIDATE_UNVERIFIED","POSITIVE_NEWS_CANDIDATE_UNVERIFIED"):
            continue
        count += 1
        observed=stamp(e["observed_at_utc"])
        if observed > now:
            pending += 1
        elif observed.astimezone(CHICAGO).time() > ENTRY_CUTOFF:
            after_cutoff += 1
    return {"candidate_headlines": count, "arrived_after_1315_ct": after_cutoff,
            "not_yet_observed": pending, "order_authorized": False}
