"""Static, read-only MBB PAPER BUY gate audit. No network or broker calls."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path

NEWS_TERMS = ("negative_news", "news_clear_asof", "news_unknown",
              "issuer_news", "adverse_news", "news_veto", "issuer_clearance")

def audit_source(source: str) -> dict:
    tree = ast.parse(source)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    run = funcs.get("run")
    transport = funcs.get("paper_api")
    if not run or not transport:
        return {"status": "UNKNOWN_SOURCE", "direct_buy_order_post": False,
                "explicit_news_check_observed": False}
    posts = []
    for node in ast.walk(run):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "paper_api" and len(node.args) >= 2
                and all(isinstance(a, ast.Constant) for a in node.args[:2])
                and node.args[0].value == "POST"
                and node.args[1].value == "/v2/orders"):
            posts.append(node.lineno)
    tokens = set()
    for node in ast.walk(run):
        if isinstance(node, ast.Name):
            tokens.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            tokens.add(node.attr.lower())
    explicit = any(any(term in token for term in NEWS_TERMS) for token in tokens)
    paper_strings = [node.value for node in ast.walk(transport)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    direct_http = any("paper-api.alpaca.markets" in s for s in paper_strings)
    if posts and direct_http and not explicit:
        status = "MISSING_EXPLICIT_PREBUY_NEWS_CLEARANCE_IN_DIRECT_ORDER_PATH"
    elif posts:
        status = "REQUIRES_MANUAL_CODE_AND_ASOF_EVIDENCE_REVIEW"
    else:
        status = "NO_DIRECT_ORDER_POST_FOUND"
    return {"status": status, "direct_buy_order_post": bool(posts),
            "post_line_numbers": posts,
            "direct_paper_https_transport": direct_http,
            "explicit_news_check_observed": explicit,
            "sha256": hashlib.sha256(source.encode()).hexdigest()}

def audit_journal(lines) -> dict:
    scans = 0
    accepted_buy_responses = 0
    responses_with_news_proof = 0
    for line in lines:
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(obj, dict) or obj.get("status") != "SCAN_COMPLETE":
            continue
        scans += 1
        for order in obj.get("orders", []):
            if not isinstance(order, dict) or order.get("side") != "buy":
                continue
            if not order.get("broker_order_id"):
                continue
            accepted_buy_responses += 1
            if order.get("news_clearance") == "NEWS_CLEAR_ASOF" and order.get("news_evidence_observed_at"):
                responses_with_news_proof += 1
    return {"scans": scans, "buy_order_responses": accepted_buy_responses,
            "buy_responses_with_documented_news_clearance": responses_with_news_proof,
            "warning": "Order responses are NOT broker fills. Missing journal fields do not independently prove no prior check."}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--journal", type=Path)
    a = p.parse_args()
    result = {"source": audit_source(a.source.read_text(encoding="utf-8"))}
    if a.journal:
        with a.journal.open(encoding="utf-8") as f:
            result["journal"] = audit_journal(f)
    print(json.dumps(result, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()

[executed on device: www3.securityprepper.com (1016f4a4-5f2e-452e-8c88-0e4b9430d76e)]