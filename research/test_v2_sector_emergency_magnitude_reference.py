import unittest
from research.v2_sector_emergency_magnitude_reference import historical_cutoffs
class TestShockReference(unittest.TestCase):
    def data(self):
        return [{"sector":"semis","day":f"2026-01-{i:03d}",
                 "ETF_full_day_pct":str((i%12)*.5)} for i in range(120)]
    def test_training_only_ignores_later_outlier(self):
        x=historical_cutoffs(self.data(),min_training_days=80)
        z=self.data()
        z[-1]["ETF_full_day_pct"]="99"
        y=historical_cutoffs(z,min_training_days=80)
        self.assertEqual(x["semis"]["rth_observed_shock_candidate_pct"],
                         y["semis"]["rth_observed_shock_candidate_pct"])
    def test_larger_extended_threshold(self):
        x=historical_cutoffs(self.data(),min_training_days=80)["semis"]
        self.assertGreaterEqual(x["extended_observed_shock_candidate_pct"],
                                x["rth_observed_shock_candidate_pct"])
        self.assertFalse(x["is_order_authorization"])
    def test_min_days_required(self):
        with self.assertRaises(ValueError):
            historical_cutoffs(self.data()[:20],min_training_days=80)
    def test_duplicate_rejected(self):
        a=self.data()
        with self.assertRaises(ValueError):
            historical_cutoffs(a+[a[-1]],min_training_days=80)
    def test_invalid_split(self):
        with self.assertRaises(ValueError):
            historical_cutoffs(self.data(),train_fraction=1,min_training_days=80)
if __name__=="__main__":unittest.main()
