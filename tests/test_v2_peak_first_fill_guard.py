import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from v2_peak_first_fill_guard import complete_bar_peak,UnknownFirstFillEvidence
UTC=timezone.utc
def t(h,m,s=0):return datetime(2026,11,12,h,m,s,tzinfo=UTC)
def candle(minute,hi):return {'t':t(16,minute),'high':str(hi)}
class TestPeak(unittest.TestCase):
 def test_prefill_peak_and_first_fill_overlapping_candle_are_excluded(self):
  # Accepted 16:00:40. Actual first fill 16:02:30. 101.3 at 16:01 was never owned.
  peak,status,n=complete_bar_peak('100',t(16,2,30),
     [candle(1,101.3),candle(2,102.0),candle(3,100.3)],t(16,4,40))
  self.assertEqual((peak,status,n),(Decimal('100.3'),'VERIFIED_POSTFILL_FULL_MINUTES',1))
 def test_fill_exactly_at_minute_boundary(self):
  peak,_,n=complete_bar_peak('100',t(16,2),[candle(2,101),candle(3,100.4)],t(16,4,40))
  self.assertEqual((peak,n),(Decimal('101'),2))
 def test_missing_proven_fill_rejected(self):
  with self.assertRaises(UnknownFirstFillEvidence):
   complete_bar_peak('100',None,[candle(3,105)],t(16,4,40))
 def test_missing_full_minute_not_falsely_clean(self):
  peak,status,n=complete_bar_peak('100',t(16,1,30),[candle(2,101.5)],t(16,4,40))
  self.assertEqual((peak,status,n),(None,'MISSING_COMPLETE_POSTFILL_MINUTES',1))
 def test_future_and_unfinished_minute_excluded(self):
  peak,status,n=complete_bar_peak('100',t(16,3),[candle(3,100.2),candle(4,120)],t(16,4,40))
  self.assertEqual((peak,status,n),(Decimal('100.2'),'VERIFIED_POSTFILL_FULL_MINUTES',1))
 def test_no_complete_bar_yet(self):
  peak,status,n=complete_bar_peak('100',t(16,4,10),[],t(16,4,40))
  self.assertEqual((peak,status,n),(Decimal('100'),'NO_COMPLETE_POSTFILL_BARS',0))
 def test_duplicates_rejected(self):
  with self.assertRaises(ValueError):
   complete_bar_peak('100',t(16,2),[candle(2,100.1),candle(2,100.2),candle(3,100.2)],t(16,4,40))
 def test_negative_price_rejected(self):
  with self.assertRaises(ValueError):complete_bar_peak('100',t(16,3),[candle(3,-1)],t(16,4,40))
if __name__=='__main__':unittest.main()
