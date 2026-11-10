import unittest
from datetime import datetime, timedelta, timezone
from v2_forward_day_evidence_gate_20261110 import score, wilson_lower

T=datetime(2026,11,10,15,35,25,tzinfo=timezone.utc)
def stamp(d): return d.isoformat()
def row(day="2026-11-10",direction="UP",mark=100.,end=101.,slot=0,**updates):
    base = dict(mode="RESEARCH_ONLY",session_date=day,sector="semiconductors",
        horizon="60m",direction=direction,signal_id=f"{day}-{direction}-{slot}",
        source_bar_end_utc=stamp(T),signal_available_utc=stamp(T),
        sealed_at_utc=stamp(T+timedelta(seconds=2,minutes=slot)),
        signal_mark=mark,future_at_utc=stamp(T+timedelta(minutes=60)),
        outcome_retrieved_utc=stamp(T+timedelta(minutes=61)),future_mark=end,
        independent_seal_verified=True,quote_cost_verified=True,friction_bp=30)
    base.update(updates)
    return base

class GateTests(unittest.TestCase):
    def test_familywise_30_perfect_not_enough(self):
        self.assertLess(wilson_lower(30,30,42),.8)
        self.assertGreater(wilson_lower(43,43,42),.8)
    def test_unadjusted_29_30_not_allowed_by_familywise(self):
        self.assertLess(wilson_lower(29,30,42),.8)
    def test_earliest_signal_wins_no_hindsight_slot_selection(self):
        bad=row(end=98.,slot=0)
        good=row(end=104.,slot=1)
        r=score([bad,good],["2026-11-10"])["semiconductors:60m"]
        self.assertEqual((r["up"]["misses"],r["up"]["hits"],r["skipped_later_within_day"]),(1,0,1))
    def test_up_and_down_correctness_after_signal(self):
        r=score([row(direction="DOWN",end=98.)],["2026-11-10"])["semiconductors:60m"]
        self.assertEqual(r["down"]["hits"],1)
    def test_tiny_is_not_hit(self):
        r=score([row(end=100.02)],["2026-11-10"])["semiconductors:60m"]
        self.assertEqual((r["up"]["hits"],r["up"]["tiny"]),(0,1))
    def test_missing_dates_are_abstentions(self):
        r=score([row()],["2026-11-10","2026-11-11"])["semiconductors:60m"]
        self.assertEqual((r["predicted_days"],r["abstain_days"],r["coverage"]),(1,1,.5))
    def test_duplicate_id_fail_closed(self):
        with self.assertRaises(ValueError):score([row(),row()],[ "2026-11-10"])
    def test_future_bar_rejected(self):
        with self.assertRaises(ValueError):score([row(source_bar_end_utc=stamp(T+timedelta(minutes=5)))],["2026-11-10"])
    def test_future_outcome_before_seal_rejected(self):
        with self.assertRaises(ValueError):score([row(outcome_retrieved_utc=stamp(T+timedelta(minutes=10)))],["2026-11-10"])
    def test_unverified_quote_never_entitles_review(self):
        r=score([row(quote_cost_verified=False)],["2026-11-10"])["semiconductors:60m"]
        self.assertFalse(r["independent_evidence_all"])
        self.assertFalse(r["paper_review_eligible"])
    def test_80_predictive_does_not_equal_aftercost(self):
        r=score([row(end=100.2,friction_bp=30)],["2026-11-10"])["semiconductors:60m"]
        self.assertEqual((r["up"]["hits"],r["up"]["net_positive_attested"]),(1,0))
    def test_abstention_has_no_hindsight_price_requirements(self):
        r=score([row(direction="ABSTAIN",signal_mark=None,future_mark=None)],["2026-11-10"])["semiconductors:60m"]
        self.assertEqual((r["predicted_days"],r["abstain_days"]),(0,1))
    def test_paper_remains_unapproved(self):
        r=score([row()],["2026-11-10"])["semiconductors:60m"]
        self.assertFalse(r["paper_review_eligible"])
if __name__=="__main__": unittest.main()
