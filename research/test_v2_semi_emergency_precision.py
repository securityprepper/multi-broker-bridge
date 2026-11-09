import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from research.v2_semi_emergency_precision import eligible,parse,prior_price,first_signals
class OverlapTests(unittest.TestCase):
 def test_total_includes_last15(self):
  ET=ZoneInfo("America/New_York")
  d=datetime(2026,1,6,10,0,tzinfo=ET)
  days={"2026-01-05":{"15:55":(d,100,100)},"2026-01-06":{
    "09:45":(d,98.5,98.5),"10:00":(d,97.5,97.5)}}
  ser={"AMD":days}
  self.assertTrue(eligible(ser,"AMD","2026-01-06","10:00",100,2.5,1,"none"))
  self.assertFalse(eligible(ser,"AMD","2026-01-06","10:00",100,3,1,"none"))
 def test_requires_complete_15m(self):
  d=datetime(2026,1,6,10,0,tzinfo=ZoneInfo("America/New_York"))
  ser={"AMD":{"2026-01-06":{"10:00":(d,97,97)}}}
  self.assertFalse(eligible(ser,"AMD","2026-01-06","10:00",100,2.5,1,"none"))
 def test_missing_sector_fails_closed(self):
  d=datetime(2026,1,6,10,0,tzinfo=ZoneInfo("America/New_York"))
  ser={"AMD":{"2026-01-06":{"09:45":(d,99,99),"10:00":(d,97,97)}},"SOXX":{}}
  self.assertFalse(eligible(ser,"AMD","2026-01-06","10:00",100,2.5,1,"soxx"))
if __name__=="__main__":unittest.main()
