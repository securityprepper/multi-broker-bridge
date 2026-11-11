"""Independent GET-only Alpaca news research observer.

Does not classify BUY, touch broker APIs, send alerts or submit orders.
Only persisted timestamped candidate evidence; must not be treated as a trading signal.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://data.alpaca.markets/v1beta1/news"
EARNINGS_SOON = ("will report", "to report", "earnings date", "earnings call", "earnings scheduled")
EARNINGS_REPORTED = ("quarterly results", "reports earnings", "earnings results", "reports q1", "reports q2",
                     "reports q3", "reports q4", "announces financial results", "earnings beat")
POSITIVE = ("raises guidance", "beats estimates", "beats expectations", "fda approves",
            "wins contract", "awarded contract", "increases forecast", "raises outlook")
NEGATIVE = ("cuts guidance", "lowers guidance", "misses estimates", "misses expectations",
            "recall", "fraud", "downgrade", "profit warning", "files for bankruptcy")

def holiday_allows(now: datetime) -> bool:
    # Reuse the host's previously tested boundary-cached trusted validation.
    # A paused/invalid holiday gate MUST block news collection entirely.
    from holiday_gate import current_gate
    path = Path(os.environ.get("V2_NEWS_HOLIDAY_CACHE", ""))
    if not path.is_absolute() or not path.parent.is_dir():
        raise ValueError("trusted holiday cache path required")
    gate, state = current_gate(path, now)
    if gate is None:
        raise ValueError("unverified holiday gate")
    return gate.get("paused") is False

def parse_dt(value: str) -> datetime:
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("news timestamp has no timezone")
    return t.astimezone(timezone.utc)

def categorize(headline: str) -> str:
    h = headline.lower()
    if any(x in h for x in NEGATIVE):
        return "REVIEW_POSSIBLY_NEGATIVE"
    if any(x in h for x in EARNINGS_SOON):
        return "EARNINGS_SCHEDULE_MENTION_UNVERIFIED"
    if any(x in h for x in EARNINGS_REPORTED):
        return "EARNINGS_RELEASE_CANDIDATE_UNVERIFIED"
    if any(x in h for x in POSITIVE):
        return "POSITIVE_NEWS_CANDIDATE_UNVERIFIED"
    return "OTHER_NEWS"

def validate_article(article, observed_at: datetime):
    if not isinstance(article, dict) or not isinstance(article.get("id"), (str, int)):
        return None
    created = parse_dt(article["created_at"])
    # Source create time may be stale/delayed; never silently equate arrival with publication.
    latency = (observed_at - created).total_seconds()
    names = article.get("symbols") or []
    if not isinstance(names, list):
        return None
    headline = str(article.get("headline", ""))[:450]
    return {
        "news_id": str(article["id"])[:80],
        "published_at_utc": created.isoformat(),
        "observed_at_utc": observed_at.astimezone(timezone.utc).isoformat(),
        "latency_seconds": round(latency),
        "realtime_fresh": bool(0 <= latency <= 180),
        "category": categorize(headline),
        "headline": headline,
        "symbols": [str(x)[:20] for x in names[:20]],
        "source": str(article.get("source") or "")[:100],
        "url": str(article.get("url") or "")[:1000],
        "order_permissions": False,
    }

def get_news(now: datetime, credential_dir: Path, opener=urlopen):
    if not credential_dir.is_absolute() or credential_dir.is_symlink():
        raise ValueError("protected credentials directory required")
    kid = (credential_dir / "alpaca_data_key_id").read_text().strip()
    secret = (credential_dir / "alpaca_data_secret").read_text().strip()
    if not kid or not secret:
        raise ValueError("missing authenticated market-data credentials")
    params = {
        "start": (now - timedelta(minutes=12)).astimezone(timezone.utc).isoformat(),
        "end": now.astimezone(timezone.utc).isoformat(),
        "limit": 50, "sort": "asc", "include_content": "false",
    }
    rows = []
    token = None
    for _ in range(10):
        q = dict(params)
        if token:
            q["page_token"] = token
        uri = BASE + "?" + urlencode(q)
        req = Request(uri, headers={
            "APCA-API-KEY-ID": kid,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        }, method="GET")
        with opener(req, timeout=8) as resp:
            if getattr(resp, "status", 200) != 200:
                raise ValueError("news provider returned non-200")
            data = json.loads(resp.read(1_000_001))
        if not isinstance(data, dict) or not isinstance(data.get("news"), list):
            raise ValueError("invalid news response")
        rows.extend(data["news"])
        if len(rows) > 500:
            raise ValueError("news pagination overflow")
        token = data.get("next_page_token")
        if not token:
            return rows
        if not isinstance(token, str) or len(token) > 512:
            raise ValueError("invalid pagination token")
    raise ValueError("news pagination incomplete")

def ingest(rows, now, previous):
    if not isinstance(previous, dict):
        raise ValueError("invalid prior journal")
    prior_ids = previous.get("seen", [])
    if not isinstance(prior_ids, list):
        raise ValueError("invalid prior seen IDs")
    # Preserve chronological insertion order for deterministic bounded de-duplication.
    # list(set(...)) previously evicted arbitrary article IDs at the 4000 cap.
    ordered_ids = list(dict.fromkeys(map(str, prior_ids)))
    seen = set(ordered_ids)
    accepted = []
    for article in rows:
        item = validate_article(article, now)
        if item is None or item["news_id"] in seen:
            continue
        seen.add(item["news_id"])
        ordered_ids.append(item["news_id"])
        accepted.append(item)
    # Bound replay state; full archive/older entries are not assumed exhaustive.
    journal = list(previous.get("recent", [])) + accepted
    if any(not isinstance(x, dict) for x in journal):
        raise ValueError("invalid journal")
    new = {
        "schema_version": 1,
        "asof_utc": now.astimezone(timezone.utc).isoformat(),
        "source": "Alpaca GET news, possibly delayed",
        "broker_read_only": True,
        "orders_submitted": 0,
        "seen": ordered_ids[-4000:],
        "recent": journal[-300:],
    }
    return new, accepted

def write_atomic(state_file: Path, data):
    root = state_file.parent
    if not root.is_absolute() or not root.is_dir() or root.is_symlink() or state_file.is_symlink():
        raise ValueError("private absolute state directory required")
    fd, tmp = tempfile.mkstemp(prefix=".news-watch-", dir=root)
    try:
        with os.fdopen(fd, "w") as h:
            json.dump(data, h, ensure_ascii=False)
            h.write("\n")
            h.flush()
            os.fsync(h.fileno())
        os.chmod(tmp, 0o640)
        os.replace(tmp, state_file)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def run(now=None, news_fetcher=get_news, holiday_checker=holiday_allows):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("aware time required")
    if not holiday_checker(now):
        return {"status": "HOLIDAY_PAUSED_NO_NEWS_POLL", "orders_submitted": 0,
                "broker_order_permissions": False, "market_data_requests": 0}
    creds = Path(os.environ.get("CREDENTIALS_DIRECTORY", ""))
    state = Path(os.environ.get("V2_NEWS_WATCH_STATE", ""))
    if not state.is_absolute() or not state.parent.is_dir():
        raise ValueError("private state path not configured")
    previous = json.loads(state.read_text()) if state.exists() else {}
    fetched = news_fetcher(now, creds)
    # First independently observable local boundary after the completed GET.
    # Poll start is not the time the article became visible to this process.
    received_at = datetime.now(timezone.utc)
    if received_at < now:
        raise ValueError("receipt clock predates poll start")
    updated, fresh = ingest(fetched, received_at, previous)
    updated["poll_started_at_utc"] = now.astimezone(timezone.utc).isoformat()
    updated["poll_completed_at_utc"] = received_at.isoformat()
    updated["first_seen_time_basis"] = "GET_response_completed_not_publication_or_stream_delivery"
    updated["historical_first_seen_backfill_permitted"] = False
    write_atomic(state, updated)
    return {"status": "READ_ONLY_NEWS_WATCH_OK", "new_articles": len(fresh),
            "new_earnings_mentions": sum("EARNINGS_" in x["category"] for x in fresh),
            "new_positive_candidates": sum(x["category"] == "POSITIVE_NEWS_CANDIDATE_UNVERIFIED" for x in fresh),
            "new_fresh_under_180s": sum(x["realtime_fresh"] for x in fresh),
            "orders_submitted": 0, "broker_order_permissions": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", required=True)
    parser.parse_args()
    try:
        print(json.dumps(run(), sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "READ_ONLY_NEWS_WATCH_ERROR", "error_type": type(e).__name__,
                          "orders_submitted": 0}))
        raise SystemExit(2)
