"""Pure tests for 2026-11-09 offline 20-day MBB signal-shape audit."""
from __future__ import annotations
import unittest
from datetime import datetime,timedelta,time
from zoneinfo import ZoneInfo
from v2_mbb_early_shape_vs_breadth_20261109 import (
    rising_shape,eligible_now,observe,previous_rth_close,NY
)
from v2_mbb_shape_vs_breadth_forward_20261109 import (
    mark_at_first_future_open,exit_at_flat,metrics
)
def z(d="2026-11-06",hh=4,mm=0,ss=0):
    return datetime.fromisoformat(d).replace(tzinfo=NY,hour=hh,minute=mm,second=ss)

def seq(vs=(101.,102.,103.,104.),day="2026-11-06"):
    return [(z(day,4,i),v+1,v-1,v,"sip") for i,v in enumerate(vs)]

class TestMBBShapeVsBreadth(unittest.TestCase):
    def test_four_consecutive_successive_higher_highs_lows(self):
        self.assertTrue(rising_shape([r[:4] for r in seq()]))
    def test_net_up_is_not_monotonic_bar_shape(self):
        a=[r[:4] for r in seq((101,101,103,103))]
        self.assertFalse(rising_shape(a))
    def test_requires_four(self):
        self.assertFalse(rising_shape([r[:4] for r in seq()][:3]))
    def test_disqualifies_nonconsecutive(self):
        q=[list(r[:4]) for r in seq()]
        q[2][0]+=timedelta(minutes=3)
        self.assertFalse(rising_shape(q))
    def test_disqualifies_single_bar_spike(self):
        self.assertFalse(rising_shape([r[:4] for r in seq((100,103,105,107))]))
    def test_no_incomplete_bar_in_observation(self):
        now=z(mm=4,ss=40)
        a=eligible_now(seq((100,101,102,103,104)),now.date(),now)
        self.assertEqual([r[0].minute for r in a],[0,1,2,3])
        self.assertNotIn(4,[r[0].minute for r in a])
    def test_positive_net_breadth_not_sufficient_for_MBB_buy(self):
        day=z().date();now=z(mm=4,ss=40)
        d={s:seq((100,100,100,100,100)) for s in ("AMD","MU","SNDK")}
        a=observe(d,day,now,{s:95 for s in d})
        self.assertTrue(a["net_breadth_3of3"])
        self.assertFalse(a["MBB_eligible_AMD_shape"])
    def test_strict_MBB_buy_with_two_rising_anchors(self):
        day=z().date();now=z(mm=4,ss=40)
        a=observe({"AMD":seq(),"MU":seq(),"SNDK":[]},
                  day,now,{"AMD":99,"MU":99,"SNDK":99})
        self.assertTrue(a["MBB_eligible_AMD_shape"])
        self.assertFalse(a["net_breadth_3of3"])
    def test_prev_close_must_be_prior_day(self):
        d=z().date()
        a=[(z("2026-11-05",hh=15,mm=59),100,100,100,"sip"),
           (z("2026-11-06",hh=15,mm=59),200,200,200,"sip")]
        self.assertEqual(previous_rth_close(a,d),100)
    def test_future_entry_not_signal_bar(self):
        now=z(mm=2,ss=40);bars=[(z(mm=2),[100]),(z(mm=3),[101])]
        self.assertEqual(mark_at_first_future_open(bars,now)[0],z(mm=3))
    def test_no_entry_if_too_old_or_only_pre_signal(self):
        now=z(mm=2,ss=40);bars=[(z(mm=2),[100]),(z(mm=8),[101])]
        self.assertIsNone(mark_at_first_future_open(bars,now))
    def test_exit_requires_exact_1340_chicago(self):
        day="2026-11-06";b=[(z(day,hh=14,mm=39),[100]),
                            (z(day,hh=14,mm=40),[101])]
        self.assertEqual(exit_at_flat(b,day)[0],z(day,hh=14,mm=40))
        self.assertIsNone(exit_at_flat(b[:1],day))
if __name__=="__main__":unittest.main()
