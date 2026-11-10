"""Pure offline V2 forward-direction evidence gate. NO broker API or orders."""
from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite, sqrt
from statistics import NormalDist

SECTORS = ("semiconductors", "gold_miners", "energy", "financials", "industrials", "healthcare", "software")
DIRECTIONS = ("UP", "DOWN", "ABSTAIN")

def instant(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include UTC offset")
    return dt.astimezone(timezone.utc)

def wilson_lower(hits, total, hypotheses=42, alpha=0.05):
    """Two-sided Bonferroni-adjusted Wilson lower confidence bound."""
    if not 0 <= hits <= total or not isinstance(total, int) or total < 0:
        raise ValueError("invalid counts")
    if not isinstance(hypotheses, int) or hypotheses < 1 or not 0 < alpha < 1:
        raise ValueError("invalid statistical controls")
    if not total:
        return 0.0
    z = NormalDist().inv_cdf(1.0 - alpha / (2.0 * hypotheses))
    p = hits / total
    return (p + z*z/(2*total) - z*sqrt(p*(1-p)/total + z*z/(4*total*total))) / (1+z*z/total)

def score(rows, eligible_dates, horizons=("60m",), hypotheses=42, min_days=30):
    """Count one earliest SEALED forecast per sector/session/horizon, no hindsight pick.

    Signal availability/record seal and independently obtained outcome must be ordered.
    A 'sealed' flag here is asserted evidence, NOT proof of cryptographic authenticity.
    Every absent sector/day/horizon is an abstention, rather than dropped from coverage.
    Direction uses signal MARK, not preceding close/open; tiny moves are not hits.
    Real-fill P&L is never inferred from marks or asserted quote completeness.
    """
    dates = sorted(set(eligible_dates))
    if not dates or any(not isinstance(d,str) or len(d)!=10 or datetime.strptime(d,"%Y-%m-%d").date().isoformat()!=d for d in dates):
        raise ValueError("eligible calendar days required")
    if any(h not in ("15m","60m","1330","close","next_open") for h in horizons):
        raise ValueError("unsupported horizon")
    if min_days < 1:
        raise ValueError("invalid minimum")
    groups = defaultdict(list)
    ids = set()
    for row in rows:
        if row.get("mode") != "RESEARCH_ONLY" or row.get("sector") not in SECTORS:
            raise ValueError("unexpected mode or sector")
        if row.get("direction") not in DIRECTIONS or row.get("horizon") not in horizons:
            raise ValueError("unexpected direction or horizon")
        day = row.get("session_date")
        if day not in dates:
            raise ValueError("session outside approved calendar")
        identifier = row.get("signal_id")
        if not identifier or identifier in ids:
            raise ValueError("missing or duplicate immutable signal ID")
        ids.add(identifier)
        started = instant(row.get("source_bar_end_utc"))
        available = instant(row.get("signal_available_utc"))
        sealed = instant(row.get("sealed_at_utc"))
        if not started <= available <= sealed:
            raise ValueError("unfinished bar or impossible sealing time")
        if row["direction"] != "ABSTAIN":
            observed = float(row.get("signal_mark", 0))
            future = float(row.get("future_mark", 0))
            if not all(isfinite(v) and v > 0 for v in (observed,future)):
                raise ValueError("unusable price marks")
            when = instant(row.get("future_at_utc"))
            retrieved = instant(row.get("outcome_retrieved_utc"))
            if not sealed < when <= retrieved:
                raise ValueError("future leakage / premature outcome")
        groups[(row["sector"],day,row["horizon"])].append((sealed,row))
    result = {}
    for sector in SECTORS:
        for horizon in horizons:
            selected = []
            for day in dates:
                candidates = sorted(groups[(sector,day,horizon)],key=lambda sr:sr[0])
                if not candidates:
                    selected.append((day, None))
                else:
                    selected.append((day, candidates[0][1]))
            r = {"eligible_days":len(dates),"predicted_days":0,"abstain_days":0,
                 "up":{"hits":0,"misses":0,"tiny":0,"days":0,"net_positive_attested":0},
                 "down":{"hits":0,"misses":0,"tiny":0,"days":0,"net_positive_attested":0},
                 "skipped_later_within_day":sum(max(0,len(groups[(sector,d,horizon)])-1) for d in dates)}
            evidence_all = True
            for day,row in selected:
                if row is None or row["direction"] == "ABSTAIN":
                    r["abstain_days"] += 1
                    continue
                r["predicted_days"] += 1
                direction = row["direction"].lower()
                bucket = r[direction]
                bucket["days"] += 1
                signed = (float(row["future_mark"])/float(row["signal_mark"])-1)*100
                if direction == "down":
                    signed = -signed
                if abs(signed) < 0.05:  # 5bp tiny-move bucket; NEVER count as a hit
                    bucket["tiny"] += 1
                elif signed > 0:
                    bucket["hits"] += 1
                else:
                    bucket["misses"] += 1
                verified = row.get("independent_seal_verified") is True and row.get("quote_cost_verified") is True
                evidence_all = evidence_all and verified
                if verified:
                    friction_bp = float(row.get("friction_bp", -1))
                    if not isfinite(friction_bp) or friction_bp < 0:
                        raise ValueError("invalid broker-cost evidence")
                    if signed > friction_bp/100:
                        bucket["net_positive_attested"] += 1
            r["coverage"] = r["predicted_days"] / len(dates)
            r["independent_evidence_all"] = evidence_all and r["predicted_days"]>0
            for direction in ("up","down"):
                b = r[direction]
                b["precision"] = b["hits"]/b["days"] if b["days"] else None
                b["familywise_wilson_lower"] = wilson_lower(b["hits"], b["days"], hypotheses)
                b["statistically_supported_80"] = b["days"] >= min_days and b["familywise_wilson_lower"] >= .80
            r["paper_review_eligible"] = False # Pure research NEVER grants release/GO or operational eligibility
            r["reason"] = "research only; requires independent prospective seal/quote audit and separate PAPER release review"
            result[f"{sector}:{horizon}"]=r
    return result
