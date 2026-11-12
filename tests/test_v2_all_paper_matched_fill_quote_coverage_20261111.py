import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "research" / "v2_all_paper_matched_fill_quote_coverage_20261111.py"
spec = importlib.util.spec_from_file_location("quoteaudit", SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(source="MBB", day="2026-11-11", sym="MCHP", entry="100", exitp="101"):
    return dict(source=source, day=day, symbol=sym, entry=entry, exit=exitp, qty="2",
                entry_at=f"{day}T15:00:00+00:00",
                exit_at=f"{day}T15:02:00+00:00")


def fresh(bid, ask):
    return dict(status=m.FRESH, bid=bid, ask=ask, quote_age_seconds=0.1,
                size_at_best_at_least_order_quantity=True)


def qpair(day="2026-11-11", source="MBB", sym="MCHP", exit_status=None):
    k=f"{day}|{source}|{sym}|"
    return {k+"entry": fresh("99.9","100"), k+"exit": exit_status or fresh("101","101.1")}


class ReadOnlyQuoteEvidenceTest(unittest.TestCase):
    def test_complete_quote_pair_and_cost(self):
        z=m.audit([row()], qpair())
        self.assertEqual(z["two_sided_fresh_quote_pairs"],1)
        self.assertEqual(z["paired_actual_gross_usd"],2)
        self.assertAlmostEqual(z["midpoint_cost_descriptive_usd"],0.2)
        self.assertEqual(z["orders_submitted"],0)

    def test_one_stale_quote_not_a_pair(self):
        z=m.audit([row()],qpair(exit_status={"status":"QUOTE_STALE"}))
        self.assertEqual(z["two_sided_fresh_quote_pairs"],0)
        self.assertEqual(z["filled_leg_quote_status"],{m.FRESH:1,"QUOTE_STALE":1})

    def test_negative_fills_and_time_buckets(self):
        z=m.audit([row(entry="100",exitp="99")],qpair())
        self.assertEqual(z["by_source"]["MBB"]["gross_losses"],1)
        self.assertEqual(z["hold_time_bins"]["<=2m"],1)

    def test_duplicate_source_symbol_day_rejected(self):
        with self.assertRaises(ValueError):
            m.audit([row(),row()],qpair())

    def test_unmatched_quote_key_rejected(self):
        with self.assertRaises(ValueError):
            m.audit([row()], {**qpair(),"unexpected":{"status":"QUOTE_STALE"}})

    def test_missing_quote_leg_rejected(self):
        with self.assertRaises(ValueError):
            m.audit([row()],{"2026-11-11|MBB|MCHP|entry":fresh(99,100)})

    def test_ambiguous_source_rejected(self):
        with self.assertRaises(ValueError):
            m.audit([row(source="UNKNOWN")],qpair())

    def test_future_or_invalid_quote_rejected(self):
        q=qpair(); q["2026-11-11|MBB|MCHP|entry"]["quote_age_seconds"]=-0.1
        with self.assertRaises(ValueError):
            m.audit([row()],q)

    def test_per_source_disjoint_counts(self):
        r=[row(),row(source="FDR",day="2026-11-10",sym="AMD")]
        q={**qpair(),**qpair(day="2026-11-10",source="FDR",sym="AMD")}
        z=m.audit(r,q)
        self.assertEqual(z["distinct_days"],2)
        self.assertEqual(z["by_source"]["FDR"]["trades"],1)
        self.assertEqual(z["by_source"]["MBB"]["trades"],1)


if __name__ == "__main__":
    unittest.main()
