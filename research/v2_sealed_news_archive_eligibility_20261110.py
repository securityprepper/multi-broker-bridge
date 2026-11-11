"""Research-only, strict as-of audit of sealed catalyst-news archives.

This never fetches market data, calls a broker, or constructs an order.
It does not infer an issuer or guidance upgrade from a headline.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path

CT = ZoneInfo("America/Chicago")
CUTOFF = time(13, 15)
CATEGORIES = {"EARNINGS_RELEASE_CANDIDATE_UNVERIFIED",
              "POSITIVE_NEWS_CANDIDATE_UNVERIFIED"}

class InvalidArchive(ValueError):
    pass

def timestamp(s):
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (AttributeError,ValueError,TypeError) as exc:
        raise InvalidArchive("invalid timestamp") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise InvalidArchive("naive timestamp")
    return t.astimezone(timezone.utc)

def audit(records, asof_utc):
    """Counts only records observed at or before as-of; no future leakage."""
    asof = timestamp(asof_utc)
    counts = Counter()
    seen = set()
    observed = []
    for row in records:
        if not isinstance(row,dict) or not isinstance(row.get("article"),dict):
            raise InvalidArchive("malformed evidence")
        article = row["article"]
        if row.get("orders_submitted") != 0 or row.get("trade_authorized") is not False:
            raise InvalidArchive("not a research-only evidence artifact")
        event_id = article.get("news_id")
        if not isinstance(event_id,str) or not event_id:
            raise InvalidArchive("news ID missing")
        obs = timestamp(article["observed_at_utc"])
        pub = timestamp(article["published_at_utc"])
        if obs > asof:
            counts["future_abstain"] += 1
            continue
        if pub > obs:
            counts["publication_after_observation_error"] += 1
            continue
        if event_id in seen:
            counts["duplicate_id"] += 1
            continue
        seen.add(event_id)
        counts["unique_observed"] += 1
        if row.get("prospective_archive") is True:
            counts["prospective"] += 1
        if article.get("realtime_fresh") is True:
            counts["news_under_180s"] += 1
        if article.get("category") not in CATEGORIES:
            continue
        counts["earnings_or_positive_headline_candidate"] += 1
        if obs.astimezone(CT).time() >= CUTOFF:
            counts["after_1315_ct"] += 1
            continue
        if not row.get("issuer_verified"):
            counts["missing_verified_primary_issuer"] += 1
            continue
        if not row.get("guidance_change_verified"):
            counts["missing_verified_guidance_upgrade"] += 1
            continue
        # A verified news item alone STILL cannot be a trade: need
        # as-of quotes, liquidity, model, risk, approved order route.
        counts["verified_catalyst_still_needs_quote_and_paper_gate"] += 1
    return {"counts":dict(counts),"evaluated_asof_utc":asof.isoformat(),
            "research_only":True,"broker_access":False,"orders_submitted":0,
            "approved_trades":0}

def read_archive(directory,asof_utc):
    directory=Path(directory)
    if not directory.is_absolute() or not directory.is_dir():
        raise InvalidArchive("absolute archive directory required")
    records=[]
    for p in sorted(directory.glob("*.json")):
        if not p.is_file() or p.is_symlink():
            raise InvalidArchive("invalid archive object")
        records.append(json.loads(p.read_text(encoding="utf-8")))
    return audit(records,asof_utc)
