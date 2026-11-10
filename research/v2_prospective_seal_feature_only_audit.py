"""Read-only as-of validation of prospective V2 sector evidence.

NO broker, quote, database, or notification APIs. Source snapshots remain unmodified.
A feature-only record is not a sealed directional forecast.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json
import sys

ETFS = {
    "semiconductors": "SOXX", "gold_miners": "GDX",
    "energy": "XLE", "financials": "XLF", "industrials": "XLI",
    "healthcare": "XLV", "software": "IGV",
}
DIRECTIONS = {"UP": 1, "DOWN": -1}


def timestamp(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.utcoffset() is None:
        raise ValueError("timezone missing")
    return t


def validate_seal(doc: dict[str, Any]) -> dict[str, Any]:
    seen_at = timestamp(doc["time_of_observation_ET"])
    if not doc.get("research_only") or doc.get("orders_submitted") != 0:
        raise ValueError("not a read-only research seal")
    if doc.get("PAPER_orders_allowed") or doc.get("LIVE_orders_allowed"):
        raise ValueError("broker permissions in research seal")
    if not doc.get("no_current_or_future_outcomes_in_document"):
        raise ValueError("future outcome leakage")
    sectors = doc.get("sectors")
    if not isinstance(sectors, dict) or set(sectors) != set(ETFS):
        raise ValueError("incomplete sectors")
    counts = {"ASOF_FEATURES": 0, "ABSTAIN_MISSING_ASOF_DATA": 0}
    classifications = {"UP": 0, "DOWN": 0, "OTHER": 0}
    observed = {}
    for sector, value in sectors.items():
        status = value.get("status")
        if status not in counts:
            raise ValueError("unexpected sector status")
        counts[status] += 1
        classification = value.get("shadow_classification")
        if classification is not None:
            if classification not in DIRECTIONS:
                classifications["OTHER"] += 1
            else:
                classifications[classification] += 1
        features = value.get("features", {})
        if status == "ABSTAIN_MISSING_ASOF_DATA" and features:
            raise ValueError("abstention contains observations")
        if status == "ASOF_FEATURES" and ETFS[sector] not in features:
            raise ValueError("ETF missing")
        for symbol, feature in features.items():
            end = timestamp(feature["observed_bar_end_ET"])
            if end > seen_at:
                raise ValueError("future or unfinished bar")
            px = float(feature["observed_price"])
            if not 0 < px < 1_000_000:
                raise ValueError("invalid price")
        if ETFS[sector] in features:
            observed[sector] = {
                "etf": ETFS[sector],
                "mark": float(features[ETFS[sector]]["observed_price"]),
                "bar_end": features[ETFS[sector]]["observed_bar_end_ET"],
            }
    return {
        "observation_et": doc["time_of_observation_ET"],
        "slot": doc["forecast_slot_ET"],
        "feature_counts": counts,
        "classifications": classifications,
        "etf_marks": observed,
    }


def observational_move(first: dict, later: dict, sector: str) -> dict:
    a, b = first["etf_marks"].get(sector), later["etf_marks"].get(sector)
    if not a or not b:
        return {"status": "MISSING_MARK_ABSTAIN"}
    if timestamp(b["bar_end"]) <= timestamp(a["bar_end"]):
        raise ValueError("non-future comparison")
    return {
        "status": "DESCRIPTIVE_MOVE_NOT_PREDICTION",
        "start_mark": a["mark"],
        "end_mark": b["mark"],
        "forward_change_pct": round((b["mark"] / a["mark"] - 1) * 100, 5),
    }


def score_frozen_forecast(doc: dict, future: dict, sector: str) -> dict:
    """No posthoc UP/DOWN derivation from an unclassified feature snapshot."""
    first = validate_seal(doc)
    direction = doc["sectors"][sector].get("shadow_classification")
    if direction not in DIRECTIONS:
        return {"status": "NO_PRECOMMITTED_DIRECTION_NOT_SCORABLE"}
    next_mark = future["etf_marks"].get(sector)
    initial = first["etf_marks"].get(sector)
    if not initial or not next_mark:
        return {"status": "NO_FUTURE_MARK_NOT_SCORABLE"}
    if timestamp(next_mark["bar_end"]) <= timestamp(doc["time_of_observation_ET"]):
        raise ValueError("outcome is not after signal")
    pct = (next_mark["mark"] / initial["mark"] - 1) * 100
    aligned = DIRECTIONS[direction] * pct
    return {
        "status": "FLAT_OR_TINY" if abs(pct) < 0.05 else ("HIT" if aligned > 0 else "MISS"),
        "signed_postsignal_pct": round(aligned, 5),
    }


def audit(paths: list[Path]) -> dict:
    if len(paths) < 2:
        raise ValueError("two or more evidence snapshots required")
    docs = [json.loads(p.read_text()) for p in paths]
    validated = [validate_seal(d) for d in docs]
    for a, b in zip(validated, validated[1:]):
        if timestamp(b["observation_et"]) <= timestamp(a["observation_et"]):
            raise ValueError("slot order invalid")
    comparisons = {}
    for sector in ETFS:
        comparisons[sector] = {
            "first_to_last": observational_move(validated[0], validated[-1], sector),
            "second_to_last": observational_move(validated[1], validated[-1], sector)
            if len(validated) >= 3 else {"status": "NOT_AVAILABLE"},
            "forecast_score_first": score_frozen_forecast(docs[0], validated[-1], sector),
        }
    return {
        "research_only": True, "brokers_queried": False,
        "orders_submitted": 0, "not_a_trading_recommendation": True,
        "seals": validated, "sectors": comparisons,
        "caution": "Feature-only seals do not establish forward prediction hit rate; mark changes are descriptive and not executable fills.",
    }


if __name__ == "__main__":
    paths = [Path(s) for s in sys.argv[1:]]
    print(json.dumps(audit(paths), indent=2, sort_keys=True))

