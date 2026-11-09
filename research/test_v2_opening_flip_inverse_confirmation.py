"""No-broker tests for SOXS/SOXL confirmation and re-trigger causality."""
import unittest
from datetime import date,datetime,time
from research.v2_stock_risk_dayphase import ET
from research.test_v2_opening_sector_flip_stress import DAY,PRE,stub,SYMS
from research.v2_opening_flip_inverse_confirmation import (
    inverse_confirmation_at,confirmed_flip)

def extras(pre=100.0,soxs=104.0,soxl=96.0):
    d={}
    closes={}
    for s,now in (("SOXS",soxs),("SOXL",soxl)):
        d[s]={
            datetime.combine(DAY,time(9,10),ET):[pre]*4+[100],
            datetime.combine(DAY,time(9,30),ET):[now]*4+[100]}
        closes[s]={PRE:100.0}
    return d,closes

class InverseConfirmationTests(unittest.TestCase):
    def test_bullish_preopen_downward_confirm(self):
        a,b=extras()
        self.assertTrue(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"soxs",4))
        self.assertTrue(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"both",4))
        self.assertFalse(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"both",6))

    def test_bearish_preopen_upward_confirm(self):
        a,b=extras(soxs=96,soxl=104)
        self.assertTrue(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),-1,"both",4))
        self.assertFalse(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"both",4))

    def test_one_inverse_is_insufficient_for_both(self):
        a,b=extras(soxs=105,soxl=99)
        now=datetime.combine(DAY,time(9,35),ET)
        self.assertTrue(inverse_confirmation_at(a,b,PRE,DAY,now,1,"soxs",4))
        self.assertFalse(inverse_confirmation_at(a,b,PRE,DAY,now,1,"both",4))

    def test_missing_quote_or_regular_close_fails_closed(self):
        a,b=extras()
        a["SOXS"].pop(datetime.combine(DAY,time(9,30),ET))
        self.assertFalse(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"soxs",2))
        a,b=extras(); b["SOXL"]={}
        self.assertFalse(inverse_confirmation_at(a,b,PRE,DAY,
            datetime.combine(DAY,time(9,35),ET),1,"both",2))

    def test_invalid_variant_and_threshold(self):
        a,b=extras();now=datetime.combine(DAY,time(9,35),ET)
        for variant,level in (("unknown",4),("both",-1),("both",99)):
            with self.assertRaises(ValueError):
                inverse_confirmation_at(a,b,PRE,DAY,now,1,variant,level)

    def test_first_qualified_event_at_0935(self):
        bars,closes=stub()
        a,b=extras()
        r=confirmed_flip(bars,closes,a,b,"AMD",PRE,DAY,"both",4)
        self.assertEqual(r["asof"],"2026-11-02T09:35:00-05:00")
        self.assertEqual(r["side"],"down")

    def test_recheck_late_qualification_not_only_first_candidate(self):
        bars,closes=stub()
        for s in SYMS:
            bars[s][datetime.combine(DAY,time(9,35),ET)]=[99.7]*4+[100]
        a,b=extras(soxs=101,soxl=99)
        a["SOXS"][datetime.combine(DAY,time(9,35),ET)]=[105]*4+[100]
        a["SOXL"][datetime.combine(DAY,time(9,35),ET)]=[95]*4+[100]
        r=confirmed_flip(bars,closes,a,b,"AMD",PRE,DAY,"both",4)
        self.assertEqual(r["asof"],"2026-11-02T09:40:00-05:00")

    def test_no_future_bar_leakage_into_0935(self):
        bars,closes=stub()
        a,b=extras(soxs=101,soxl=99)
        future=datetime.combine(DAY,time(9,35),ET)
        a["SOXS"][future]=[1000]*4+[100]
        a["SOXL"][future]=[1]*4+[100]
        self.assertIsNone(confirmed_flip(bars,closes,a,b,"AMD",PRE,DAY,
                                          "both",4))

    def test_no_original_sector_flip_no_confirmation(self):
        bars,closes=stub(post_value=100.8)
        a,b=extras(soxs=108,soxl=92)
        self.assertIsNone(confirmed_flip(bars,closes,a,b,"AMD",PRE,DAY,
                                          "both",2))

if __name__=="__main__":unittest.main()
