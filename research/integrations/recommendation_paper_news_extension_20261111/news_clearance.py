"""Mandatory fail-closed root-published, point-in-time news eligibility for PAPER BUY only.

The V2 reducer checks completeness and materiality; a separate independently
authorized publisher must populate immutable root-owned attestations. This
module does not fetch news, attest provider coverage, or place broker orders.
Never interpret a missing document as clear.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from .news_eligibility import evaluate_news_asof, CLEAR, UNKNOWN

ROOT = Path("/etc/securityprepper/recommendation-paper-bridge/news-clearance")
SYMBOL = re.compile(r"[A-Z][A-Z0-9.]{0,11}\Z")
MAX_BYTES = 256 * 1024

class NewsBlocked(ValueError):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__(status + ":" + reason)

def _utc(value):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if t.tzinfo is None:
            raise ValueError("naive")
        return t.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise NewsBlocked(UNKNOWN, "ATTESTATION_TIMESTAMP_INVALID")

def _read_protected(symbol, root=ROOT):
    if not SYMBOL.fullmatch(symbol):
        raise NewsBlocked(UNKNOWN, "BAD_SYMBOL")
    try:
        parent = root.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0
                or parent.st_mode & 0o022):
            raise NewsBlocked(UNKNOWN, "CLEARANCE_DIRECTORY_UNTRUSTED")
        path = root / (symbol + ".json")
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0
                    or st.st_mode & 0o022 or st.st_nlink != 1
                    or st.st_size <= 0 or st.st_size > MAX_BYTES):
                raise NewsBlocked(UNKNOWN, "CLEARANCE_FILE_UNTRUSTED")
            with os.fdopen(fd, "rb", closefd=False) as f:
                raw = f.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise NewsBlocked(UNKNOWN, "CLEARANCE_FILE_OVERSIZE")
        finally:
            os.close(fd)
        return json.loads(raw), sha256(raw).hexdigest()
    except NewsBlocked:
        raise
    except (OSError, ValueError, TypeError, UnicodeError):
        raise NewsBlocked(UNKNOWN, "TRUSTED_CLEARANCE_UNAVAILABLE")

def require_clear(symbol, now, loader=None):
    """Return evidence digest only on a CURRENT, trusted verified V2 clear.

    loader is exclusively for broker-free tests; production always reads the
    fixed root-owned path rather than caller-supplied recommendation text.
    """
    if now.tzinfo is None:
        raise NewsBlocked(UNKNOWN, "DECISION_CLOCK_UNTRUSTED")
    now = now.astimezone(timezone.utc)
    try:
        doc, digest = (loader(symbol) if loader is not None
                       else _read_protected(symbol))
    except NewsBlocked:
        raise
    except Exception as exc:
        raise NewsBlocked(UNKNOWN, "TRUSTED_CLEARANCE_UNAVAILABLE") from exc
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise NewsBlocked(UNKNOWN, "CLEARANCE_SCHEMA_INVALID")
    if doc.get("symbol") != symbol or doc.get("producer") != "trusted_issuer_sec_news_attestor_v1":
        raise NewsBlocked(UNKNOWN, "CLEARANCE_PROVENANCE_MISMATCH")
    published = _utc(doc.get("produced_at_utc"))
    if not timedelta(0) <= now - published <= timedelta(seconds=60):
        raise NewsBlocked(UNKNOWN, "CLEARANCE_NOT_CURRENT")
    try:
        decision = evaluate_news_asof(
            symbol=symbol, exchange=doc["exchange"],
            issuer_cik=doc["issuer_cik"], asof_utc=now.isoformat(),
            identity=doc["identity"], coverage=doc["coverage"],
            evidence=doc["evidence"])
    except (KeyError, ValueError, TypeError):
        raise NewsBlocked(UNKNOWN, "CLEARANCE_EVIDENCE_MALFORMED")
    if decision.get("status") != CLEAR or decision.get("paper_order_eligible") is not True:
        raise NewsBlocked(decision.get("status", UNKNOWN),
                          decision.get("reason", "NEWS_NOT_CLEARED"))
    return {"status":CLEAR, "reason":decision["reason"],
            "asof_utc":now.isoformat(), "attestation_produced_at_utc":published.isoformat(),
            "evidence_sha256":digest, "issuer_cik":doc["issuer_cik"],
            "exchange":doc["exchange"]}
