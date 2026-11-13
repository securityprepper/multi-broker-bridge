"""Last-five-completed-minute BUY direction, recommendation-to-PAPER bridge.

Uses the existing, independent Alpaca SIP DATA GET transport ONLY, never a
new broker account, order, or optional third-party inventory. Same pure
MBB reducer applies. A failed/unknown quote or downtrend is NO BUY.
"""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from urllib.parse import quote,urlencode

from multi_broker_bridge.trend import Bar
from multi_broker_bridge.paper_buy_safety import (
    recent_five_minute_direction,PaperBuyBlocked
)

class DirectionBlocked(ValueError):
    def __init__(self,reason):
        self.reason=str(reason)
        super().__init__(self.reason)

def require_prior_five_minutes(symbol:str,asof:datetime,bid:Decimal,ask:Decimal,httpfn):
    if asof.tzinfo is None:
        raise DirectionBlocked("PRICE_5M_CLOCK_UNKNOWN")
    start=asof-timedelta(minutes=9)
    # No intentional waiting; request only source bars already completed.
    end=asof-timedelta(seconds=15)
    qs=urlencode({"timeframe":"1Min","feed":"sip","adjustment":"split",
        "start":start.astimezone(timezone.utc).isoformat(),
        "end":end.astimezone(timezone.utc).isoformat(),
        "limit":1000,"sort":"asc"})
    path="/v2/stocks/"+quote(symbol,safe="")+"/bars?"+qs
    try:
        data=httpfn("GET",path,data=True)
        if not isinstance(data,dict) or data.get("next_page_token"):
            raise DirectionBlocked("PRICE_5M_SOURCE_INCOMPLETE")
        records=data.get("bars")
        if not isinstance(records,list) or len(records)>1000:
            raise DirectionBlocked("PRICE_5M_BAR_SOURCE_INVALID")
        bars=[]
        for row in records:
            dt=datetime.fromisoformat(row["t"].replace("Z","+00:00"))
            if dt.tzinfo is None:raise ValueError("unaware market timestamp")
            bars.append(Bar(symbol,dt,Decimal(str(row["h"])),Decimal(str(row["l"])),
                           Decimal(str(row["c"]))))
        return recent_five_minute_direction(symbol,bars,asof,bid,ask)
    except PaperBuyBlocked as exc:
        raise DirectionBlocked(exc.reason) from exc
    except DirectionBlocked:
        raise
    except (ValueError,TypeError,KeyError,ArithmeticError,OSError,OverflowError):
        raise DirectionBlocked("PRICE_5M_EVIDENCE_UNKNOWN") from None
