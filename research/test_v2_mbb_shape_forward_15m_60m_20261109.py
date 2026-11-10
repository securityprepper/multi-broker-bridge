"""Tests for signal-mark post-signal 15/60m no-lookahead AMD outcome scoring."""
from __future__ import annotations
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from v2_mbb_shape_forward_15m_60m_20261109 import observed_completed_close,evaluate
NY=ZoneInfo("America/New_York")
def d(h=4,m=0,s=0):
    return datetime(2026,11,6,h,m,s,tzinfo=NY)
def row(z,p):
    return (z,[p,p,p,p,100,"sip"])
class TestForwardHorizon(unittest.TestCase):
    def test_incomplete_current_bar_is_excluded(self):
        b=[row(d(4,0),100),row(d(4,1),200)]
        self.assertEqual(observed_completed_close(b,d(4,1,40))[1],100)
    def test_recent_completed_bar_selected(self):
        b=[row(d(4,0),100),row(d(4,1),101),row(d(4,2),102)]
        self.assertEqual(observed_completed_close(b,d(4,2,40))[1],101)
    def test_old_bar_abstains(self):
        b=[row(d(4,0),100)]
        self.assertIsNone(observed_completed_close(b,d(4,10)))
    def test_empty_abstains(self):
        self.assertIsNone(observed_completed_close([],d(4,10)))
    def test_prospective_signal_baseline_last_completed_close(self):
        day="2026-11-06"
        raw={day:{"AMD":{
           "2026-11-06T09:00:00Z":[100,100,100,100,100,"sip"],
           "2026-11-06T09:15:00Z":[103,103,103,103,100,"sip"],
           "2026-11-06T10:00:00Z":[104,104,104,104,100,"sip"]}}}
        f={"bar_completed_by":d(4,1,40).isoformat(),
           "amd_bar_timestamp":d(4,0).isoformat()}
        audit={"days":[{"day":day,"first":{"net_breadth_3of3":f}}]}
        a=evaluate(raw,audit)
        r=a[0]
        self.assertEqual(r["signal_amd_close"],100)
        self.assertEqual(r["h15_forward_pct"],3.0)
        self.assertEqual(r["h60_forward_pct"],4.0)
        self.assertFalse(a[1].get("signal_available_at"))
    def test_future_price_never_in_trigger_inputs(self):
        day="2026-11-06"
        f={"bar_completed_by":d(4,1,40).isoformat(),
           "amd_bar_timestamp":d(4,0).isoformat()}
        def sample(future):
            r={"2026-11-06T09:00:00Z":[100,100,100,100,100,"sip"],
               "2026-11-06T09:15:00Z":[future,future,future,future,100,"sip"]}
            return evaluate({day:{"AMD":r}},{"days":[{"day":day,
                        "first":{"net_breadth_3of3":f}}]})[0]
        self.assertEqual(sample(99)["signal_amd_close"],sample(110)["signal_amd_close"])
        self.assertNotEqual(sample(99)["h15_forward_pct"],sample(110)["h15_forward_pct"])
if __name__=="__main__":unittest.main()
