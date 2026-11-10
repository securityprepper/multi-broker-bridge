import unittest
from collections import defaultdict
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
import v2_premarket_0925_after_signal_seven_sector_20261109 as s

ET=ZoneInfo("America/New_York")
HISTORY=["2026-10-01","2026-10-02","2026-10-05","2026-10-06","2026-10-07"]
DAY="2026-10-08"
SYMS=("SOXX","AMD","MU","NVDA")

def make_cache(history=HISTORY, include_etf=True, peer_count=3, future=True):
    data=defaultdict(lambda:defaultdict(dict))
    for sym in SYMS:
        for d in history:
            dt=datetime.fromisoformat(d).replace(tzinfo=ET,hour=9,minute=30)
            for i in range(78):
                z=dt+timedelta(minutes=5*i)
                data[sym][d][z]=(100.,100.,100.,100.)
        d=datetime.fromisoformat(DAY).replace(tzinfo=ET,hour=9,minute=20)
        if (sym=="SOXX" and include_etf) or (sym=="AMD" or (sym=="MU" and peer_count>=2) or (sym=="NVDA" and peer_count==3)):
            px=101 if sym=="SOXX" else 100.7
            data[sym][DAY][d]=(px,px,px,px)
        # opening mark is AFTER decision snapshot and MUST NOT change event time
        op=d+timedelta(minutes=10)
        data[sym][DAY][op]=(101.2,101.2,101.2,101.2)
        if future:
            end=d+timedelta(hours=5,minutes=15) # 14:35
            data[sym][DAY][end]=(104,104,104,104)
    return data

class TestEarlyPremarket(unittest.TestCase):
    def test_asof_0920_bar_earliest_0925(self):
        d=make_cache()
        e=s.analyze_sector(d,"semiconductors",.5)[0]["event"]
        self.assertEqual(e["signal_et"],"09:25")
        self.assertEqual(e["source_bar_start_et"],"09:20")
        self.assertEqual(e["ref_to_signal_pct"],1.0)
        self.assertEqual(e["peers_confirmed"],3)
        self.assertEqual(e["source_refday"],"2026-10-07")
    def test_future_price_does_not_select_or_change_signal(self):
        a=s.analyze_sector(make_cache(future=False),"semiconductors",.5)[0]["event"]
        b=s.analyze_sector(make_cache(),"semiconductors",.5)[0]["event"]
        self.assertEqual(a["signal_price"],b["signal_price"])
        self.assertEqual(a["sign"],b["sign"])
        self.assertIsNone(a["future_sign_pct"])
        self.assertGreater(b["future_sign_pct"],0)
    def test_requires_five_prior_completed_sessions(self):
        d=make_cache(history=HISTORY[:4])
        self.assertEqual(s.analyze_sector(d,"semiconductors",.5),[])
    def test_missing_exact_etf_premarket_bar_abstains_in_denominator(self):
        d=make_cache(include_etf=False)
        rows=s.analyze_sector(d,"semiconductors",.5)
        self.assertEqual(len(rows),1)
        self.assertEqual(s.summarize(rows)["abstained"],1)
        self.assertIsNone(rows[0]["event"])
    def test_only_one_peer_does_not_qualify(self):
        d=make_cache(peer_count=3)
        for sym in ("MU","NVDA"):
            z=datetime.fromisoformat(DAY).replace(tzinfo=ET,hour=9,minute=20)
            d[sym][DAY][z]=(99,99,99,99)
        self.assertIsNone(s.analyze_sector(d,"semiconductors",.5)[0]["event"])
    def test_stale_or_missing_peer_does_not_qualify(self):
        d=make_cache(peer_count=1)
        self.assertIsNone(s.analyze_sector(d,"semiconductors",.5)[0]["event"])
    def test_future_outcomes_are_separate_from_trade_marks(self):
        e=s.analyze_sector(make_cache(),"semiconductors",.5)[0]["event"]
        self.assertAlmostEqual(e["future_sign_pct"],(104/101-1)*100,places=5)
        self.assertAlmostEqual(e["modeled_0930_1440_after_30bp_pct"],(104/101.2-1)*100-.3,places=5)
    def test_future_tiny_not_hit(self):
        rows=[{"day":"2026-10-08","event":{"sign":1,"future_sign_pct":.03,"modeled_0930_1440_after_30bp_pct":-.5}}]
        r=s.summarize(rows)
        self.assertEqual(r["future_hit"],0)
        self.assertEqual(r["future_tiny"],1)
    def test_no_live_execution_method(self):
        self.assertFalse(hasattr(s,"submit_order"))
        self.assertFalse(hasattr(s,"place_order"))
if __name__=="__main__":unittest.main()
