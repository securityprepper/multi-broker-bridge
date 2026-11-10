import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import v2_premarket_fourbar_availability_20261110 as mod

ET = ZoneInfo("America/New_York")
def make_day(day="2026-11-06", times=range(5), missing=None):
    start = datetime.fromisoformat(day + "T04:00:00").replace(tzinfo=ET)
    missing = missing or {}
    result = {}
    for symbol in mod.SYMBOLS:
        result[symbol] = {}
        for i in times:
            if i in missing.get(symbol, set()):
                continue
            stamp = (start + timedelta(minutes=i)).astimezone(
                ZoneInfo("UTC")).isoformat()
            result[symbol][stamp] = [100, 101, 99, 100, 3, "sip"]
    return result

class Coverage(unittest.TestCase):
    def test_fourbar_uses_preceding_four_not_current(self):
        row = mod.day_audit("2026-11-06", make_day(times=range(4)))
        self.assertEqual(row["fourbar_allfour"], 1)
        self.assertEqual(row["onebar_allfour"], 4)
        self.assertEqual(row["fourbar_denominator"], 326)
    def test_missing_latest_completed_bar_abstains(self):
        row = mod.day_audit("2026-11-06", make_day(
            missing={"AMD": {3}}))
        self.assertEqual(row["fourbar_amd_and_one_other_peer"], 0)
    def test_fourbar_is_not_same_minute_overlap(self):
        row = mod.day_audit("2026-11-06", make_day(
            times=(0, 1, 2, 4)))
        self.assertEqual(row["fourbar_allfour"], 0)
    def test_mbb_like_peer_minimum_is_not_3of3(self):
        row = mod.day_audit("2026-11-06", make_day(
            missing={"SNDK": {2}}))
        self.assertEqual(row["fourbar_amd_and_one_other_peer"], 2)
        self.assertEqual(row["fourbar_own_three"], 0)
    def test_soxx_absence_not_mbb_peer_failure(self):
        row = mod.day_audit("2026-11-06", make_day(
            missing={"SOXX": {2}}))
        self.assertEqual(row["fourbar_amd_and_one_other_peer"], 2)
        self.assertEqual(row["fourbar_allfour"], 0)
    def test_incomplete_invalid_prices_excluded(self):
        obs = make_day()
        key = list(obs["AMD"])[3]
        obs["AMD"][key] = [100, float("nan"), 99, 100]
        self.assertEqual(mod.day_audit("2026-11-06", obs)["fourbar_amd"], 0)
    def test_different_dst_offset_not_hardcoded(self):
        obs = make_day(day="2026-10-29")
        row = mod.day_audit("2026-10-29", obs)
        self.assertEqual(row["fourbar_allfour"], 2)
    def test_future_bars_cannot_supply_past(self):
        obs = make_day(times=range(4, 9))
        row = mod.day_audit("2026-11-06", obs)
        self.assertEqual(row["fourbar_allfour"], 2)
    def test_timezone_less_rejected(self):
        obs = make_day()
        obs["AMD"]["2026-11-06T04:00:00"] = [1, 2, 1, 2]
        with self.assertRaises(ValueError):
            mod.day_audit("2026-11-06", obs)
    def test_missing_sector_fails_closed(self):
        obs = make_day()
        del obs["SOXX"]
        with self.assertRaises(ValueError):
            mod.day_audit("2026-11-06", obs)

if __name__ == "__main__":
    unittest.main()

