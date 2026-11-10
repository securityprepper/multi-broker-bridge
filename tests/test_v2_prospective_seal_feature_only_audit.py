"""Research-only as-of / no-lookahead tests. No broker dependencies."""
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
import v2_prospective_seal_feature_only_audit as mod


def fixture(when="2026-11-10T09:35:25-05:00", bar="2026-11-10T09:35:00-05:00", px=100.0):
    sectors = {
        name: {
            "status": "ASOF_FEATURES",
            "features": {
                symbol: {
                    "observed_bar_end_ET": bar,
                    "observed_price": px,
                    "from_0930_open_pct": 0.0,
                    "last_5m_pct": 0.0,
                }
            },
            "shadow_classification": None,
        }
        for name, symbol in mod.ETFS.items()
    }
    return {
        "time_of_observation_ET": when,
        "forecast_slot_ET": when[11:16],
        "research_only": True,
        "orders_submitted": 0,
        "PAPER_orders_allowed": False,
        "LIVE_orders_allowed": False,
        "no_current_or_future_outcomes_in_document": True,
        "sectors": sectors,
    }


class ProspectiveSealTests(unittest.TestCase):
    def test_valid_seal_all_sectors(self):
        x = mod.validate_seal(fixture())
        self.assertEqual(x["feature_counts"]["ASOF_FEATURES"], 7)
        self.assertEqual(x["classifications"]["UP"], 0)

    def test_future_bar_rejected(self):
        x = fixture(bar="2026-11-10T09:40:00-05:00")
        with self.assertRaisesRegex(ValueError, "future"):
            mod.validate_seal(x)

    def test_future_data_flag_rejected(self):
        x = fixture()
        x["no_current_or_future_outcomes_in_document"] = False
        with self.assertRaisesRegex(ValueError, "future"):
            mod.validate_seal(x)

    def test_broker_permission_rejected(self):
        x = fixture()
        x["PAPER_orders_allowed"] = True
        with self.assertRaisesRegex(ValueError, "broker"):
            mod.validate_seal(x)

    def test_missing_timezone_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            mod.timestamp("2026-11-10T09:35:00")

    def test_missing_sector_abstains(self):
        x = fixture()
        x["sectors"]["gold_miners"]["status"] = "ABSTAIN_MISSING_ASOF_DATA"
        x["sectors"]["gold_miners"]["features"] = {}
        out = mod.validate_seal(x)
        self.assertNotIn("gold_miners", out["etf_marks"])

    def test_feature_only_never_scored(self):
        original = fixture()
        later = mod.validate_seal(fixture(when="2026-11-10T10:05:25-05:00",
                                          bar="2026-11-10T10:05:00-05:00", px=104))
        result = mod.score_frozen_forecast(original, later, "semiconductors")
        self.assertEqual(result["status"], "NO_PRECOMMITTED_DIRECTION_NOT_SCORABLE")

    def test_only_post_signal_prediction(self):
        original = fixture()
        original["sectors"]["semiconductors"]["shadow_classification"] = "UP"
        later = mod.validate_seal(fixture(when="2026-11-10T10:05:25-05:00",
                                          bar="2026-11-10T10:05:00-05:00", px=101))
        self.assertEqual(mod.score_frozen_forecast(original, later, "semiconductors")["status"], "HIT")
        original["sectors"]["semiconductors"]["shadow_classification"] = "DOWN"
        self.assertEqual(mod.score_frozen_forecast(original, later, "semiconductors")["status"], "MISS")

    def test_tiny_change_not_hit(self):
        original = fixture()
        original["sectors"]["semiconductors"]["shadow_classification"] = "UP"
        later = mod.validate_seal(fixture(when="2026-11-10T10:05:25-05:00",
                                          bar="2026-11-10T10:05:00-05:00", px=100.02))
        self.assertEqual(mod.score_frozen_forecast(original, later, "semiconductors")["status"], "FLAT_OR_TINY")

    def test_bars_not_from_future_even_if_direction_valid(self):
        original = fixture()
        original["sectors"]["semiconductors"]["shadow_classification"] = "UP"
        old = mod.validate_seal(fixture())
        with self.assertRaisesRegex(ValueError, "after signal"):
            mod.score_frozen_forecast(original, old, "semiconductors")

    def test_descriptive_not_prediction(self):
        first = mod.validate_seal(fixture())
        later = mod.validate_seal(fixture(when="2026-11-10T10:05:25-05:00",
                                          bar="2026-11-10T10:05:00-05:00", px=103))
        out = mod.observational_move(first, later, "semiconductors")
        self.assertEqual(out["status"], "DESCRIPTIVE_MOVE_NOT_PREDICTION")
        self.assertEqual(out["forward_change_pct"], 3.0)

    def test_no_malformed_abstention_with_prices(self):
        x = fixture()
        x["sectors"]["gold_miners"]["status"] = "ABSTAIN_MISSING_ASOF_DATA"
        with self.assertRaisesRegex(ValueError, "abstention"):
            mod.validate_seal(x)


if __name__ == "__main__":
    unittest.main()

