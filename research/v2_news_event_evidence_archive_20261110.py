#!/usr/bin/env python3
"""Read-only, append-only news provenance archive for V2 EVENT RESEARCH.

Consumes the existing GET-only news observer's local JSON. Zero network,
broker credentials, account APIs, order routing, notifications or Pushover.
Never interprets a ticker tag/headline as verified issuer or BUY signal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Chicago")
VALID_CATEGORIES = {
    "OTHER_NEWS", "EARNINGS_SCHEDULE_MENTION_UNVERIFIED",
    "EARNINGS_RELEASE_CANDIDATE_UNVERIFIED", "POSITIVE_NEWS_CANDIDATE_UNVERIFIED",
    "REVIEW_POSSIBLY_NEGATIVE",
}
FIELDS = ("news_id", "published_at_utc", "observed_at_utc", "headline",
          "symbols", "category", "source", "realtime_fresh", "latency_seconds")

class EvidenceError(ValueError):
    pass

def timestamp(value):
    if not isinstance(value, str):
        raise EvidenceError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as ex:
        raise EvidenceError("invalid timestamp") from ex
    if parsed.tzinfo is None:
        raise EvidenceError("timezone required")
    return parsed.astimezone(timezone.utc)

def iso(value):
    return value.astimezone(timezone.utc).isoformat()

def holiday_gate(cache, now):
    """Fail closed on unknown state, pause, stale revision or elapsed boundary."""
    if not isinstance(cache, dict):
        return False
    if cache.get("timezone") != "America/Chicago":
        return False
    if cache.get("paused") is not False or cache.get("calendar_coverage_ok") is not True:
        return False
    try:
        rev = int(cache["calendar_revision"])
        boundary = timestamp(cache["next_check_at"])
        coverage = date.fromisoformat(cache["calendar_coverage_through"])
    except (KeyError, ValueError, TypeError, EvidenceError):
        return False
    return rev >= 2 and now < boundary and coverage >= now.astimezone(TZ).date()

def canonical_article(article, feed_asof):
    if not isinstance(article, dict):
        raise EvidenceError("article not an object")
    result = {}
    for key in FIELDS:
        if key not in article:
            raise EvidenceError("article missing " + key)
        result[key] = article[key]
    if not isinstance(result["news_id"], str) or not result["news_id"].strip() or len(result["news_id"]) > 120:
        raise EvidenceError("invalid news ID")
    if (not isinstance(result["headline"], str) or
            not (1 <= len(result["headline"]) <= 900)):
        raise EvidenceError("invalid headline")
    if (not isinstance(result["source"], str) or
            not (1 <= len(result["source"]) <= 120)):
        raise EvidenceError("invalid source")
    if (not isinstance(result["symbols"], list) or len(result["symbols"]) > 100 or
            any(not isinstance(x, str) or len(x) > 20 for x in result["symbols"])):
        raise EvidenceError("invalid symbols")
    if result["category"] not in VALID_CATEGORIES:
        raise EvidenceError("invalid category")
    if not isinstance(result["realtime_fresh"], bool):
        raise EvidenceError("invalid realtime freshness")
    if not isinstance(result["latency_seconds"], (int, float)) or isinstance(result["latency_seconds"], bool):
        raise EvidenceError("invalid news latency")
    published = timestamp(result["published_at_utc"])
    observed = timestamp(result["observed_at_utc"])
    if observed > feed_asof + timedelta(seconds=5):
        raise EvidenceError("future article relative to feed snapshot")
    result["published_at_utc"] = iso(published)
    result["observed_at_utc"] = iso(observed)
    return result

def content_digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf8")).hexdigest()

def write_once(path, record):
    """Atomic create-only link, no overwrite even during concurrent runs."""
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    raw = (json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()
    fd, tempname = tempfile.mkstemp(prefix=".new-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(tempname, path, follow_symlinks=False)
            try:
                directory_fd = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except OSError:
                pass
            return True
        except FileExistsError:
            old = json.loads(path.read_text(encoding="utf8"))
            if old.get("content_digest") != record.get("content_digest"):
                raise EvidenceError("same article ID conflicts with sealed original")
            return False
    finally:
        try:
            os.unlink(tempname)
        except FileNotFoundError:
            pass

def capture(news_path, holiday_path, state_dir, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise EvidenceError("UTC-aware now required")
    now = now.astimezone(timezone.utc)
    gate = json.loads(Path(holiday_path).read_text(encoding="utf8"))
    if not holiday_gate(gate, now):
        return {"status":"PAUSED_OR_INVALID_GATE","created":0,"existing":0}
    feed = json.loads(Path(news_path).read_text(encoding="utf8"))
    if feed.get("broker_read_only") is not True or feed.get("orders_submitted") != 0:
        raise EvidenceError("news source not data-only")
    if feed.get("source") != "Alpaca GET news, possibly delayed":
        raise EvidenceError("unapproved news source")
    asof = timestamp(feed.get("asof_utc"))
    if asof > now + timedelta(seconds=10) or now - asof > timedelta(seconds=120):
        raise EvidenceError("stale or future feed snapshot")
    articles = feed.get("recent")
    if not isinstance(articles, list) or len(articles) > 1000:
        raise EvidenceError("invalid bounded feed")
    state_dir = Path(state_dir)
    state_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
    marker = state_dir / "activation.json"
    activation = {"schema_version":1, "activated_at_utc":iso(now),
                  "research_only":True, "orders_allowed":False,
                  "content_digest":"activation"}
    write_once(marker, activation)
    activated = timestamp(json.loads(marker.read_text(encoding="utf8"))["activated_at_utc"])
    created = existing = prospective = 0
    for raw in articles:
        src = canonical_article(raw, asof)
        observed = timestamp(src["observed_at_utc"])
        published = timestamp(src["published_at_utc"])
        digest = content_digest(src)
        path = state_dir / observed.astimezone(TZ).date().isoformat() / (hashlib.sha256(src["news_id"].encode()).hexdigest() + ".json")
        # Earlier feed entries are HISTORICAL BASELINE. A new entry qualifies
        # as prospectively sealed only if the evidence was archived promptly.
        future_eligible = (activated <= observed <= now and
                           now - observed <= timedelta(seconds=120) and
                           published <= observed and src["realtime_fresh"])
        record = {"schema_version":1,"content_digest":digest,"article":src,
                  "archived_at_utc":iso(now),"activation_at_utc":iso(activated),
                  "prospective_archive":bool(future_eligible),
                  "source_time_causal":published <= observed,
                  "issuer_verified":False,"guidance_change_verified":False,
                  "trade_authorized":False,"orders_submitted":0,
                  "provenance":"LOCAL_GET_ONLY_NEWS_OBSERVER"}
        if write_once(path, record):
            created += 1
            prospective += bool(future_eligible)
        else:
            existing += 1
    return {"status":"ARCHIVED_RESEARCH_ONLY","created":created,
            "existing":existing,"prospective_new":prospective,
            "sample_count":len(articles)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", default="/var/lib/securityprepper-news-watch-v2/current.json")
    parser.add_argument("--holiday", default="/var/lib/securityprepper-news-watch-v2/holiday_gate.json")
    parser.add_argument("--state", default="/var/lib/securityprepper-v2-news-evidence")
    args = parser.parse_args()
    print(json.dumps(capture(args.feed, args.holiday, args.state), sort_keys=True))

if __name__ == "__main__":
    main()
