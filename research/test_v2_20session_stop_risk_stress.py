"""Offline tests for as-of minute stop/hold release logic."""
import unittest
from v2_20session_stop_risk_stress import model_exit,aggregate
def bars(closes,opens=None):
    opens=opens or closes
    times=["09:%02d"%i for i in range(30,60)]+["10:%02d"%i for i in range(60)][:0]
    # real chronological 311 min stamps, including 14:40
    from datetime import datetime,timedelta
    names=[(datetime(2026,10,12,9,30)+timedelta(minutes=i)).strftime("%H:%M") for i in range(311)]
    return {"AMD":{s:[opens[min(i,len(opens)-1)],max(opens[min(i,len(opens)-1)],closes[min(i,len(closes)-1)]),min(opens[min(i,len(opens)-1)],closes[min(i,len(closes)-1)]),closes[min(i,len(closes)-1)],10] for i,s in enumerate(names)}}
class Stops(unittest.TestCase):
    def test_delayed_stop_not_same_candle(self):
        x=bars([100]*5+[100,97]+[96]*304,[100]*5+[100,100,96]+[96]*303)
        z=model_exit(x,"AMD",1,2.5)
        self.assertEqual(z["exit_clock"],"09:37")
        self.assertEqual(z["exit"],96)
    def test_hold_always_at_final(self):
        x=bars([100]*311)
        z=model_exit(x,"AMD",1,"hold")
        self.assertEqual(z["exit_clock"],"14:40")
    def test_short_stop_mirrors_up_loss(self):
        x=bars([100]*5+[100,104]+[104]*304)
        z=model_exit(x,"AMD",-1,2.5)
        self.assertEqual(z["reason"],"HARD_STOP")
    def test_trail_arms_only_after_profit(self):
        x=bars([100]*5+[100,101.5,100]+[100]*303)
        z=model_exit(x,"AMD",1,("trail",1.0,1.0))
        self.assertEqual(z["reason"],"TRAIL_FROM_MAX_FAVORABLE_CLOSE")
    def test_no_signal_denominator_is_not_trade(self):
        self.assertEqual(aggregate([])["trades"],0)
    def test_win_threshold_strict_cost(self):
        rows=[{"gross_pct":.3,"worst_completed_close_pct_to_exit":0,"hold_minutes":5,"reason":"TIME"},{"gross_pct":.31,"worst_completed_close_pct_to_exit":0,"hold_minutes":5,"reason":"TIME"}]
        self.assertEqual(aggregate(rows)["win_after_30bp"],1)
if __name__=="__main__":unittest.main()
