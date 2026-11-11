"""Independent causal and retrospective-contamination checks for seven-sector V2 shadow."""
import json
import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo

from research import v2_sector_forecast_policy_20261111 as pol
from research import v2_forward_only_sector_shadow_20261109 as capture
from research import v2_forward_shadow_score_20261111 as scoring

ET=ZoneInfo("America/New_York")
NOW=datetime(2026,11,12,9,35,40,tzinfo=ET)
def sample_inputs(etf_move=.30,peer_moves=(.25,.15,.12)):
    previous={}
    features={}
    for sector,(etf,peers) in capture.SECTORS.items():
        for symbol in (etf,*peers):
            previous[symbol]={
                "five_previous_dates":["2026-11-05","2026-11-06","2026-11-09","2026-11-10","2026-11-11"],
                "five_previous_closes":[100,100,100,100,100],
            }
            n=0 if symbol==etf else list(peers).index(symbol)
            pct=etf_move if symbol==etf else peer_moves[n]
            features[symbol]={
                "from_0930_open_pct":pct, "last_5m_pct":0.1,
                "observed_price":100+float(pct),
                "observed_bar_end_ET":"2026-11-12T09:35:00-05:00",
            }
    return previous,features

class IndependentFrozenCoverageTests(unittest.TestCase):
    def test_both_arms_cover_every_sector_with_frozen_id(self):
        prev,features=sample_inputs()
        for sector,(etf,peers) in capture.SECTORS.items():
            group={s:features[s] for s in (etf,*peers)}
            row=pol.frozen_forecast(sector,etf,peers,group,prev,NOW)
            self.assertEqual(row["benchmark_side"],"UP")
            self.assertEqual(row["peer_confirmed_side"],"UP")
            self.assertEqual(row["policy_sha256"],pol.POLICY_SHA256)
            self.assertFalse(row["alerts_authorized"])
            self.assertFalse(row["orders_authorized"])

    def test_observed_bar_cannot_come_from_future(self):
        prev,features=sample_inputs()
        features["SOXX"]["observed_bar_end_ET"]=(NOW+timedelta(seconds=1)).isoformat()
        row=pol.frozen_forecast("semiconductors","SOXX",("AMD","MU","NVDA"),
                                {s:features[s] for s in ("SOXX","AMD","MU","NVDA")},prev,NOW)
        self.assertEqual(row["peer_confirmed_side"],"ABSTAIN")

    def test_missing_peer_never_becomes_zero_or_qualified(self):
        prev,features=sample_inputs()
        features.pop("AMD")
        row=pol.frozen_forecast("semiconductors","SOXX",("AMD","MU","NVDA"),
                                features,prev,NOW)
        self.assertEqual(row["peer_confirmed_side"],"ABSTAIN")

    def test_score_rejects_old_nonforecast_schema(self):
        doc={"schema_version":1,"sectors":{}}
        with self.assertRaises(ValueError):
            scoring.validate_seal(json.dumps(doc),"2026-11-10","09:35")

    def test_score_direction_is_future_only_with_flat_not_hit(self):
        self.assertEqual(scoring.score_one("UP",100,100.8)["direction"],"HIT")
        self.assertEqual(scoring.score_one("DOWN",100,99.2)["direction"],"HIT")
        self.assertEqual(scoring.score_one("UP",100,99.2)["direction"],"MISS")
        self.assertEqual(scoring.score_one("DOWN",100,100.03)["direction"],"TINY_NOT_A_HIT")
        self.assertEqual(scoring.score_one("UP",100,100)["direction"],"TINY_NOT_A_HIT")
        self.assertEqual(scoring.score_one("ABSTAIN",100,102)["direction"],"ABSTAIN")
        self.assertEqual(scoring.score_one("UP",100,None)["direction"],"MISSING_OUTCOME")

    def test_future_only_marks_and_no_rewrite(self):
        self.assertFalse(hasattr(scoring,"place_order"))
        self.assertFalse(hasattr(scoring,"submit_order"))
        self.assertFalse(hasattr(scoring,"pushover"))
        self.assertTrue(callable(scoring._atomic_new))

if __name__=="__main__":
    unittest.main()
