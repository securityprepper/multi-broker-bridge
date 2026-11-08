"""Durable no-duplicate reservation for PAPER submission attempts.

Unknown results intentionally block resubmission until broker reconciliation.
This stores no API credentials, account IDs or account balances.
"""
from __future__ import annotations
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from .models import LimitOrder, OrderRejected

class DuplicateOrder(OrderRejected):
    pass

def state_path() -> Path:
    configured = os.getenv("MULTI_BROKER_STATE_DIR", "")
    if not configured or not Path(configured).is_absolute():
        raise OrderRejected("set absolute MULTI_BROKER_STATE_DIR in a private directory")
    folder = Path(configured)
    if not folder.exists():
        folder.mkdir(mode=0o700, parents=True)
    stat = folder.lstat()
    if folder.is_symlink() or (stat.st_mode & 0o077):
        raise OrderRejected("state folder must not allow group/other access")
    return folder / "paper-orders.sqlite3"

@contextmanager
def connect(path: Path):
    if not path.is_absolute() or path.is_symlink():
        raise OrderRejected("database path must be absolute, non-symlink")
    if path.exists() and (path.stat().st_mode & 0o077):
        raise OrderRejected("database permissions are not private")
    previous = os.umask(0o077)
    try:
        db = sqlite3.connect(str(path), timeout=10)
    finally:
        os.umask(previous)
    try:
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("""CREATE TABLE IF NOT EXISTS orders(
            broker TEXT NOT NULL, client_id TEXT NOT NULL,
            symbol TEXT NOT NULL, side TEXT NOT NULL, qty INTEGER NOT NULL,
            price TEXT NOT NULL, state TEXT NOT NULL,
            broker_id TEXT, PRIMARY KEY(broker,client_id)
        )""")
        db.commit()
        yield db
    finally:
        db.close()

def reserve(db: sqlite3.Connection, req: LimitOrder) -> None:
    """A second attempt is forbidden even if the previous one timed out."""
    try:
        db.execute("BEGIN IMMEDIATE")
        db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?)",
                   (req.broker, req.client_order_id, req.symbol, req.side,
                    req.qty, str(req.limit_price), "UNKNOWN", None))
        db.commit()
    except sqlite3.IntegrityError as exc:
        db.rollback()
        raise DuplicateOrder("existing client order id: inspect broker before any new action") from exc
    except BaseException:
        db.rollback()
        raise

def record(db: sqlite3.Connection, req: LimitOrder, status: str, broker_id: str | None) -> None:
    """Only the current reserved intent may receive a readback status."""
    if status not in ("SUBMITTED", "ACCEPTED", "REJECTED", "UNKNOWN"):
        raise OrderRejected("invalid receipt status")
    db.execute("UPDATE orders SET state=?,broker_id=? WHERE broker=? AND client_id=?",
               (status,broker_id,req.broker,req.client_order_id))
    db.commit()
