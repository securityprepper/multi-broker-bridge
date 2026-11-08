"""Provider-neutral one-minute trend signals; NO BROKER API CALLS.

Feed one-minute OHLC bars from a licensed, sufficiently current market-data
source. This pure reducer does not assume an observed last trade is executable
or treat software exits as guaranteed stop orders.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from math import ceil
from zoneinfo import ZoneInfo
from collections import defaultdict, deque
from .watchlists import SECTORS, SECTOR_ETFS

CHICAGO=ZoneInfo("America/Chicago")
MAX_BAR_AGE=timedelta(seconds=95)
MIN_COVERAGE=0.60
MIN_RISING_BREADTH=0.60
MAX_SINGLE_BAR_JUMP=Decimal("0.025")  # exclude one-bar +2.5% spikes
PROFIT_TARGET=Decimal("0.01")
LOSS_WATCH=Decimal("-0.01")
TRAIL_ENABLE=Decimal("0.005")
TRAIL_REVERSAL=Decimal("0.005")
NEW_ENTRY_CUTOFF=time(13,30)
DAY_EXIT_CUTOFF=time(13,55)

@dataclass(frozen=True)
class Bar:
    symbol:str
    timestamp:datetime
    high:Decimal
    low:Decimal
    close:Decimal
    bid:Decimal|None=None
    ask:Decimal|None=None

    def __post_init__(self):
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone aware")
        for key in ("high","low","close"):
            value=getattr(self,key)
            if type(value) is not Decimal or not value.is_finite() or value<=0:
                raise ValueError("non-positive or nonfinite bar "+key)
        if not self.low<=self.close<=self.high:
            raise ValueError("bar close outside range")
        for key in ("bid","ask"):
            value=getattr(self,key)
            if value is not None and (type(value) is not Decimal or
                                      not value.is_finite() or value<=0):
                raise ValueError("invalid "+key)
        if self.bid is not None and self.ask is not None and self.bid>self.ask:
            raise ValueError("crossed bid/ask")

    @classmethod
    def parse(cls,payload:dict):
        if not isinstance(payload,dict):
            raise ValueError("bar must be object")
        ts=datetime.fromisoformat(payload["timestamp"].replace("Z","+00:00"))
        def dec(key):
            value=payload.get(key)
            return None if value is None else Decimal(str(value))
        return cls(str(payload["symbol"]).upper(),ts,
                   dec("high"),dec("low"),dec("close"),dec("bid"),dec("ask"))

@dataclass(frozen=True)
class Holding:
    symbol:str
    quantity:int
    entry_price:Decimal
    highest_since_entry:Decimal

    def __post_init__(self):
        if type(self.quantity) is not int or self.quantity<=0:
            raise ValueError("holding quantity")
        if self.entry_price<=0 or self.highest_since_entry<self.entry_price:
            raise ValueError("invalid holding entry/high")

def _is_fresh(bar:Bar,now:datetime)->bool:
    age=now-bar.timestamp
    return timedelta(0)<=age<=MAX_BAR_AGE

def _three_rising(bars:list[Bar]) -> bool:
    if len(bars)<4:return False
    values=bars[-4:]
    for before,after in zip(values,values[1:]):
        if after.timestamp<=before.timestamp:
            return False
        if after.timestamp-before.timestamp>timedelta(seconds=90):
            return False
        if not (after.high>before.high and after.low>before.low):
            return False
        if (after.close-before.close)/before.close>MAX_SINGLE_BAR_JUMP:
            return False
    return values[-1].close>values[0].close

def _two_falling(bars:list[Bar])->bool:
    if len(bars)<3:return False
    a,b,c=bars[-3:]
    return b.high<a.high and b.low<a.low and c.high<b.high and c.low<b.low

class TrendMonitor:
    def __init__(self,sectors=None):
        self.sectors=dict(SECTORS if sectors is None else sectors)
        self.bars=defaultdict(lambda:deque(maxlen=5))
        self.last_scan_timestamp=None

    def add(self,bar:Bar):
        if bar.timestamp.tzinfo is None:raise ValueError("UTC required")
        history=self.bars[bar.symbol]
        if history and bar.timestamp<=history[-1].timestamp:
            raise ValueError("stale or duplicate bar")
        history.append(bar)

    def breadth(self,sector:str,now:datetime)->dict:
        symbols=self.sectors[sector]
        qualifying=[]
        covered=0
        for symbol in symbols:
            bars=list(self.bars[symbol])
            if bars and _is_fresh(bars[-1],now) and len(bars)>=4:
                covered+=1
                if _three_rising(bars):
                    qualifying.append(symbol)
        required=max(3,ceil(len(symbols)*MIN_COVERAGE))
        breadth=(len(qualifying)/covered) if covered else 0.
        return {"sector":sector,"covered":covered,"total":len(symbols),
                "rising":len(qualifying),"breadth":round(breadth,3),
                "qualified":covered>=required and breadth>=MIN_RISING_BREADTH,
                "rising_symbols":qualifying}

    def scan(self,now:datetime,holdings:dict[str,Holding]|None=None,
             executable_session:bool=False)->list[dict]:
        if now.tzinfo is None:raise ValueError("aware scan time required")
        if self.last_scan_timestamp is not None and now<=self.last_scan_timestamp:
            raise ValueError("scan time did not advance")
        self.last_scan_timestamp=now
        chicago=now.astimezone(CHICAGO)
        current=chicago.timetz().replace(tzinfo=None)
        positions=holdings or {}
        output=[]
        # Exit evaluations run even when a sector is no longer rising.
        for symbol,position in positions.items():
            bars=list(self.bars[symbol])
            if not bars or not _is_fresh(bars[-1],now):
                output.append({"symbol":symbol,"action":"FEED_STALE_HOLDING",
                               "reason":"do not claim a working software stop"})
                continue
            last=bars[-1]
            change=(last.close-position.entry_price)/position.entry_price
            high=max(position.highest_since_entry,last.high)
            trail=(last.close/high)-Decimal("1")
            reason=None
            if current>=DAY_EXIT_CUTOFF:reason="mandatory exit by 2 PM Chicago"
            elif change<=LOSS_WATCH:reason="loss threshold reached"
            elif change>=PROFIT_TARGET:reason="profit target reached"
            elif high>=position.entry_price*(1+TRAIL_ENABLE) and trail<=-TRAIL_REVERSAL:
                reason="trailing peak reversal"
            elif _two_falling(bars):reason="two completed bars with lower highs and lower lows"
            if reason:
                output.append({"symbol":symbol,
                               "action":"SELL_LIMIT_CANDIDATE" if last.bid is not None and executable_session else "EXIT_WATCH",
                               "quantity":position.quantity,
                               "reference_bid":str(last.bid) if last.bid else None,
                               "reason":reason})
        # Never add new risk when our clock is outside the entry window.
        if current>=NEW_ENTRY_CUTOFF or current>=DAY_EXIT_CUTOFF:
            return output
        for sector in self.sectors:
            strength=self.breadth(sector,now)
            if not strength["qualified"]:continue
            for symbol in strength["rising_symbols"]:
                if symbol in positions:continue
                last=self.bars[symbol][-1]
                output.append({"sector":sector,"symbol":symbol,
                               "action":"BUY_LIMIT_CANDIDATE" if last.ask is not None and executable_session else "BUY_WATCH",
                               "reference_ask":str(last.ask) if last.ask else None,
                               "rising_breadth":strength["breadth"],
                               "reason":"three successive higher highs and lows; breadth confirmed, no single large spike"})
            # SOXX preferred over SOXL: use as a ONE-ETF alternative,
            # never automatically double sector exposure with all stocks.
            output.append({"sector":sector,"symbol":SECTOR_ETFS.get(sector),
                           "action":"ETF_ALTERNATIVE_WATCH",
                           "reason":"unleveraged sector ETF alternative; do not auto-buy alongside constituents"})
        return output
