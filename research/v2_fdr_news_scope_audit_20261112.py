"""Read-only, fail-closed static coverage audit of the legacy FDR news veto.

Never imports the runner, opens a network connection, reads credentials, or submits orders.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path

def _binding(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    return None

def _symbols(node):
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        items = node.elts
    elif isinstance(node, ast.Dict):
        items = node.keys
    else:
        raise ValueError("symbol set not a literal")
    if not items or not all(isinstance(x, ast.Constant) and isinstance(x.value, str) for x in items):
        raise ValueError("unverifiable symbol set")
    return sorted(set(x.value for x in items))

def _screen_minimum(tree):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "screen":
            args = node.args.args
            defaults = {a.arg: d for a, d in zip(args[-len(node.args.defaults):], node.args.defaults)} if node.args.defaults else {}
            val = defaults.get("minimum_distinct")
            if isinstance(val, ast.Constant) and type(val.value) is int:
                return val.value
    return None

def audit_sources(runner: str, catalysts: str):
    runner_tree = ast.parse(runner)
    catalyst_tree = ast.parse(catalysts)
    basket = _symbols(_binding(runner_tree, "BASKET"))
    anchors = _symbols(_binding(catalyst_tree, "ANCHORS"))
    news_fn = next((n for n in runner_tree.body if isinstance(n, ast.FunctionDef) and n.name == "_fetch_causal_news"), None)
    anchor_query = bool(news_fn and any(isinstance(n, ast.Name) and n.id == "ANCHORS" for n in ast.walk(news_fn)))
    minimum = _screen_minimum(catalyst_tree)
    missing = sorted(set(basket) - set(anchors))
    first_seen = "first_observed_at" in runner or "first_observed_at" in catalysts
    clear_proof = "NEWS_CLEAR_ASOF" in runner
    blocked = bool(missing or minimum is None or minimum > 1 or not anchor_query or not first_seen or not clear_proof)
    return {
        "basket_symbols": basket, "veto_anchor_symbols": anchors,
        "uncovered_basket_symbols": missing,
        "news_query_uses_anchor_set": anchor_query,
        "distinct_adverse_headline_minimum": minimum,
        "first_observed_at_field_present": first_seen,
        "NEWS_CLEAR_ASOF_gate_present": clear_proof,
        "paper_reactivation_research_decision": "NO_GO" if blocked else "STATIC_CHECKS_ONLY_REQUIRES_RUNTIME_VALIDATION",
        "note": "Source-level scope audit, not evidence of real adverse news, real fills, or active orders."
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runner", type=Path)
    ap.add_argument("catalysts", type=Path)
    args = ap.parse_args()
    print(json.dumps(audit_sources(args.runner.read_text(), args.catalysts.read_text()), sort_keys=True))

if __name__ == "__main__":
    main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]