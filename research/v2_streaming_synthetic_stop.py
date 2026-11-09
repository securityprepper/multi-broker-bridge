"""V2 synthetic-stop research ONLY. Pure calculation; no broker/network/order code."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal as D, ROUND_DOWN

@dataclass(frozen=True)
class Quote:
    at: datetime
    bid: D
    ask: D
    bid_size: int
    ask_size: int

@dataclass(frozen=True)
class Intent:
    symbol: str
    qty: D
    limit_price: D
    triggered_at: datetime
    total_decline_pct: D
    recent_decline_pct_points: D
    reason: str = "RESEARCH_ONLY_NOT_AN_ORDER"

@dataclass(frozen=True)
class Controls:
    max_quote_age: timedelta = timedelta(seconds=2)
    history_tolerance: timedelta = timedelta(seconds=5)
    max_spread_pct: D = D("0.60")
    limit_slippage_pct: D = D("0.15")
    max_gap_beyond_trigger_pct: D = D("5.0")
    total_decline_threshold_pct: D = D("2.5")
    recent_decline_threshold_pct_points: D = D("1.0")

class SyntheticStop:
    """One outstanding intent at most; only reconciled broker outcomes may re-arm.
    Caller supplies verified LONG holdings, quote history and session permissions.
    A marketable limit can remain UNFILLED: no fill or price guarantee is implied.
    """
    def __init__(self, symbol: str, prev_close: D, controls: Controls = Controls()):
        if not symbol.isascii() or not symbol.isupper() or not symbol.isalnum() or len(symbol) > 10:
            raise ValueError("invalid symbol")
        if not prev_close.is_finite() or prev_close <= 0:
            raise ValueError("invalid previous close")
        self.symbol, self.prev_close, self.controls = symbol, prev_close, controls
        self.order_pending = False
        self.locked_uncertain = False
        self.last_event_at = None

    def propose(self, *, now: datetime, quote: Quote, quote_15m_ago: Quote,
                available_long_qty: D, verified_position: bool,
                permitted_session: bool, known_no_open_sell: bool):
        if now.tzinfo is None or quote.at.tzinfo is None or quote_15m_ago.at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.last_event_at is not None and now <= self.last_event_at:
            return None
        self.last_event_at = now
        c = self.controls
        if self.order_pending or self.locked_uncertain:
            return None
        if not (verified_position and known_no_open_sell and permitted_session):
            return None
        if not (available_long_qty.is_finite() and available_long_qty > 0):
            return None
        if not (timedelta(0) <= now - quote.at <= c.max_quote_age):
            return None
        if abs((quote.at - quote_15m_ago.at) - timedelta(minutes=15)) > c.history_tolerance:
            return None
        if not (quote_15m_ago.at < quote.at <= now):
            return None
        if quote.bid_size <= 0 or quote.ask_size <= 0:
            return None
        prices = (quote.bid, quote.ask, quote_15m_ago.bid, quote_15m_ago.ask)
        if not all(x.is_finite() and x > 0 for x in prices):
            return None
        if quote.ask < quote.bid or quote_15m_ago.ask < quote_15m_ago.bid:
            return None
        spread_pct = (quote.ask - quote.bid) / quote.bid * 100
        if spread_pct > c.max_spread_pct:
            return None
        # Both thresholds are expressed against the SAME previous close:
        # recent 1 percentage point is INCLUDED in the total 2.5%.
        total = (self.prev_close - quote.bid) / self.prev_close * 100
        recent = (quote_15m_ago.bid - quote.bid) / self.prev_close * 100
        if total < c.total_decline_threshold_pct or recent < c.recent_decline_threshold_pct_points:
            return None
        if total > c.max_gap_beyond_trigger_pct:
            return None
        limit = (quote.bid * (1 - c.limit_slippage_pct / 100)).quantize(D("0.01"), rounding=ROUND_DOWN)
        if limit <= 0:
            return None
        self.order_pending = True
        return Intent(self.symbol, available_long_qty, limit, now, total, recent)

    def reconcile(self, *, broker_outcome: str, remaining_long_qty: D,
                  known_no_open_sell: bool):
        if broker_outcome not in {"FILLED", "CANCELLED", "REJECTED", "PARTIAL", "UNKNOWN"}:
            raise ValueError("unrecognized outcome")
        if not remaining_long_qty.is_finite() or remaining_long_qty < 0:
            raise ValueError("invalid remaining shares")
        if broker_outcome in {"UNKNOWN", "PARTIAL"}:
            self.locked_uncertain = True
            self.order_pending = True
        elif broker_outcome == "FILLED":
            self.order_pending = False
            self.locked_uncertain = remaining_long_qty != 0 or not known_no_open_sell
        else:
            self.order_pending = not known_no_open_sell
            self.locked_uncertain = not known_no_open_sell
