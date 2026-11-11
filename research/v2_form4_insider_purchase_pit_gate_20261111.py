"""Research-only SEC Form 4 point-in-time open-market insider purchase gate.

Official XML / SEC accepted metadata are not proof of our collector's original
first-seen time. This module never issues broker orders or user alerts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import re
import xml.etree.ElementTree as ET

MAX_XML_BYTES = 256_000
MIN_DIRECT_PURCHASE_USD = Decimal("250000")
CIK_RE = re.compile(r"^\d{1,10}$")
ACC_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")


@dataclass(frozen=True)
class Form4Result:
    decision: str
    reasons: tuple[str, ...]
    issuer_cik: str | None
    accession: str | None
    direct_purchased_usd: str
    first_observed_at_utc: str | None
    accepted_at_utc: str | None
    content_sha256: str | None
    flagged_open_market_purchase: bool = False
    allowed_to_trade: bool = False


def timestamp(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def normalized_cik(v: str | None):
    if v is None or not CIK_RE.fullmatch(v.strip()):
        return None
    return str(int(v.strip()))


def xmltext(element, path):
    v = element.findtext(path)
    return v.strip() if v else None


def explicit_boolean(v):
    if v in ("true", "1", "TRUE", "True"):
        return True
    if v in ("false", "0", "FALSE", "False"):
        return False
    return None


def value(v):
    if v is None:
        return None
    try:
        d = Decimal(v)
        return d if d.is_finite() and d > 0 else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def evaluate_form4(
    xml_bytes: bytes,
    *,
    expected_issuer_cik: str,
    accession: str,
    sec_accepted_at: str,
    first_observed_at: str | None,
    decision_at: str,
    expected_symbol: str | None = None,
) -> Form4Result:
    """Compute screening readiness, never an order or a profit prediction.

    Strictly requires SEC accepted and truly observed times before decision.
    Returns RESEARCH_CANDIDATE_ONLY for a qualifying filing; never BUY.
    """
    reasons = []
    accepted = timestamp(sec_accepted_at)
    observed = timestamp(first_observed_at)
    decision = timestamp(decision_at)
    accession_ok = bool(ACC_RE.fullmatch(accession))
    expected = normalized_cik(expected_issuer_cik)
    digest = hashlib.sha256(xml_bytes).hexdigest() if isinstance(xml_bytes, bytes) else None
    if not isinstance(xml_bytes, bytes) or not xml_bytes or len(xml_bytes) > MAX_XML_BYTES:
        reasons.append("XML_INVALID_SIZE")
        return Form4Result("REJECT", tuple(reasons), expected, accession, "0",
                           first_observed_at, sec_accepted_at, digest)
    if b"<!DOCTYPE" in xml_bytes.upper() or b"<!ENTITY" in xml_bytes.upper():
        reasons.append("XML_PROHIBITED_DTD")
        return Form4Result("REJECT", tuple(reasons), expected, accession, "0",
                           first_observed_at, sec_accepted_at, digest)
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        reasons.append("XML_PARSE_FAILURE")
        return Form4Result("REJECT", tuple(reasons), expected, accession, "0",
                           first_observed_at, sec_accepted_at, digest)
    issuer_cik = normalized_cik(xmltext(root, "issuer/issuerCik"))
    if root.tag != "ownershipDocument":
        reasons.append("NOT_FORM4_OWNERSHIP_XML")
    if xmltext(root, "documentType") != "4":
        reasons.append("NOT_ORIGINAL_FORM4")
    if not accession_ok:
        reasons.append("ACCESSION_INVALID")
    if issuer_cik is None or issuer_cik != expected:
        reasons.append("ISSUER_CIK_MISMATCH")
    if expected_symbol and (xmltext(root, "issuer/issuerTradingSymbol") or "").upper() != expected_symbol.upper():
        reasons.append("ISSUER_SYMBOL_MISMATCH")
    plan = explicit_boolean(xmltext(root, "aff10b5One"))
    if plan is True:
        reasons.append("AFFIRMED_10B5_1_PLAN")
    elif plan is None:
        reasons.append("AFF10B5_1_STATUS_UNVERIFIED")
    relationships = root.findall("reportingOwner/reportingOwnerRelationship")
    if not relationships or not any(
        explicit_boolean(xmltext(r, "isOfficer")) is True or explicit_boolean(xmltext(r, "isDirector")) is True
        for r in relationships
    ):
        reasons.append("NO_CONFIRMED_OFFICER_OR_DIRECTOR")
    # Any combined sale or derivative exercise creates ambiguity in the
    # purchase interpretation. Fail closed rather than label a net company buy.
    transactions = root.findall(".//nonDerivativeTransaction")
    if any(xmltext(t, "transactionCoding/transactionCode") == "S" for t in transactions):
        reasons.append("SAME_FORM_SALE_MIXED")
    if any(xmltext(t, "transactionCoding/transactionCode") in {"M", "F"} for t in transactions):
        reasons.append("SAME_FORM_COMPENSATION_OR_WITHHOLDING_MIXED")
    if root.findall(".//derivativeTransaction"):
        reasons.append("DERIVATIVE_TRANSACTION_PRESENT")
    purchases = Decimal("0")
    for t in transactions:
        if xmltext(t, "transactionCoding/transactionCode") != "P":
            continue
        shares = value(xmltext(t, "transactionAmounts/transactionShares/value"))
        price = value(xmltext(t, "transactionAmounts/transactionPricePerShare/value"))
        title = (xmltext(t, "securityTitle/value") or "").casefold()
        direct = xmltext(t, "ownershipNature/directOrIndirectOwnership/value")
        acquisition = xmltext(t, "transactionAmounts/transactionAcquiredDisposedCode/value")
        txdate = xmltext(t, "transactionDate/value")
        try:
            dated = date.fromisoformat(txdate) if txdate else None
        except ValueError:
            dated = None
        if not title.startswith("common stock") and not title.startswith("class a common stock"):
            reasons.append("NOT_ELIGIBLE_COMMON_STOCK")
            continue
        if direct != "D":
            reasons.append("INDIRECT_OWNERSHIP_AMBIGUITY")
            continue
        if acquisition != "A" or shares is None or price is None:
            reasons.append("P_AMOUNT_OR_ACQUISITION_INVALID")
            continue
        if not dated or not accepted or (accepted.date()-dated).days not in range(0, 6):
            reasons.append("TRADE_DATE_STALE_OR_UNKNOWN")
            continue
        purchases += shares * price
    flagged = purchases >= MIN_DIRECT_PURCHASE_USD
    if not flagged:
        reasons.append("NO_QUALIFIED_LARGE_DIRECT_P_TRANSACTION")
    if accepted is None or decision is None or accepted > decision:
        reasons.append("INVALID_OR_FUTURE_SEC_ACCEPTANCE")
    if observed is None:
        reasons.append("MISSING_ORIGINAL_FIRST_SEEN")
    elif decision is None or observed > decision or accepted is None or observed < accepted:
        reasons.append("FIRST_SEEN_OUTSIDE_CAUSAL_WINDOW")
    if not reasons:
        return Form4Result("RESEARCH_CANDIDATE_ONLY", tuple(), issuer_cik, accession,
                           str(purchases), first_observed_at, sec_accepted_at, digest,
                           flagged_open_market_purchase=True, allowed_to_trade=False)
    return Form4Result("REJECT", tuple(sorted(set(reasons))), issuer_cik, accession,
                       str(purchases), first_observed_at, sec_accepted_at, digest,
                       flagged_open_market_purchase=flagged, allowed_to_trade=False)