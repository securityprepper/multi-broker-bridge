"""Conservative, provider-independent LIMIT order request."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

class OrderRejected(ValueError):
    """Request is invalid and MUST NOT be sent to a broker."""

class UnknownSubmission(RuntimeError):
    """Broker state is ambiguous. Reconcile; NEVER retry automatically."""

TICKER = re.compile(r"[A-Z][A-Z0-9.]{0,9}\Z")
CLIENT_ID = re.compile(r"[A-Za-z0-9_-]{6,64}\Z")
MAX_NOTIONAL = Decimal("2000.00")

@dataclass(frozen=True)
class LimitOrder:
    broker: str
    symbol: str
    side: str
    qty: int
    limit_price: Decimal
    client_order_id: str

    def __post_init__(self) -> None:
        if self.broker not in ("alpaca", "ibkr", "robinhood"):
            raise OrderRejected("unsupported broker")
        if not isinstance(self.symbol, str) or not TICKER.fullmatch(self.symbol):
            raise OrderRejected("invalid ticker")
        if self.side not in ("buy", "sell"):
            raise OrderRejected("invalid side")
        if type(self.qty) is not int or self.qty < 1:
            raise OrderRejected("quantity must be a positive whole-share count")
        if type(self.limit_price) is not Decimal or not self.limit_price.is_finite():
            raise OrderRejected("finite Decimal price required")
        if not Decimal("0.01") <= self.limit_price or self.limit_price != self.limit_price.quantize(Decimal("0.01")):
            raise OrderRejected("price must have two decimal places and be positive")
        if self.qty * self.limit_price > MAX_NOTIONAL:
            raise OrderRejected("PAPER limit: $2,000 maximum per independent order")
        if not isinstance(self.client_order_id, str) or not CLIENT_ID.fullmatch(self.client_order_id):
            raise OrderRejected("client order id must be 6-64 safe characters")

    @classmethod
    def make(cls, broker: str, symbol: str, side: str, qty: int, limit_price: str, client_order_id: str) -> "LimitOrder":
        try:
            price = Decimal(limit_price)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise OrderRejected("invalid price") from exc
        return cls(broker, symbol, side, qty, price, client_order_id)

    def public(self) -> dict:
        return dict(broker=self.broker, symbol=self.symbol, side=self.side,
                    qty=self.qty, limit_price=str(self.limit_price),
                    client_order_id=self.client_order_id, environment="PAPER_ONLY",
                    order_type="LIMIT", time_in_force="DAY",
                    extended_hours=False, max_notional_usd=str(MAX_NOTIONAL))

@dataclass(frozen=True)
class Receipt:
    broker: str
    client_order_id: str
    status: str
    broker_order_id: str | None = None
    note: str = ""
    def public(self) -> dict:
        return dict(broker=self.broker, client_order_id=self.client_order_id,
                    status=self.status, broker_order_id=self.broker_order_id,
                    note=self.note)
