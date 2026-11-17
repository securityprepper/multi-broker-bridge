#!/usr/bin/env python3
"""Holiday- and cadence-gated Robinhood MCP collector launcher. No broker order actions.

A successful published holiday projection allows collection. Paused/invalid/expired
projections fail closed *before* Node.js or Robinhood OAuth network contact.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

GATE = Path("/var/cache/securityprepper-holiday/task-gate.json")
NODE = Path("/opt/securityprepper/robinhood-mcp-collector/collect.mjs")
CT = ZoneInfo("America/Chicago")
UTC = dt.timezone.utc

def allowed(gate: dict, now: dt.datetime) -> tuple[bool, str, str | None]:
    # Share the validated schema and boundary policy used by the existing holiday scheduler.
    sys.path.insert(0, "/opt/securityprepper/sector-monitor")
    from holiday_gate import validate_fresh
    try:
        verified = validate_fresh(gate, now)
    except (ValueError, KeyError, TypeError, OverflowError):
        return False, "HOLIDAY_UNVERIFIED", None
    return not verified["paused"], ("UNPAUSED" if not verified["paused"] else "HOLIDAY_PAUSED"), verified["next_check_at"]

def scheduled_slot(now: dt.datetime) -> bool:
    # Timer wakes each minute. Both Robinhood account kinds are captured.
    # Off-hours: every minute; regular session: existing 15-minute cadence.
    sys.path.insert(0,"/opt/securityprepper/multi-broker-bridge")
    from multi_broker_bridge.offhours_stop import session
    if session(now) in ("PREMARKET","AFTERHOURS","OVERNIGHT"):
        return True  # One-minute read-only evidence for off-hours stop watch.
    local = now.astimezone(CT)
    minute, hour = local.minute, local.hour
    if (hour == 8 and minute >= 30) or (9 <= hour < 15):
        return minute % 15 == 0
    if 3 <= hour < 8 or (hour == 8 and minute < 30) or 15 <= hour < 19:
        return minute % 30 == 0
    return minute == 0

def main(now: dt.datetime | None = None, gate_path: Path = GATE, execute: bool = True, manual_once: bool = False) -> int:
    now = now or dt.datetime.now(UTC)
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        ok, status, next_check = allowed(gate, now)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        ok, status, next_check = False, "HOLIDAY_UNVERIFIED", None
    out = {"holiday_gate": status, "next_check_at": next_check, "collector_started": False}
    if not ok:
        print(json.dumps(out, sort_keys=True))
        return 0 if status == "HOLIDAY_PAUSED" else 2
    if not manual_once and not scheduled_slot(now):
        out["cadence"] = "NOT_DUE"
        print(json.dumps(out, sort_keys=True))
        return 0
    if not execute:
        out["cadence"] = "DUE_DRY_RUN"
        print(json.dumps(out, sort_keys=True))
        return 0
    out["collector_started"] = True
    print(json.dumps(out, sort_keys=True), flush=True)
    cmd = ["/usr/bin/node", str(NODE)]
    result = subprocess.run(cmd, env=os.environ.copy(), timeout=240, check=False)
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main(manual_once=(sys.argv[1:]==["--manual-once"])))