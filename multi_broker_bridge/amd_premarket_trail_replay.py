"""Nov 9 AMD 1-minute premarket trailing-stop experiment — broker READ ONLY.

Trails are paper-only hypothetical thresholds and are not Alpaca broker-native
extended-hours stops. Compare the actual entry fills and an earlier
minute-bar confirmation against minute highs/lows and continuous-rise metrics.
No live/PAPER order placement, no order cancellation or credentials logging.
"""
from __future__ import annotations
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import json
from .premarket_historical_replay import bars
CT=ZoneInfo("America/Chicago")
DAY=(2026,11,9)
OPEN=datetime(*DAY,8,30,tzinfo=CT)
HARD_FLAT=datetime(*DAY,13,40,tzinfo=CT)
START=datetime(*DAY,3,0,tzinfo=CT)

def clock(h,m,s=0):
    return datetime(*DAY,h,m,s,tzinfo=CT)

def rounded(value:Decimal|None):
    return str(value.quantize(Decimal(".001"))) if value is not None else None

def trailing(rows:list[dict],entry_time:datetime,entry:Decimal,trail:Decimal,
             endpoint:datetime)->dict:
    """Evaluate each completed minute, using previous bar's high-water stop.

    When bar low hits previous trailing threshold, report *observed
    threshold crossing*, NOT hypothetical fill at the stop price.
    A minute's high/low ordering is unknown so the previous peak is used,
    preventing optimistic lookahead in the same bar.
    """
    peak=entry
    prior_stop=entry*(Decimal(1)-trail)
    first=None;ambiguous_same_bar=0
    evaluated=0
    last_price=None
    peak_at=None
    for bar in rows:
        # Bar is only usable after its full one-minute window. Skip the
        # minute containing the entry's actual fill (intrabar order unknown).
        if bar["dt"]<entry_time.replace(second=0,microsecond=0)+timedelta(minutes=1):
            continue
        when=bar["dt"]+timedelta(minutes=1)
        if when>endpoint:break
        evaluated+=1
        if bar["low"]<=prior_stop:
            first={
                "bar_open_ct":bar["dt"].strftime("%H:%M"),
                "detectable_after_ct":when.strftime("%H:%M"),
                "trail_threshold_at_prior_peak":rounded(prior_stop),
                "bar_low":rounded(bar["low"]),
                "peak_before_crossover":rounded(peak),
            }
            break
        if bar["high"]>peak:
            peak=bar["high"];peak_at=when
        new_stop=peak*(Decimal(1)-trail)
        if bar["low"]<=new_stop and new_stop>prior_stop:
            ambiguous_same_bar+=1
        prior_stop=new_stop
        last_price=bar["close"]
    return {
        "trail_percent":rounded(trail*100),
        "triggered_by_endpoint":first is not None,
        "first_completed_bar_trigger":first,
        "highest_observed_price_before_trigger":rounded(peak),
        "peak_reached_by":peak_at.strftime("%H:%M") if peak_at else None,
        "remaining_threshold_if_no_trigger":rounded(prior_stop) if first is None else None,
        "last_close_if_no_trigger":rounded(last_price) if first is None else None,
        "completed_minutes_evaluated":evaluated,
        "ambiguous_within_bar_price_order_count":ambiguous_same_bar,
    }

def trend_metrics(rows:list[dict],start:datetime,end:datetime)->dict:
    chosen=[r for r in rows if start<=r["dt"]<end]
    if len(chosen)<2:return {"bars":len(chosen)}
    change=(chosen[-1]["close"]/chosen[0]["close"]-1)*100
    up=sum(chosen[i]["close"]>chosen[i-1]["close"] for i in range(1,len(chosen)))
    down=sum(chosen[i]["close"]<chosen[i-1]["close"] for i in range(1,len(chosen)))
    largest_rise=max((chosen[i]["close"]/chosen[i-1]["close"]-1)*100
                     for i in range(1,len(chosen)))
    largest_fall=min((chosen[i]["close"]/chosen[i-1]["close"]-1)*100
                     for i in range(1,len(chosen)))
    peak=chosen[0]["close"]
    max_drop=Decimal(0)
    for r in chosen[1:]:
        peak=max(peak,r["close"])
        max_drop=min(max_drop,(r["close"]/peak-1)*100)
    return {"bars":len(chosen),"period_change_pct":rounded(change),
            "up_close_bars":up,"down_close_bars":down,
            "largest_one_minute_close_gain_pct":rounded(largest_rise),
            "largest_one_minute_close_decline_pct":rounded(largest_fall),
            "deepest_close_to_close_pullback_pct":rounded(max_drop),
            "first_close":rounded(chosen[0]["close"]),
            "last_close":rounded(chosen[-1]["close"])}

def main():
    amd=bars("AMD")
    rba=bars("RBA")
    sndk=bars("SNDK")
    checks={}
    for label,time,price in (
        ("EARLY_0318_BAR_PROXY",clock(3,18),Decimal("458.00")),
        ("FDR_ACTUAL_BUY",clock(7,6,13),Decimal("469.000")),
        ("MBB_ACTUAL_BUY",clock(7,35,42),Decimal("466.700")),
    ):
        stop_rows=[]
        for pct in (Decimal(".01"),Decimal(".015"),Decimal(".02"),
                    Decimal(".025"),Decimal(".03")):
            stop_rows.append(trailing(amd,time,price,pct,OPEN))
        checks[label]={
            "actual_broker_fill" :label!="EARLY_0318_BAR_PROXY",
            "reference_entry_price":rounded(price),
            "entry_time_ct":time.strftime("%H:%M:%S"),
            "through_ct":OPEN.strftime("%H:%M"),
            "premarket_trails":stop_rows,
            "hypothetical_no_sell_value_at_open_bar":(
               rounded(next((b["close"] for b in amd if b["dt"]==OPEN),None))
            ),
        }
    print(json.dumps({
        "status":"READ_ONLY_AMD_PREMARKET_TRAIL_COMPARISON",
        "date_ct":"2026-11-09",
        "pre_market_historical_price_shape":{
            "AMD_03_TO_OPEN":trend_metrics(amd,START,OPEN),
            "AMD_0700_TO_OPEN":trend_metrics(amd,clock(7,0),OPEN),
            "RBA_OPEN_TO_1000":trend_metrics(rba,OPEN,clock(10,0)),
        },
        "rolling_window_shape":{
            "AMD_0300_0318":trend_metrics(amd,clock(3,0),clock(3,18)),
            "AMD_0318_0345":trend_metrics(amd,clock(3,18),clock(3,45)),
            "AMD_0630_0700":trend_metrics(amd,clock(6,30),clock(7,0)),
            "AMD_0645_0715":trend_metrics(amd,clock(6,45),clock(7,15)),
            "AMD_0650_0720":trend_metrics(amd,clock(6,50),clock(7,20)),
            "AMD_0705_0735":trend_metrics(amd,clock(7,5),clock(7,35)),
            "AMD_0710_0740":trend_metrics(amd,clock(7,10),clock(7,40)),
            "AMD_0720_0750":trend_metrics(amd,clock(7,20),clock(7,50)),
            "SNDK_0300_TO_OPEN":trend_metrics(sndk,START,OPEN),
            "RBA_0830_0900":trend_metrics(rba,OPEN,clock(9,0)),
        },
        "fills_and_trails":checks,
        "all_trailing_outcomes":"Minute-low threshold crossings only; executable bid/ask, real slippage and fill timing NOT available",
        "broker_native_extended_hours_trailing_supported":False,
        "orders_submitted":0
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
