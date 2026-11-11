"""Frozen observational UP/DOWN/ABSTAIN shadow rules for seven sectors.
These are *unvalidated forecast baselines*, NOT orders, alerts or paper strategies.
Never fit/tune using outcomes observed after the signal; freeze for >=30 new sessions.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math

POLICY = {
    "id": "v2-7sector-forward-baselines-20261111-r2",
    "effective_first_session_et": "2026-11-12",
    "scope": "research_shadow_only",
    "benchmark": {
        "description": "signed completed ETF movement since today's RTH open, before any future return",
        "min_absolute_etf_pct": 0.05,
    },
    "peer_confirmed": {
        "description": "independent precommitted ETF+own-sector peers confirmation",
        "min_absolute_etf_pct": 0.10,
        "min_peer_move_same_direction_pct": 0.05,
        "minimum_peers_same_direction": 2,
    },
    "outcome": {
        "from": "latest completed five-minute ETF close as of signal",
        "60m": "first completed SIP 5-minute bar ending no earlier than actual forecast issuance plus 60 minutes",
        "flat": "14:40 ET completed five-minute close (13:40 America/Chicago)",
        "tiny_return_below_absolute_pct": 0.05,
        "illustrative_round_trip_friction_bp": [30, 60],
    },
    "not_trade_alert_or_order": True,
}
POLICY_ID = POLICY["id"]
POLICY_SHA256 = sha256(
    json.dumps(POLICY, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()

def _direction(pct, threshold):
    if not math.isfinite(pct):
        return "ABSTAIN"
    if pct >= threshold:
        return "UP"
    if pct <= -threshold:
        return "DOWN"
    return "ABSTAIN"

def frozen_forecast(sector, etf, peers, features, prior, observation):
    """Apply one immutable rule at each completed-bar decision.
    Missing inputs do not become bullish, bearish, zeros, or broker preflights.
    """
    if observation.tzinfo is None:
        raise ValueError("timezone-aware observation required")
    from zoneinfo import ZoneInfo
    not_effective = observation.astimezone(ZoneInfo("America/New_York")).date().isoformat() < POLICY["effective_first_session_et"]
    result = {
        "policy_id": POLICY_ID,
        "policy_sha256": POLICY_SHA256,
        "sector": sector,
        "etf": etf,
        "benchmark_side": "ABSTAIN",
        "peer_confirmed_side": "ABSTAIN",
        "reason": "ABSTAIN_MISSING_ASOF",
        "signal_mark": None,
        "signal_source_bar_end_ET": None,
        "signal_recorded_at_ET": observation.isoformat(),
        "all_seven_sectors_covered": True,
        "research_only": True,
        "alerts_authorized": False,
        "orders_authorized": False,
    }
    if not_effective:
        result["reason"] = "ABSTAIN_POLICY_NOT_EFFECTIVE"
        return result
    if not isinstance(features, dict) or etf not in features:
        return result
    expected=(etf, *peers)
    if any(s not in features or not isinstance(features[s], dict) for s in expected):
        return result
    if not isinstance(prior, dict) or any(
        not isinstance(prior.get(s), dict) or
        len(prior[s].get("five_previous_dates", [])) != 5 or
        len(prior[s].get("five_previous_closes", [])) != 5
        for s in expected
    ):
        result["reason"] = "ABSTAIN_NO_PRIOR_FIVE"
        return result
    try:
        movement=float(features[etf]["from_0930_open_pct"])
        mark=float(features[etf]["observed_price"])
        if not math.isfinite(movement) or not math.isfinite(mark) or mark<=0:
            return result
        completed=datetime.fromisoformat(features[etf]["observed_bar_end_ET"])
        if completed.tzinfo is None or completed>observation:
            result["reason"]="ABSTAIN_BAR_NOT_AVAILABLE"
            return result
        peer_moves=[float(features[s]["from_0930_open_pct"]) for s in peers]
        if len(peer_moves)!=len(peers) or not all(math.isfinite(p) for p in peer_moves):
            return result
        for s in peers:
            bar_end=datetime.fromisoformat(features[s]["observed_bar_end_ET"])
            if bar_end.tzinfo is None or bar_end>observation:
                result["reason"]="ABSTAIN_PEER_BAR_NOT_AVAILABLE"
                return result
    except (TypeError, ValueError, KeyError, OverflowError):
        return result
    base=_direction(movement,POLICY["benchmark"]["min_absolute_etf_pct"])
    confirmed="ABSTAIN"
    agreeing=0
    if base!="ABSTAIN" and abs(movement)>=POLICY["peer_confirmed"]["min_absolute_etf_pct"]:
        margin=POLICY["peer_confirmed"]["min_peer_move_same_direction_pct"]
        agreeing=sum(
            (p>=margin if base=="UP" else p<=-margin) for p in peer_moves
        )
        if agreeing>=POLICY["peer_confirmed"]["minimum_peers_same_direction"]:
            confirmed=base
    result.update({
        "benchmark_side":base,
        "peer_confirmed_side":confirmed,
        "reason":("ETF_AND_PEER_CONSENSUS" if confirmed!="ABSTAIN"
                  else "ETF_ONLY_NO_PEER_CONFIRM" if base!="ABSTAIN"
                  else "ABSTAIN_TINY_ETF_MOVE"),
        "signal_mark":mark,
        "signal_source_bar_end_ET":completed.isoformat(),
        "observed_etf_from_open_pct":movement,
        "confirming_peers":agreeing,
        "available_peer_count":len(peer_moves),
        "prior_five_end": prior[etf]["five_previous_dates"][-1],
    })
    return result