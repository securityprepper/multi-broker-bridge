"""Research-only V2 recorder's read-only, fail-closed root holiday projection.

Never edit the authoritative holiday cache or any broker execution control.
Unlike the historical shadow copy, this projection has a short validity TTL.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import stat
from pathlib import Path
from zoneinfo import ZoneInfo

CT = ZoneInfo("America/Chicago")
UTC = dt.timezone.utc
AUTHORITATIVE_GATE = Path("/var/cache/securityprepper-holiday/task-gate.json")


def timestamp(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("holiday timestamp missing")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("holiday timestamp lacks timezone")
    return parsed.astimezone(UTC)


def verified_gate(path: Path, now: dt.datetime) -> dict:
    """Read a short-lived, root-protected file without following a symlink.

    Missing, stale, paused, untrusted, or incomplete data cannot authorize
    the GET-only market-data recorder. The root publisher owns all refreshing.
    """
    if now.tzinfo is None:
        raise ValueError("naive holiday decision time")
    now = now.astimezone(UTC)
    if not path.is_absolute() or path.parent.is_symlink():
        raise ValueError("untrusted holiday path")
    parent = path.parent.stat()
    if parent.st_uid != 0 or parent.st_mode & 0o022:
        raise ValueError("holiday parent not root-protected")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_mode & 0o022 or info.st_nlink != 1
            or info.st_size > 16384):
            raise ValueError("untrusted holiday projection")
        with os.fdopen(fd, "rb", closefd=False) as reader:
            data = json.loads(reader.read(16385))
    finally:
        os.close(fd)
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
        or data["schema_version"] != 1 or data.get("status_valid") is not True
        or data.get("timezone") != "America/Chicago"
        or data.get("calendar_coverage_ok") is not True
        or type(data.get("paused")) is not bool):
        raise ValueError("unverified holiday status")
    revision = data.get("calendar_revision")
    if not isinstance(revision, str) or not revision.isdigit() or int(revision) < 2:
        raise ValueError("unverified holiday revision")
    if dt.date.fromisoformat(data["calendar_coverage_through"]) < now.astimezone(CT).date():
        raise ValueError("holiday calendar coverage expired")
    published = timestamp(data["published_at"])
    valid_until = timestamp(data["valid_until"])
    boundary = timestamp(data["next_check_at"])
    if (not published <= now < valid_until or not now < boundary
        or now - published > dt.timedelta(seconds=150)
        or valid_until - published > dt.timedelta(seconds=150)
        or valid_until <= published):
        raise ValueError("holiday projection stale or outside boundary")
    return data


def unpaused(now: dt.datetime, path: Path = AUTHORITATIVE_GATE) -> bool:
    return verified_gate(path, now)["paused"] is False
