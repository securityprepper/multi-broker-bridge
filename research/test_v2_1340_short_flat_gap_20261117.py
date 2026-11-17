"""Read-only regression for deployed V2 13:40 CT time-exit gap.

Run only on a trusted host with the original installed source trees.
No broker calls, no production changes and no state writes.
"""
from __future__ import annotations

import ast
import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

source = Path("/opt/securityprepper/direction-paper-executor/direction_paper.py")
tree = ast.parse(source.read_text())
function = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "software_risk_exits"
)
assign = next(
    node for node in ast.walk(function)
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "near_cutoff"
            for target in node.targets)
)
condition = compile(ast.Expression(assign.value), str(source), "eval")
ct = ZoneInfo("America/Chicago")
for hour, minute, expected in (
    (13, 39, False), (13, 40, False), (13, 50, False),
    (13, 59, False), (14, 0, True)
):
    local = dt.datetime(2026, 11, 17, hour, minute, tzinfo=ct)
    actual = eval(condition, {"__builtins__": {}}, {"local": local})
    assert actual is expected, (hour, minute, actual, expected)
    print(f"V2_EXIT_CUTOFF {local:%H:%M} = {actual}")

from multi_broker_bridge.paper_time_exit import _positive_whole_qty
from multi_broker_bridge.models import OrderRejected
try:
    _positive_whole_qty({
        "symbol": "AMD", "side": "short", "qty": "-4", "qty_available": "-4"
    })
except OrderRejected:
    print("MBB_1340_BACKSTOP_SHORT_REJECTED")
else:
    raise AssertionError("Unexpected MBB short coverage")

from recommendation_paper_bridge.exit_guard import exclusively_owned, Unsafe
try:
    exclusively_owned(
        "AMD", 4, [{"symbol": "AMD", "side": "short", "qty": "-4"}], [], set()
    )
except Unsafe:
    print("RECOMMENDATION_1340_BACKSTOP_SHORT_REJECTED")
else:
    raise AssertionError("Unexpected recommendation short coverage")

print("NO_BROKER_CONTACTS; RESEARCH_PROOF_OK")
