"""Broker-transport-mocked completed five-minute direction gate tests."""
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from urllib.parse import parse_qs,urlsplit
from recommendation_paper_bridge.recent_direction import (
    require_prior_five_minutes,DirectionBlocked
)
NOW=datetime(2026,11,13,15,35,25,tzinfo=timezone.utc)
SYM="AMD"
def make_bars(vals=(100,100.1,100.2,100.3,100.4,100.5),last_shift=0):
    start=NOW.replace(second=0,microsecond=0)-timedelta(minutes=6)+timedelta(minutes=last_shift)
    return [{"t":(start+timedelta(minutes=i)).isoformat(),
             "h":str(v),"l":str(v),"c":str(v)} for i,v in enumerate(vals)]
def source(data, paginated=False):
    def fetch(method,path,body=None,data=None):
        if method!="GET" or "/v2/stocks/AMD/bars?" not in path or not data:
            raise AssertionError("unexpected API call")
        qs=parse_qs(urlsplit(path).query)
        assert qs["feed"]==["sip"] and qs["timeframe"]==["1Min"]
        return {"bars":data_list,"next_page_token":"next" if paginated else None}
    data_list=data
    return fetch
class DirectionPreflightTests(unittest.TestCase):
    def run_gate(self,bars=None,now=NOW):
        return require_prior_five_minutes(SYM,now,Decimal("100.51"),Decimal("100.52"),
                                          source(make_bars() if bars is None else bars))
    def test_positive_prior_five_minutes_pass(self):
        self.assertEqual(self.run_gate()["status"],"PRICE_5M_RISING_ASOF")
    def test_old_bars_rejected(self):
        with self.assertRaises(DirectionBlocked):self.run_gate(make_bars(last_shift=-6))
    def test_negative_five_minute_response_rejected(self):
        with self.assertRaisesRegex(DirectionBlocked,"PRICE_5M_DECLINING_AVOID"):
            self.run_gate(make_bars((100.5,100.4,100.3,100.2,100.1,99.9)))
    def test_latest_bar_negative_even_if_overall_positive(self):
        with self.assertRaisesRegex(DirectionBlocked,"PRICE_5M_LAST_COMPLETED_BAR_FALLING"):
            self.run_gate(make_bars((100,100.2,100.4,100.6,100.8,100.5)))
    def test_incomplete_pagination_rejected(self):
        with self.assertRaisesRegex(DirectionBlocked,"PRICE_5M_SOURCE_INCOMPLETE"):
            require_prior_five_minutes(SYM,NOW,Decimal("100.51"),Decimal("100.52"),
                                       source(make_bars(),paginated=True))
    def test_missing_data_rejected(self):
        with self.assertRaises(DirectionBlocked):self.run_gate([])
    def test_6_consecutive_required(self):
        rows=make_bars();rows.pop(2)
        with self.assertRaises(DirectionBlocked):self.run_gate(rows)
    def test_no_side_effect_order_or_external_broker(self):
        calls=[]
        def fn(method,path,data=False):
            calls.append((method,path))
            return {"bars":make_bars(),"next_page_token":None}
        x=require_prior_five_minutes(SYM,NOW,Decimal("100.51"),Decimal("100.52"),fn)
        self.assertEqual(x["status"],"PRICE_5M_RISING_ASOF")
        self.assertEqual(len(calls),1)
        self.assertTrue(calls[0][1].startswith("/v2/stocks/AMD/bars?"))
if __name__=="__main__": unittest.main()
