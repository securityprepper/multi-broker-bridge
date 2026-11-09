"""V2 RESEARCH ONLY: precision-first PAPER candidate evaluation.

No broker connectivity or order functions. Do not import into V1.
Thresholds are hypotheses; only independent out-of-sample outcomes can qualify a setup.
"""
from dataclasses import dataclass
from math import sqrt
from typing import Sequence

@dataclass(frozen=True)
class FinishedTrade:
    # Outcomes are measured AFTER signals and must never leak into decision-time features.
    signal_day: str
    net_return_pct: float
    signal_time: str
    sector: str

@dataclass(frozen=True)
class PrecisionResult:
    count: int
    profitable: int
    precision: float
    wilson_95_lower: float
    mean_net_pct: float
    independent_days: int
    approved_for_further_paper_testing: bool

def wilson_lower(successes: int, n: int, z: float = 1.96) -> float:
    if not (0 <= successes <= n):
        raise ValueError("invalid sample")
    if n == 0:
        return 0.0
    p = successes/n
    z2 = z*z
    return (p+z2/(2*n)-z*sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n)

def evaluate(trades: Sequence[FinishedTrade], min_days: int = 30,
             desired_precision: float = .80, require_lower_bound: float = .70) -> PrecisionResult:
    if not 0 < desired_precision <= 1 or not 0 < require_lower_bound <= 1:
        raise ValueError("invalid target")
    if min_days < 2:
        raise ValueError("minimum independent day count too low")
    if any(not (-100 <= t.net_return_pct <= 10000) for t in trades):
        raise ValueError("invalid return")
    n = len(trades)
    wins = sum(t.net_return_pct > 0 for t in trades)
    days = len({t.signal_day for t in trades})
    precision = wins/n if n else 0.0
    low = wilson_lower(wins,n)
    mean = sum(t.net_return_pct for t in trades)/n if n else 0.0
    # Research eligibility ONLY. No broker orders are ever emitted.
    gate = (days >= min_days and precision >= desired_precision and
            low >= require_lower_bound and mean > 0)
    return PrecisionResult(n,wins,precision,low,mean,days,gate)

def emergency_threshold_pct(atr_pct: float, fixed_floor_pct: float,
                            atr_multiple: float = 1.25) -> float:
    """Research candidate: volatility-scaled emergency drop level."""
    if not (0 < atr_pct <= 100 and 0 < fixed_floor_pct <= 25 and 0 < atr_multiple <= 10):
        raise ValueError("invalid threshold inputs")
    return max(fixed_floor_pct,atr_pct*atr_multiple)

def leading_signal_eligible(lead_observed_at: str, miner_decision_at: str,
                            lead_session: str, miner_session: str,
                            fresh: bool, independently_validated: bool) -> bool:
    """Gold/miner lead-lag must use timestamped available/tradeable observations."""
    return bool(fresh and independently_validated and lead_session == miner_session
                and lead_observed_at < miner_decision_at)
