"""As-of confirmation / delayed hypothetical exits: no broker actions."""
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import v2_semi_confirm_five_min as s
ET=ZoneInfo("America/New_York")
class SemiConfirmTests(unittest.TestCase):
    def setUp(self):
        self.d="2026-11-09";p="2026-11-06";n="2026-11-10"
        def stamp(day,hhmm):
            return datetime.fromisoformat(day+"T"+hhmm+":00").replace(tzinfo=ET)
        def b(day,hhmm,o,c):
            return (stamp(day,hhmm),o,c)
        self.ss={}
        for symbol in ("AMD","SOXX"):
            prior=100 if symbol=="AMD" else 200
            # first warning at 09:40, later closes at 09:45 & 09:50
            self.ss[symbol]={p:{"15:55":b(p,"15:55",prior,prior)},
              self.d:{"09:30":b(self.d,"09:30",prior,prior),
                "09:35":b(self.d,"09:35",prior*.975,prior*.975),
                "09:40":b(self.d,"09:40",prior*.972,prior*.971),
                "09:45":b(self.d,"09:45",prior*.970,prior*.969),
                "09:50":b(self.d,"09:50",prior*.968,prior*.967)},
              n:{"09:30":b(n,"09:30",prior*.958,prior*.957)}}
        self.event={"sym":"AMD","day":self.d,
            "alert_at":stamp(self.d,"09:40").isoformat(),
            "total_pct":-2.5,"last15_pp":-1.0,"major":True}
    def test_confirmation_after_complete_bar_only(self):
        row=s.eligible_confirm(self.event,self.ss,5,.1,"stock_sector")
        self.assertIsNotNone(row)
        self.assertEqual(row["confirmation_time"].split("T")[1][:5],"09:45")
        self.assertEqual(row["entry_time"].split("T")[1][:5],"09:50")
        self.assertEqual(row["next_regular_open_at"][:10],"2026-11-10")
    def test_sector_recovery_prevents_confirmation(self):
        self.ss["SOXX"][self.d]["09:40"]=(
          self.ss["SOXX"][self.d]["09:40"][0],210,210)
        self.assertIsNone(s.eligible_confirm(self.event,self.ss,5,.1,"stock_sector"))
        self.assertIsNotNone(s.eligible_confirm(self.event,self.ss,5,.1,"stock"))
    def test_higher_threshold_excludes_marginal_move(self):
        self.assertIsNone(s.eligible_confirm(self.event,self.ss,5,.5,"stock"))
    def test_no_next_bar_fails_closed(self):
        del self.ss["AMD"][self.d]["09:50"]
        self.assertIsNone(s.eligible_confirm(self.event,self.ss,5,.1,"stock"))
    def test_no_next_bar_after_delay(self):
        row=s.eligible_confirm(self.event,self.ss,10,.1,"stock")
        self.assertIsNone(row)  # next simulated entry 09:55 absent
    def test_empty_stat_keeps_denominator(self):
        self.assertEqual(s.stats([],49)["missed_severe"],49)
        self.assertEqual(s.stats([],49)["nonmajor_warnings"],0)

if __name__=="__main__":unittest.main()
