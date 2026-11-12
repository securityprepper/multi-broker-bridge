"""Read-only AST audit of the active PAPER exit policy and sell audit serialization.

No broker access, code imports or writes to production. Parses source text only.
"""
from __future__ import annotations

import ast
import argparse
import json
from pathlib import Path


def _name(call: ast.Call) -> str:
    return call.func.id if isinstance(call.func, ast.Name) else ""


def _target_name(node: ast.AST) -> str:
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
        return ""
    if node.value.id != "recorded" or not isinstance(node.slice, ast.Constant):
        return ""
    return str(node.slice.value)


def audit(trend_source: str, executor_source: str) -> dict:
    trend = ast.parse(trend_source)
    executor = ast.parse(executor_source)
    monitors = [n for n in trend.body if isinstance(n, ast.ClassDef) and n.name == "TrendMonitor"]
    if len(monitors) != 1:
        raise ValueError("TrendMonitor class not uniquely found")
    scans = [n for n in monitors[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "scan"]
    if len(scans) != 1:
        raise ValueError("TrendMonitor.scan not uniquely found")
    scan = scans[0]
    parents = {}
    for parent in ast.walk(scan):
        for field, value in ast.iter_fields(parent):
            values = value if isinstance(value, list) else [value]
            for child in values:
                if isinstance(child, ast.AST):
                    parents[child] = (parent, field)
    two_bar = [n for n in ast.walk(scan) if isinstance(n, ast.Call) and _name(n) == "_two_falling"]
    timing = []
    for call in two_bar:
        cur = call
        early = False
        while cur in parents:
            parent, field = parents[cur]
            if isinstance(parent, ast.If) and field == "body" and "is_early_market(" in ast.unparse(parent.test):
                early = True
            cur = parent
        timing.append("PREMARKET" if early else "OTHER")
    source_scan = ast.unparse(scan)
    has_rth_loss = "change <= LOSS_WATCH" in source_scan
    has_rth_profit = "change >= PROFIT_TARGET" in source_scan
    has_rth_trail = "trail <= -TRAIL_REVERSAL" in source_scan
    if not (has_rth_loss and has_rth_profit and has_rth_trail):
        raise ValueError("RTH protective source clauses missing")

    fields = {}
    for node in ast.walk(executor):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            key = _target_name(target)
            if key in ("exit_signal_reason", "exit_fill_verified"):
                fields[key] = ast.unparse(node.value)
    return {
        "rth_independent_two_falling_present": "OTHER" in timing,
        "premarket_two_falling_calls": timing.count("PREMARKET"),
        "rth_one_percent_loss_clause_present": has_rth_loss,
        "rth_one_percent_profit_clause_present": has_rth_profit,
        "rth_peak_trail_clause_present": has_rth_trail,
        "sell_order_submission_reason_field_present": "exit_signal_reason" in fields,
        "sell_submission_explicitly_not_verified_fill": fields.get("exit_fill_verified") == "False",
        "sell_submission_reason_expression": fields.get("exit_signal_reason", "MISSING"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trend", type=Path, required=True)
    parser.add_argument("--executor", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.trend.read_text(), args.executor.read_text()), sort_keys=True))


if __name__ == "__main__":
    main()
