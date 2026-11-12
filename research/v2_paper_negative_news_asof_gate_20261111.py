"""Research-only, fail-closed issuer-specific negative-news BUY eligibility reducer.

Not an executor, recommendation, news fetcher, or actual clearance source.
It accepts independently verified evidence objects; it must NEVER be used
to convert missing coverage or historical headline-only archives into BUY.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

CATEGORIES = frozenset({
    "earnings", "guidance", "dilution", "restatement", "liquidity",
    "litigation", "regulatory", "analyst_downgrade",
    "corporate_development", "imminent_event",
})
SOURCES = frozenset({"sec_edgar", "issuer_ir", "licensed_news"})
ADVERSE = "NEWS_MATERIAL_ADVERSE"
WATCH = "NEWS_REVIEW_WATCH_ONLY"
UNKNOWN = "NEWS_UNKNOWN"
CLEAR = "NEWS_CLEAR_ASOF"

def _as_utc(raw: Any) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp without zone")
    return dt.astimezone(timezone.utc)

def _valid_cik(raw: Any) -> bool:
    return isinstance(raw, str) and raw.isdigit() and len(raw) == 10 and int(raw) != 0

def _result(status: str, reason: str, decision_at: datetime) -> dict:
    return {"status": status, "reason": reason,
            "asof_utc": decision_at.isoformat(), "paper_order_eligible": status == CLEAR}

def evaluate_news_asof(
    *, symbol: str, exchange: str, issuer_cik: str, asof_utc: str,
    identity: dict, coverage: list[dict], evidence: list[dict]
) -> dict:
    """Produce a research-only potential BUY news clearance decision.

    All inputs must be genuine independently collected records when deployed.
    A clear response here is not an authorization without trusted producer
    provenance, account-specific gates and a final recheck at order time.
    """
    now = _as_utc(asof_utc)
    if not (isinstance(symbol, str) and symbol == symbol.upper()
            and 1 <= len(symbol) <= 12 and symbol.replace(".", "").isalnum()
            and isinstance(exchange, str) and exchange in {"NYSE", "NASDAQ", "AMEX"}
            and _valid_cik(issuer_cik)):
        return _result(WATCH, "UNRESOLVED_ISSUER_IDENTITY", now)
    if not isinstance(identity, dict) or (
        identity.get("verified") is not True
        or identity.get("symbol") != symbol
        or identity.get("exchange") != exchange
        or identity.get("issuer_cik") != issuer_cik
    ):
        return _result(WATCH, "UNRESOLVED_ISSUER_IDENTITY", now)
    try:
        id_seen = _as_utc(identity.get("first_observed_at"))
        if id_seen > now:
            return _result(WATCH, "IDENTITY_NOT_AVAILABLE_ASOF", now)
    except (ValueError, TypeError):
        return _result(WATCH, "IDENTITY_PROVENANCE_UNKNOWN", now)

    if not isinstance(evidence, list) or not isinstance(coverage, list):
        return _result(UNKNOWN, "NEWS_INPUT_NOT_COMPLETE", now)
    for item in evidence:
        if not isinstance(item, dict):
            return _result(WATCH, "MALFORMED_OR_CONTRADICTORY_EVIDENCE", now)
        if item.get("symbol") != symbol or item.get("issuer_cik") != issuer_cik:
            continue  # unrelated issuer cannot veto or clear this one
        if item.get("source") not in SOURCES:
            return _result(WATCH, "UNTRUSTED_OR_CONTRADICTORY_NEWS", now)
        try:
            published = _as_utc(item["published_at"])
            first_seen = _as_utc(item["first_observed_at"])
        except (ValueError, TypeError, KeyError):
            return _result(WATCH, "NEWS_TIME_PROVENANCE_MISSING", now)
        if first_seen > now or published > now:
            continue  # cannot retrospectively veto a historical BUY
        if not item.get("source_reference") or not item.get("content_hash"):
            return _result(WATCH, "NEWS_SOURCE_PROVENANCE_MISSING", now)
        category = item.get("category")
        status = item.get("status")
        if category not in CATEGORIES:
            return _result(WATCH, "UNCLASSIFIED_COMPANY_NEWS", now)
        if status == "material_adverse_verified":
            return _result(ADVERSE, f"ADVERSE_{category.upper()}", now)
        if status in {"pending_allegation", "contradictory", "review_needed", "materiality_unknown"}:
            return _result(WATCH, f"REVIEW_{category.upper()}", now)
        if status != "verified_nonmaterial":
            return _result(WATCH, "UNSUPPORTED_NEWS_CLASSIFICATION", now)

    # Evidence absence is never clearance. Independent source attestations,
    # complete coverage and actual timely observations are all mandatory.
    acceptable = {}
    for row in coverage:
        if not isinstance(row, dict):
            return _result(UNKNOWN, "COVERAGE_MALFORMED", now)
        if row.get("symbol") != symbol or row.get("issuer_cik") != issuer_cik:
            continue
        src = row.get("source")
        if src not in SOURCES or row.get("verified_complete") is not True:
            continue
        try:
            observed = _as_utc(row["first_observed_at"])
            since = _as_utc(row["coverage_since"])
            until = _as_utc(row["coverage_through"])
        except (KeyError, ValueError, TypeError):
            continue
        if not (timedelta(0) <= now - observed <= timedelta(minutes=2)
                and since <= now - timedelta(days=30)
                and now - timedelta(seconds=60) <= until <= now
                and row.get("source_reference") and row.get("content_hash")):
            continue
        try:
            covered = frozenset(row["categories"])
        except (TypeError, KeyError):
            continue
        if not covered <= CATEGORIES:
            continue
        acceptable[src] = acceptable.get(src, frozenset()) | covered

    if not {"sec_edgar", "issuer_ir", "licensed_news"} <= set(acceptable):
        return _result(UNKNOWN, "INDEPENDENT_ISSUER_SEC_NEWS_COVERAGE_MISSING", now)
    if acceptable["licensed_news"] != CATEGORIES:
        return _result(UNKNOWN, "ADVERSE_NEWS_CATEGORY_COVERAGE_MISSING", now)
    if not {"earnings", "guidance", "dilution", "restatement", "liquidity",
            "litigation", "regulatory", "corporate_development"} <= acceptable["sec_edgar"]:
        return _result(UNKNOWN, "MATERIAL_SEC_FILING_COVERAGE_MISSING", now)
    if not {"earnings", "guidance", "corporate_development"} <= acceptable["issuer_ir"]:
        return _result(UNKNOWN, "ISSUER_RELEASE_COVERAGE_MISSING", now)
    return _result(CLEAR, "COMPLETE_VERIFIED_NO_MATERIAL_ADVERSE_ASOF", now)
