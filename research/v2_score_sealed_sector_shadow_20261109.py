"""Research-only scorer for pre-outcome V2 sealed 5-minute sector snapshots.

Inputs are an immutable pre-outcome JSON snapshot and an *independently fetched*
subsequent 5-minute trade-bar series. Never calls a broker or emits orders.
A 5-minute price is NOT an executable NBBO quotation or a validated short.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc
COST_BP = 30.0  # research stress only; not a measured broker cost
SECTOR_ETFS = {"semiconductors":"SOXX", "gold_miners":"GDX", "energy":"XLE",
               "financials":"XLF", "industrials":"XLI", "healthcare":"XLV",
               "software":"IGV"}


def timestamp(text):
    val = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if val.tzinfo is None:
        raise ValueError("naive timestamp")
    return val.astimezone(UTC)


def price(value):
    x = float(value)
    if not isfinite(x) or x <= 0:
        raise ValueError("invalid nonfinite/nonpositive price")
    return x


def index_completed_bars(rows, day, now):
    """Exact completed 5m bars only, never use uncompleted/future observations."""
    ret = {}
    for b in rows:
        start = timestamp(b["t"])
        end = start + timedelta(minutes=5)
        if start.astimezone(ET).date() != day or end > now - timedelta(seconds=15):
            continue
        if start.second or start.microsecond or start.minute % 5:
            raise ValueError("off-grid timestamp")
        op, hi, lo, cl = (price(b[k]) for k in ("o", "h", "l", "c"))
        if lo > min(op, cl) or hi < max(op, cl) or lo > hi:
            raise ValueError("inconsistent OHLC")
        vals = (op, hi, lo, cl)
        if start in ret and ret[start] != vals:
            raise ValueError("conflicting bar duplicate")
        ret[start] = vals
    return ret


def at_or_after_end(bars, horizon):
    # Strict fixed-horizon rule: the first fully completed 5m bar at/after the
    # requested clock time, not an earlier price or a nearest-price backfill.
    eligible = sorted((st, b) for st, b in bars.items()
                      if st + timedelta(minutes=5) >= horizon)
    for st, b in eligible:
        # A missing bar at the exact 5-minute interval means an abstention;
        # do not substitute an arbitrarily later observation.
        if st + timedelta(minutes=5) - horizon < timedelta(minutes=5):
            return st + timedelta(minutes=5), b[3]
        break
    return None


def entry_bar(bars, earliest):
    # This is the first 5m OPEN at or after the snapshot's stated earliest
    # entry. The historical next-bar OPEN may be earlier; never use it here.
    eligible = [(st, b[0]) for st, b in bars.items() if st >= earliest]
    return min(eligible, default=None, key=lambda row: row[0])


def score_snapshot(snapshot, outcomes_by_symbol, evaluated_at, cost_bp=COST_BP):
    """Score true post-signal movement separately from conservative entry P&L.

    Missing quotes or a not-yet-completed horizon yield null, never a hit.
    Returns research-only facts; does not modify original snapshot.
    """
    now = timestamp(evaluated_at) if isinstance(evaluated_at, str) else evaluated_at.astimezone(UTC)
    observed = timestamp(snapshot["time_of_observation_utc"])
    earliest = timestamp(snapshot["earliest_later_entry_at_ET"])
    slot = snapshot["forecast_slot_ET"]
    if earliest < observed or now < observed or cost_bp < 0:
        raise ValueError("invalid clock order or research friction")
    day = observed.astimezone(ET).date()
    if observed.astimezone(ET).strftime("%H:%M") != slot:
        # Actual record has :25 seconds, so equality at HH:MM is expected.
        raise ValueError("forecast slot mismatch")
    hard_flat_local = observed.astimezone(ET).replace(hour=14, minute=40, second=0, microsecond=0)
    horizons = {"forward_15m": observed + timedelta(minutes=15),
                "forward_60m": observed + timedelta(minutes=60),
                "latest_flat_1340_CT": hard_flat_local.astimezone(UTC)}
    out = {"research_only": True, "orders_submitted": 0,
           "source_snapshot_observed_utc": observed.isoformat(),
           "scored_at_utc": now.isoformat(),
           "historical_execution_quotes_verified": False,
           "short_borrow_verified": False,
           "roundtrip_friction_assumed_bp": cost_bp,
           "sectors": {}}
    for sector, row in snapshot["sectors"].items():
        features = row.get("features", {})
        if row.get("status") != "ASOF_FEATURES" or not features:
            out["sectors"][sector] = {"status": "ABSTAIN_ASOF"}
            continue
        etf = SECTOR_ETFS.get(sector)
        # Snapshot JSON is sorted alphabetically: NEVER infer the sector ETF
        # from the first feature key (AMD would precede SOXX).
        if not etf or etf not in features or etf not in outcomes_by_symbol:
            out["sectors"][sector] = {"status": "ABSTAIN_NO_OUTCOME_BARS"}
            continue
        baseline = price(features[etf]["observed_price"])
        bar_end = timestamp(features[etf]["observed_bar_end_ET"])
        if bar_end > observed or observed - bar_end > timedelta(minutes=6):
            out["sectors"][sector] = {"status": "ABSTAIN_STALE_OR_FUTURE_SIGNAL_BAR"}
            continue
        bars = index_completed_bars(outcomes_by_symbol[etf], day, now)
        direction = "DOWN" if row.get("shadow_classification") == "EXPLORATORY_BEARISH_SEMI_WATCH_ONLY" else None
        side = -1 if direction == "DOWN" else 1
        ev = {"status": "SCORED_DESCRIPTIVE" if direction is None else "SCORED_SHADOW",
              "signal_baseline_price": baseline, "direction_forecast": direction,
              "forward": {}, "trade_mark_proxy": None}
        for name, when in horizons.items():
            if now < when + timedelta(seconds=15):
                ev["forward"][name] = {"status": "NOT_YET_OBSERVABLE"}
                continue
            hit = at_or_after_end(bars, when)
            if hit is None:
                ev["forward"][name] = {"status": "MISSING_BAR"}
                continue
            end, mark = hit
            raw_pct = 100.0 * (mark / baseline - 1.0)
            signed_pct = side * raw_pct if direction else None
            ev["forward"][name] = {"status": "OBSERVED_TRADE_MARK",
                "end_utc": end.isoformat(), "mark_price": mark,
                "raw_after_signal_pct": round(raw_pct, 6),
                "direction_hit": None if direction is None else signed_pct > 0.05,
                "tiny_or_flat": abs(raw_pct) <= 0.05,
                "signed_after_signal_pct": None if signed_pct is None else round(signed_pct, 6)}
        entry = entry_bar(bars, earliest)
        flat = ev["forward"]["latest_flat_1340_CT"]
        if direction is not None and entry and flat["status"] == "OBSERVED_TRADE_MARK":
            entry_start, entry_px = entry
            latest_entry = observed.astimezone(ET).replace(hour=14, minute=15, second=0, microsecond=0)
            if entry_start <= latest_entry.astimezone(UTC) and entry_start < timestamp(flat["end_utc"]):
                # A flat 30bp deduction from trade marks is *illustrative*,
                # NOT a fill/commission/borrow proof.
                net = side * 100 * (flat["mark_price"] / entry_px - 1) - cost_bp / 100
                intratrade = [(t, b) for t, b in bars.items()
                              if entry_start <= t and t + timedelta(minutes=5) <= timestamp(flat["end_utc"])]
                # Outcome-only extrema; never inputs to the preceding prediction.
                if side == 1:
                    worst = min((100 * (b[2] / entry_px - 1) for _, b in intratrade), default=None)
                    best = max((100 * (b[1] / entry_px - 1) for _, b in intratrade), default=None)
                else:
                    worst = min((100 * (1 - b[1] / entry_px) for _, b in intratrade), default=None)
                    best = max((100 * (1 - b[2] / entry_px) for _, b in intratrade), default=None)
                trade = {"entry_bar_start_utc": entry_start.isoformat(),
                    "entry_open_mark": entry_px, "flat_close_mark": flat["mark_price"],
                    "estimated_after_assumed_cost_pct": round(net, 6),
                    "after_cost_win": net > 0, "real_fill": False,
                    "worst_intratrade_excursion_pct": None if worst is None else round(worst, 6),
                    "best_intratrade_excursion_pct": None if best is None else round(best, 6)}
                for horizon in ("forward_15m", "forward_60m"):
                    future = ev["forward"][horizon]
                    if future["status"] != "OBSERVED_TRADE_MARK":
                        continue
                    if timestamp(future["end_utc"]) <= entry_start:
                        continue
                    net_future = side * 100 * (future["mark_price"] / entry_px - 1) - cost_bp / 100
                    trade[horizon + "_after_cost_pct"] = round(net_future, 6)
                    trade[horizon + "_after_cost_win"] = net_future > 0
                ev["trade_mark_proxy"] = trade
        out["sectors"][sector] = ev
    return out
